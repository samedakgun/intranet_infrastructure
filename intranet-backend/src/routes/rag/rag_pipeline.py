# rag/rag_pipeline.py
import requests
from .config import Settings

# === EKLE: basit Türkçe tespiti ===
def _is_turkish(text: str) -> bool:
    tr_chars = set("çğıöşüÇĞİÖŞÜ")
    if any(ch in tr_chars for ch in text):
        return True
    low = text.lower()
    # Bazı yaygın TR ipuçları
    hints = (" nedir", " nasıl", " hangi", " ve ", " ile ", " mıdır", " mıdır?", " mıdır ", " mı ", " mi ", " mu ", " mü ", " neler")
    return any(h in low for h in hints)

# Dil politikasını netleştir
SYS_PROMPT = (
    "You are a helpful assistant. Answer the user's question using ONLY the provided context. "
    "If the answer is not in the context, say you don't know. Quote chunk indices if helpful. "
    "Be concise and accurate. "
    "Always respond in the SAME LANGUAGE as the user's question."
)

class RAGPipeline:
    def __init__(self, cfg: Settings, db):
        self.cfg = cfg
        self.db = db
        self.url = cfg.OLLAMA_URL.rstrip("/") + "/api/generate"
        self.model = cfg.OLLAMA_MODEL

    def _build_prompt(self, question, chunks):
        # === EKLE: dil ipucu ===
        lang_hint = "Türkçe" if _is_turkish(question) else "same as question"

        ctx_lines = []
        for c in chunks:
            idx = c["meta"].get("chunk_index", "?")
            ctx_lines.append(f"[chunk {idx}] {c['text']}")
        context_block = "\n\n".join(ctx_lines)

        return (
            f"### Context:\n{context_block}\n\n"
            f"### Question:\n{question}\n\n"
            f"### Answer Language: {lang_hint}\n"
            f"### Instructions:\nAnswer strictly from the Context."
        )

    def answer(self, doc_id, question, k=6):
        chunks = self.db.top_chunks_for_doc(doc_id, question, k=k)
        prompt = f"{SYS_PROMPT}\n\n{self._build_prompt(question, chunks)}"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2}
        }
        r = requests.post(self.url, json=payload, timeout=600)
        r.raise_for_status()
        text = r.json().get("response", "")

        return {
            "doc_id": doc_id,
            "question": question,
            "k": k,
            "chunks_used": [c["meta"].get("chunk_index") for c in chunks],
            "answer": text
        }
