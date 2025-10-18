# inference_api.py
from __future__ import annotations
import base64
import glob
import os
import time
from datetime import datetime
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from ultralytics import YOLO

from scripts.ocr_enhanced import OCREngine, postprocess_plate, normalize_text

# =================== CONFIG ===================
CONF_THRES = float(os.getenv("PLATE_CONF", "0.25"))
IOU_THRES  = float(os.getenv("PLATE_IOU",  "0.70"))
PAD_FACTOR = float(os.getenv("PLATE_PAD",  "0.12"))   # kırpımda %12 padding
DEFAULT_ENGINE = os.getenv("OCR_ENGINE", "auto")      # auto | paddle | tesseract
INCLUDE_CROPS_DEFAULT = False

def _find_weights() -> str:
    cand = sorted(glob.glob("runs/detect/train*/weights/best.pt"), key=os.path.getmtime)
    if cand:
        return cand[-1]
    path2 = "models/final/best_tr_plate_model.pt"
    if os.path.exists(path2):
        return path2
    raise FileNotFoundError("Model bulunamadı. 'models/final/best_tr_plate_model.pt' koyun veya MODEL_WEIGHTS ayarlayın.")

WEIGHTS = os.getenv("MODEL_WEIGHTS") or _find_weights()
MODEL = YOLO(WEIGHTS)  # Ultralytics
APP = FastAPI(title="TR Plate Detection API", version="1.0.0")

# =================== IO Helpers ===================
def _read_image_bytes(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Görsel decode edilemedi.")
    return img

def _bbox_with_padding(img: np.ndarray, x1: float, y1: float, x2: float, y2: float, pad: float) -> tuple[int,int,int,int]:
    h, w = img.shape[:2]
    bw, bh = (x2 - x1), (y2 - y1)
    px, py = bw * pad, bh * pad
    X1 = max(0, int(x1 - px)); Y1 = max(0, int(y1 - py))
    X2 = min(w, int(x2 + px)); Y2 = min(h, int(y2 + py))
    return X1, Y1, X2, Y2

def _crop(img: np.ndarray, box) -> np.ndarray:
    x1, y1, x2, y2 = box
    return img[y1:y2, x1:x2].copy()

def _to_b64_jpg(img: np.ndarray, q=90) -> Optional[str]:
    if img is None or img.size == 0:
        return None
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, q])
    return base64.b64encode(buf.tobytes()).decode("utf-8") if ok else None

# =================== Schemas ===================
class B64Image(BaseModel):
    image_b64: str

@APP.get("/health")
def health():
    return {"ok": True, "weights": os.path.basename(WEIGHTS), "conf": CONF_THRES, "iou": IOU_THRES}

@APP.post("/detect-plate")
async def detect_plate(
    file: UploadFile | None = File(default=None),
    payload: B64Image | None = Body(default=None),
    include_crops: bool = Query(default=INCLUDE_CROPS_DEFAULT),
    ocr_engine: str = Query(default=DEFAULT_ENGINE, pattern="^(auto|paddle|tesseract)$"),
    debug: bool = Query(default=False)
):
    try:
        # ---- input ----
        if file is None and payload is None:
            raise HTTPException(400, "image dosyası (multipart) ya da image_b64 (JSON) verilmeli.")

        if file is not None:
            raw = await file.read()
            img = _read_image_bytes(raw)
            img_fmt = (file.filename or "").split(".")[-1].upper()
        else:
            b64 = payload.image_b64
            img = _read_image_bytes(base64.b64decode(b64))
            img_fmt = "B64"

        H, W = img.shape[:2]

        # ---- detection ----
        t0 = time.time()
        pred = MODEL.predict(img, conf=CONF_THRES, iou=IOU_THRES, verbose=False)[0]
        det_ms = int((time.time() - t0) * 1000)

        detections = []
        if len(pred.boxes) == 0:
            out = {
                "success": True,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "model_info": {
                    "model_name": os.path.basename(WEIGHTS),
                    "version": "1.0.0",
                    "confidence_threshold": CONF_THRES
                },
                "detections": [],
                "processing_time": {"detection_ms": det_ms, "ocr_ms": 0, "total_ms": det_ms},
                "image_info": {"width": W, "height": H, "format": img_fmt}
            }
            return JSONResponse(out, 200)

        # ---- OCR init ----
        ocr = OCREngine(engine=ocr_engine)

        # ---- per box ----
        t1 = time.time()
        for i, b in enumerate(pred.boxes):
            conf = float(b.conf.item())
            x1, y1, x2, y2 = map(float, b.xyxy[0].tolist())
            X1, Y1, X2, Y2 = _bbox_with_padding(img, x1, y1, x2, y2, PAD_FACTOR)
            crop = _crop(img, (X1, Y1, X2, Y2))

            o = ocr.recognize(crop)  # {"text","conf","engine"}
            post = postprocess_plate(o.get("text", ""))

            det = {
                "plate_id": i + 1,
                "bbox": {"x1": X1, "y1": Y1, "x2": X2, "y2": Y2},
                "confidence": round(conf, 3),
                "plate_text": post["formatted"] if post["valid"] else "",
                "ocr_confidence": round(float(o.get("conf", 0.0)), 3),
                "text_processing": {
                    "raw_text": normalize_text(o.get("text", "")),
                    "formatted_text": post["full"] if post["valid"] else "",
                    "is_valid_format": bool(post["valid"]),
                    "applied_fixes": post.get("applied_fixes", []),
                    "components": {
                        "province": post.get("province", ""),
                        "letters":  post.get("letters", ""),
                        "numbers":  post.get("numbers", "")
                    }
                }
            }
            if include_crops:
                det["crop_b64_jpg"] = _to_b64_jpg(crop, q=90)
            if debug:
                det["debug"] = {
                    "ocr_engine": o.get("engine"),
                    "bbox_area": int((X2-X1)*(Y2-Y1))
                }
            detections.append(det)

        ocr_ms = int((time.time() - t1) * 1000)

        out = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "model_info": {
                "model_name": os.path.basename(WEIGHTS),
                "version": "1.0.0",
                "confidence_threshold": CONF_THRES
            },
            "detections": detections,
            "processing_time": {"detection_ms": det_ms, "ocr_ms": ocr_ms, "total_ms": det_ms + ocr_ms},
            "image_info": {"width": W, "height": H, "format": img_fmt}
        }
        return JSONResponse(out, 200)

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(500, f"server_error: {e}")
