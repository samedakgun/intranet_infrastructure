import requests
from .config import Settings

class Embedder:
    """Ollama /api/embeddings ile metni embed eder."""
    def __init__(self, cfg: Settings):
        self.cfg = cfg
        self.url = cfg.OLLAMA_URL.rstrip("/") + "/api/embeddings"
        self.model = cfg.EMBED_MODEL

    def embed_texts(self, texts):
        vectors = []
        for t in texts:
            payload = {"model": self.model, "prompt": t}
            r = requests.post(self.url, json=payload, timeout=120)
            r.raise_for_status()
            vectors.append(r.json()["embedding"])
        return vectors

    def embed_query(self, text):
        return self.embed_texts([text])[0]
