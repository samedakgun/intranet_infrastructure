import os
import uuid
import pdfplumber
import docx2txt
from werkzeug.utils import secure_filename

from .config import Settings
from .utils import read_txt_fallback, write_text

class Ingester:
    """
    Yüklenen dosyayı storage/files/<doc_id>/ içine kaydeder,
    metnini çıkarır ve aynı klasöre .txt yan dosyası olarak yazar.
    Ardından VectorStore'a upsert eder.
    """
    def __init__(self, cfg: Settings, db):
        self.cfg = cfg
        self.db = db

    def ingest_file(self, file_storage):
        filename = secure_filename(file_storage.filename)
        if not filename:
            raise ValueError("Geçersiz dosya adı")

        # boyut kontrol (isteğe bağlı: FileStorage.stream uzunluğu)
        folder_id = str(uuid.uuid4())
        folder = os.path.join(self.cfg.FILES_DIR, folder_id)
        os.makedirs(folder, exist_ok=True)

        original_path = os.path.join(folder, filename)
        file_storage.save(original_path)

        ext = filename.rsplit(".", 1)[-1].lower()
        if ext == "pdf":
            text = self._extract_pdf(original_path)
        elif ext == "docx":
            text = docx2txt.process(original_path) or ""
        elif ext in ("txt", "md"):
            text = read_txt_fallback(original_path)
        else:
            text = ""

        text = (text or "").strip()
        if not text:
            raise ValueError("Metin çıkarılamadı veya boş içerik")

        # aynı klasöre içerik kaydı
        text_sidecar = os.path.join(folder, f"{os.path.splitext(filename)[0]}.txt")
        write_text(text_sidecar, text)

        meta = {
            "filename": filename,
            "ext": ext,
            "folder": folder_id,
            "added_at": Settings.now_iso(),
        }

        chunks = self.db.upsert_document(
            doc_id=folder_id,
            title=filename,
            text=text,
            meta=meta
        )
        return {
            "doc_id": folder_id,
            "title": filename,
            "chunks": chunks,
            "meta": meta,
            "paths": {"original": original_path, "text": text_sidecar}
        }

    def _extract_pdf(self, path):
        out = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                try:
                    out.append(page.extract_text() or "")
                except Exception:
                    continue
        return "\n".join(out)
