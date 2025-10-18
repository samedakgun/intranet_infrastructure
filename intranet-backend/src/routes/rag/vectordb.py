import os
import shutil
import chromadb
from chromadb.config import Settings as ChromaSettings
from rank_bm25 import BM25Okapi
import numpy as np

from .config import Settings
from .embeddings import Embedder
from .utils import average_vectors

class VectorStore:
    """
    İki koleksiyon:
      - docs   : doküman centroid embedding (doc-level arama)
      - chunks : parça embedding (RAG retriever)
    """
    def __init__(self, cfg: Settings):
        self.cfg = cfg
        self.client = chromadb.PersistentClient(
            path=cfg.DB_DIR,
            settings=ChromaSettings(allow_reset=True)
        )
        self.docs = self.client.get_or_create_collection(name="docs")
        self.chunks = self.client.get_or_create_collection(name="chunks")
        self.embedder = Embedder(cfg)

        # BM25 cache (hibrit arama)
        self._bm25 = None
        self._bm25_docs = []  # (doc_id, full_text)

    # ---------- CRUD ----------
    def upsert_document(self, doc_id, title, text, meta):
        """Dokümanı chunk'la, embed et, docs ve chunks'a ekle; BM25'i güncelle."""
        words = text.split()
        cw, overlap = self.cfg.CHUNK_WORDS, self.cfg.CHUNK_OVERLAP
        chunks, metas, ids = [], [], []
        start = 0
        idx = 0
        while start < len(words):
            end = min(len(words), start + cw)
            chunk_text = " ".join(words[start:end]).strip()
            if chunk_text:
                chunks.append(chunk_text)
                metas.append({"doc_id": doc_id, "title": title, **meta, "chunk_index": idx})
                ids.append(f"{doc_id}::c{idx}")
                idx += 1
            start = end - overlap if end - overlap > start else end

        if not chunks:
            return 0

        chunk_vecs = self.embedder.embed_texts(chunks)
        doc_vec = average_vectors(chunk_vecs)

        # doc-level (tek satır: kısaltılmış gövde + meta)
        self.docs.add(
            ids=[doc_id],
            documents=[text[:2000]],
            metadatas=[{"title": title, **meta}],
            embeddings=[doc_vec],
        )
        # chunk-level
        self.chunks.add(
            ids=ids,
            documents=chunks,
            metadatas=metas,
            embeddings=chunk_vecs,
        )

        # BM25 cache güncelle
        self._bm25 = None
        self._bm25_docs.append((doc_id, text))
        return len(chunks)

    def list_documents(self):
        data = self.docs.get()
        out = []
        for i, doc_id in enumerate(data.get("ids", []) or []):
            md = data["metadatas"][i] if data.get("metadatas") else {}
            out.append({"doc_id": doc_id, "title": md.get("title"), "meta": md})
        return out

    def delete_document(self, doc_id):
        """Vektör DB'den siler ve storage/files/<doc_id> klasörünü kaldırır."""
        # vektör db
        self.docs.delete(ids=[doc_id])
        self.chunks.delete(where={"doc_id": doc_id})

        # bm25
        self._bm25 = None
        self._bm25_docs = [(d, t) for (d, t) in self._bm25_docs if d != doc_id]

        # dosya sistemi
        folder = os.path.join(self.cfg.FILES_DIR, doc_id)
        if os.path.isdir(folder):
            shutil.rmtree(folder, ignore_errors=True)
            return True
        return False

    def document_exists(self, doc_id):
        data = self.docs.get(ids=[doc_id])
        return bool(data.get("ids"))

    # ---------- Search ----------
    def search_documents(self, query, k=5, hybrid=False):
        """Top-k doküman: vektör arama (+ opsiyonel BM25 hibrit re-rank)."""
        qvec = self.embedder.embed_query(query)
        res = self.docs.query(query_embeddings=[qvec], n_results=k)
        results = []
        for i in range(len(res["ids"][0])):
            doc_id = res["ids"][0][i]
            md = res["metadatas"][0][i] if res.get("metadatas") else {}
            score_vec = 1 - res["distances"][0][i] if "distances" in res else None
            results.append({"doc_id": doc_id, "title": md.get("title"), "score_vec": score_vec, "meta": md})

        if hybrid:
            bm25 = self._get_bm25()
            tokens = query.split()
            scores = np.asarray(bm25.get_scores(tokens), dtype=float)  # ndarray
            by_id = {doc_id: s for (doc_id, _), s in zip(self._bm25_docs, scores)}

            if scores.size:  # numpy için doğrulama
                mn = float(scores.min())
                mx = float(scores.max())
                rng = max(mx - mn, 1e-9)
            else:
                mn, rng = 0.0, 1.0

            for r in results:
                kw = by_id.get(r["doc_id"], 0.0)
                # 0..1 normalize edilmiş BM25
                score_kw = (kw - mn) / rng if rng > 0 else 0.0
                r["score_kw"] = score_kw
                r["score"] = self.cfg.HYBRID_ALPHA * (r.get("score_vec") or 0.0) + (1 - self.cfg.HYBRID_ALPHA) * score_kw

            # en yüksek skora göre sırala
            results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        else:
            for r in results:
                r["score"] = r.get("score_vec")

        return results[:k]

    def top_chunks_for_doc(self, doc_id, question, k=6):
        """RAG için tek dokümanda top-k chunk retrieval."""
        qvec = self.embedder.embed_query(question)
        res = self.chunks.query(query_embeddings=[qvec], n_results=k, where={"doc_id": doc_id})
        out = []
        for i in range(len(res["ids"][0])):
            out.append({
                "chunk_id": res["ids"][0][i],
                "text": res["documents"][0][i],
                "meta": res["metadatas"][0][i],
                "distance": res["distances"][0][i] if "distances" in res else None
            })
        return out

    # ---------- internal ----------
    def _get_bm25(self):
        if self._bm25 is None:
            corpus = [t.split() for _, t in self._bm25_docs] or [["__empty__"]]
            self._bm25 = BM25Okapi(corpus)
        return self._bm25
