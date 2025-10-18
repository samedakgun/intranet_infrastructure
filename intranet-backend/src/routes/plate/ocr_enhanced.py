# ocr_enhanced.py
# OCR ve TR plaka post-process yardımcıları

from __future__ import annotations
import re
from typing import Dict, List, Tuple, Optional

import cv2
import numpy as np

# --- OCR motoru opsiyonel PaddleOCR, yoksa Tesseract ---
try:
    from paddleocr import PaddleOCR  # pip install paddleocr
    _HAS_PADDLE = True
except Exception:
    _HAS_PADDLE = False

try:
    import pytesseract  # pip install pytesseract, tesseract binary kurulu olmalı
    _HAS_TESS = True
except Exception:
    _HAS_TESS = False


# ------------------ TR plaka kuralları ------------------
# 01..81 il kodu + 1-3 harf + 2-4 rakam
TR_PLATE_REGEX_STRICT = re.compile(r"^(0[1-9]|[1-7]\d|8[01])([A-Z]{1,3})(\d{2,4})$")
# Fazla toleranslı arama (boşluk/ayraç vs. temizlendikten sonra kullanılır)
TR_PLATE_REGEX_FUZZY  = re.compile(r"(0[1-9]|[1-7]\d|8[01])[A-Z]{1,3}\d{2,4}")

# OCR karakter düzeltme haritaları
# (konuma özel uyguluyoruz: il=rakam, harf=harf, num=rakam)
MAP_TO_DIGIT = {
    "O":"0", "Q":"0", "D":"0",
    "I":"1", "l":"1", "|":"1",
    "S":"5", "B":"8", "Z":"2", "G":"6", "T":"7"
}
MAP_TO_LETTER = {
    "0":"O", "1":"I", "5":"S", "8":"B", "6":"G", "2":"Z", "4":"A", "7":"T"
}


# --------------- yardımcı small utils -------------------
def normalize_text(s: str) -> str:
    return "".join(ch for ch in s if ch.isalnum()).upper()

def enhance_crop_for_ocr(crop_bgr: np.ndarray) -> np.ndarray:
    """Plaka kırpımında kontrast/temizlik."""
    if crop_bgr is None or crop_bgr.size == 0:
        return crop_bgr
    h, w = crop_bgr.shape[:2]
    if max(h, w) < 220:
        scale = 300 / max(h, w)
        crop_bgr = cv2.resize(crop_bgr, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_CUBIC)
    blur = cv2.bilateralFilter(crop_bgr, d=7, sigmaColor=60, sigmaSpace=60)
    gray = cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    # adaptif + otsu varyantlarından hangisi iyi ise onu OCR motoruna veririz
    return gray

def binarize_variants(gray: np.ndarray) -> List[np.ndarray]:
    variants = []
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, otsu_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    adp = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 25, 7)
    adp_inv = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY_INV, 25, 7)
    variants.extend([otsu, adp, otsu_inv, adp_inv])
    return variants

# --------------- yapı parse & düzeltme -------------------
def parse_tr_plate(s: str) -> Dict:
    s = normalize_text(s)
    m = TR_PLATE_REGEX_STRICT.match(s)
    if m:
        il, harf, num = m.groups()
        return {
            "valid": True, "province": il, "letters": harf, "numbers": num,
            "full": f"{il}{harf}{num}", "formatted": f"{il} {harf} {num}"
        }
    # fuzzy arama
    m2 = TR_PLATE_REGEX_FUZZY.search(s)
    if m2:
        start = m2.start()
        candidate = s[start:start+len(m2.group(0))]
        m3 = TR_PLATE_REGEX_STRICT.match(candidate)
        if m3:
            il, harf, num = m3.groups()
            return {
                "valid": True, "province": il, "letters": harf, "numbers": num,
                "full": f"{il}{harf}{num}", "formatted": f"{il} {harf} {num}"
            }
    return {"valid": False, "full": s, "formatted": s, "province":"", "letters":"", "numbers":""}

def fix_by_position(province: str, letters: str, numbers: str) -> Tuple[str, str, str, List[str]]:
    fixes: List[str] = []
    # province: sadece rakam
    prov = "".join(MAP_TO_DIGIT.get(ch, ch) for ch in province)
    if prov != province: fixes.append("province-map")
    # letters: sadece harf
    lets = "".join(MAP_TO_LETTER.get(ch, ch) for ch in letters)
    if lets != letters: fixes.append("letters-map")
    # numbers: sadece rakam
    nums = "".join(MAP_TO_DIGIT.get(ch, ch) for ch in numbers)
    if nums != numbers: fixes.append("numbers-map")
    return prov, lets, nums, fixes

def postprocess_plate(raw_text: str) -> Dict:
    """OCR çıktısını TR kuralına göre normalize eder."""
    s0 = normalize_text(raw_text)
    parsed = parse_tr_plate(s0)
    if parsed["valid"]:
        p, l, n, fixes = fix_by_position(parsed["province"], parsed["letters"], parsed["numbers"])
        parsed.update({
            "province": p, "letters": l, "numbers": n,
            "full": f"{p}{l}{n}", "formatted": f"{p} {l} {n}",
            "applied_fixes": fixes
        })
        return parsed

    # Heuristik düzeltme: bazen başa fazladan '1/I' sızabiliyor
    s = s0
    if len(s) >= 3 and s[0] in ("1","I") and s[1:3].isdigit():
        s = s[1:]
    # tekrar dene
    parsed = parse_tr_plate(s)
    if parsed["valid"]:
        p, l, n, fixes = fix_by_position(parsed["province"], parsed["letters"], parsed["numbers"])
        parsed.update({
            "province": p, "letters": l, "numbers": n,
            "full": f"{p}{l}{n}", "formatted": f"{p} {l} {n}",
            "applied_fixes": ["drop-leading-1I"] + fixes
        })
        return parsed

    # olmadı -> valid=False gönder
    return {"valid": False, "full": s0, "formatted": s0,
            "province":"", "letters":"", "numbers":"", "applied_fixes":[]}

# --------------- OCR motoru sınıfı ----------------------
class OCREngine:
    """
    engine='paddle' -> PaddleOCR
    engine='tesseract' -> pytesseract
    engine='auto' -> önce Paddle varsa onu, yoksa Tesseract
    """
    def __init__(self, engine: str = "auto"):
        self.engine_type = engine
        self._paddle = None

        if engine in ("auto", "paddle") and _HAS_PADDLE:
            # Latin karakter seti için 'en'/'latin' yeterli
            self._paddle = PaddleOCR(lang="en", use_angle_cls=False, show_log=False)
            self.engine_type = "paddle"
        elif engine in ("auto", "tesseract") and _HAS_TESS:
            self.engine_type = "tesseract"
        elif engine == "paddle":
            raise RuntimeError("PaddleOCR kurulu değil (pip install paddleocr).")
        else:
            raise RuntimeError("Tesseract kurulu değil (pytesseract + tesseract binary).")

    def _tess_read(self, img: np.ndarray) -> Tuple[str, float]:
        assert _HAS_TESS, "pytesseract yok."
        # hızlı ve kararlı: tek satır modları
        configs = [
            "--oem 1 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            "--oem 1 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        ]
        best_txt, best_conf = "", 0.0
        for cfg in configs:
            try:
                data = pytesseract.image_to_data(img, lang="eng", config=cfg,
                                                 output_type=pytesseract.Output.DICT)
                toks, confs = [], []
                for t, c in zip(data["text"], data["conf"]):
                    if not t or t.strip() == "" or str(c) == "-1":
                        continue
                    tok = normalize_text(t)
                    if tok:
                        toks.append(tok)
                        try: confs.append(float(c))
                        except: pass
                if toks:
                    txt = "".join(toks)
                    conf = (sum(confs)/len(confs))/100.0 if confs else 0.6
                else:
                    txt = normalize_text(pytesseract.image_to_string(img, lang="eng", config=cfg))
                    conf = 0.5 if txt else 0.0
                if conf > best_conf or (conf >= best_conf and len(txt) > len(best_txt)):
                    best_txt, best_conf = txt, conf
            except Exception:
                continue
        return best_txt, best_conf

    def _paddle_read(self, img: np.ndarray) -> Tuple[str, float]:
        assert self._paddle is not None
        # PaddleOCR BGR değil RGB beklemez; direkt gray/binary verebiliriz
        res = self._paddle.ocr(img, det=False, cls=False)  # sadece tanıma
        toks, confs = [], []
        for line in res:
            for txt, conf in line:
                tok = normalize_text(txt or "")
                if tok:
                    toks.append(tok)
                    confs.append(float(conf))
        if toks:
            return "".join(toks), float(sum(confs)/len(confs)) if confs else 0.6
        return "", 0.0

    def recognize(self, crop_bgr: np.ndarray) -> Dict:
        if crop_bgr is None or crop_bgr.size == 0:
            return {"text":"", "conf":0.0}

        gray = enhance_crop_for_ocr(crop_bgr)
        # hızlı mod: iki binarizasyon dene
        variants = binarize_variants(gray)[:2]  # [otsu, adaptive]

        best_txt, best_conf = "", 0.0
        for v in variants:
            if self.engine_type == "paddle":
                txt, conf = self._paddle_read(v)
            else:
                txt, conf = self._tess_read(v)
            if conf > best_conf or (conf >= best_conf and len(txt) > len(best_txt)):
                best_txt, best_conf = txt, conf

        return {"text": best_txt, "conf": float(best_conf), "engine": self.engine_type}
