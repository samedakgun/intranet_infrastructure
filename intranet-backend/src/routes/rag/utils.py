import os
import uuid
import chardet

def ensure_uuid(x=None):
    """Geçerli bir UUID döndür. x verilirse doğrula, yoksa üret."""
    try:
        return str(uuid.UUID(str(x))) if x else str(uuid.uuid4())
    except Exception:
        return str(uuid.uuid4())

def average_vectors(vectors):
    """Vektörlerin basit ortalamasını döndür."""
    if not vectors:
        return []
    n = len(vectors)
    dim = len(vectors[0])
    out = [0.0] * dim
    for v in vectors:
        for i in range(dim):
            out[i] += v[i]
    return [x / n for x in out]

def allowed_file(filename, allowed_exts):
    """Uzantı beyaz liste kontrolü."""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in {e.strip().lower() for e in allowed_exts}

def read_txt_fallback(path):
    """UTF-8 deneyip gerekirse tespit edilen encoding ile okur."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(path, "rb") as f:
            data = f.read()
        enc = chardet.detect(data)["encoding"] or "latin-1"
        return data.decode(enc, errors="ignore")

def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
