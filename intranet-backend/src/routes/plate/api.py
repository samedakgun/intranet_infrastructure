# src/routes/plate/api.py
from __future__ import annotations
import os, base64, time, glob
from datetime import datetime
from typing import Optional

import cv2
import numpy as np
from flask import Blueprint, request, jsonify
from ultralytics import YOLO

# Relative import: aynı klasördeki OCR yardımcıları
from .ocr_enhanced import OCREngine, postprocess_plate, normalize_text

# ==== CONFIG ====
CONF_THRES = float(os.getenv("PLATE_CONF", "0.25"))
IOU_THRES  = float(os.getenv("PLATE_IOU",  "0.70"))
PAD_FACTOR = float(os.getenv("PLATE_PAD",  "0.12"))       # bbox'a % padding
DEFAULT_ENGINE = os.getenv("OCR_ENGINE", "auto")          # auto | paddle | tesseract
INCLUDE_CROPS_DEFAULT = os.getenv("INCLUDE_CROPS", "false").lower() == "true"

HERE = os.path.dirname(__file__)

def _find_weights() -> str:
    env = os.getenv("MODEL_WEIGHTS")
    if env and os.path.exists(env): return env
    cand = [
        os.path.join(HERE, "best_tr_plate_model.pt"),
        os.path.join(HERE, "models", "final", "best_tr_plate_model.pt"),
    ]
    for p in cand:
        if os.path.exists(p): return p
    globs = sorted(
        glob.glob(os.path.join(HERE, "runs", "detect", "train*", "weights", "best.pt"))
        + glob.glob("runs/detect/train*/weights/best.pt"),
        key=os.path.getmtime
    )
    if globs: return globs[-1]
    raise FileNotFoundError("YOLO weights bulunamadı. MODEL_WEIGHTS ayarla veya best_tr_plate_model.pt'yi bu klasöre koy.")

WEIGHTS_PATH = _find_weights()
MODEL = YOLO(WEIGHTS_PATH)  # global yükle (performans)

plate_bp = Blueprint("plate", __name__)

def _read_image_bytes(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Görsel decode edilemedi.")
    return img

def _bbox_with_padding(img: np.ndarray, x1: float, y1: float, x2: float, y2: float, pad: float):
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

@plate_bp.get("/plate/health")
def health():
    return jsonify({
        "ok": True,
        "weights": os.path.basename(WEIGHTS_PATH),
        "conf": CONF_THRES,
        "iou": IOU_THRES,
        "ocr_engine_default": DEFAULT_ENGINE
    }), 200

@plate_bp.post("/plate/detect")
def detect_plate():
    try:
        include_crops = (request.args.get("include_crops", str(INCLUDE_CROPS_DEFAULT)).lower() == "true")
        ocr_engine = request.args.get("ocr_engine", DEFAULT_ENGINE)
        debug = request.args.get("debug", "false").lower() == "true"

        # input: multipart (image) veya JSON (image_b64)
        if "image" in request.files:
            file = request.files["image"]
            raw = file.read()
            img_fmt = (file.filename or "").split(".")[-1].upper() or "BIN"
        else:
            payload = request.get_json(silent=True) or {}
            b64 = payload.get("image_b64")
            if not b64:
                return jsonify({"error": "image (multipart) ya da image_b64 (JSON) verilmeli."}), 400
            raw = base64.b64decode(b64)
            img_fmt = "B64"

        img = _read_image_bytes(raw)
        H, W = img.shape[:2]

        # detection
        t0 = time.time()
        pred = MODEL.predict(img, conf=CONF_THRES, iou=IOU_THRES, verbose=False)[0]
        det_ms = int((time.time() - t0) * 1000)

        if len(pred.boxes) == 0:
            return jsonify({
                "success": True,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "model_info": {"model_name": os.path.basename(WEIGHTS_PATH), "version": "1.0.0", "confidence_threshold": CONF_THRES},
                "detections": [],
                "processing_time": {"detection_ms": det_ms, "ocr_ms": 0, "total_ms": det_ms},
                "image_info": {"width": W, "height": H, "format": img_fmt}
            }), 200

        # OCR
        ocr = OCREngine(engine=ocr_engine)
        t1 = time.time()
        detections = []

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
                det["debug"] = {"ocr_engine": o.get("engine"), "bbox_area": int((X2 - X1) * (Y2 - Y1))}
            detections.append(det)

        ocr_ms = int((time.time() - t1) * 1000)

        return jsonify({
            "success": True,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "model_info": {"model_name": os.path.basename(WEIGHTS_PATH), "version": "1.0.0", "confidence_threshold": CONF_THRES},
            "detections": detections,
            "processing_time": {"detection_ms": det_ms, "ocr_ms": ocr_ms, "total_ms": det_ms + ocr_ms},
            "image_info": {"width": W, "height": H, "format": img_fmt}
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": f"server_error: {e}"}), 500
