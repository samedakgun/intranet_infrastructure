import os
import datetime


class Settings:
    # ---- Paths (sadece storage/files kullanılır) ----
    BASE_DIR    = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    STORAGE_DIR = os.path.join(BASE_DIR, "storage")
    FILES_DIR   = os.path.join(STORAGE_DIR, "files")   # her doküman için klasör
    DB_DIR      = os.path.join(STORAGE_DIR, "chroma")  # Chroma kalıcı dizini

    # ---- Ollama / Modeller ----
    OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b-instruct")
    EMBED_MODEL  = os.getenv("EMBED_MODEL", "nomic-embed-text")

    # ---- Chunking ----
    CHUNK_WORDS    = int(os.getenv("CHUNK_WORDS", "250"))
    CHUNK_OVERLAP  = int(os.getenv("CHUNK_OVERLAP", "50"))

    # ---- Arama ----
    TOPK_DOCS    = int(os.getenv("TOPK_DOCS", "5"))
    TOPK_CHUNKS  = int(os.getenv("TOPK_CHUNKS", "6"))
    HYBRID_ALPHA = float(os.getenv("HYBRID_ALPHA", "0.75"))

    # ---- Dosya türleri ----
    MAX_FILE_MB   = int(os.getenv("MAX_FILE_MB", "20"))
    ALLOWED_EXTS  = set((os.getenv("ALLOWED_EXTS", "pdf,txt,md,docx")).split(","))

    @staticmethod
    def now_iso():
        return datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    @classmethod
    def ensure_dirs(cls):
        os.makedirs(cls.STORAGE_DIR, exist_ok=True)
        os.makedirs(cls.FILES_DIR, exist_ok=True)
        os.makedirs(cls.DB_DIR, exist_ok=True)

    @classmethod
    def from_env(cls):
        cls.ensure_dirs()
        return cls
