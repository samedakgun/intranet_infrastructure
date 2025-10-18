# src/routes/rag/api.py
from __future__ import annotations
import os
from flask import Blueprint, request, jsonify, current_app
from dotenv import load_dotenv

# --- GÖRELİ IMPORTLAR (aynı paket altından) ---
from .config import Settings
from .utils import allowed_file
from . import ingest as ingest_mod
from . import vectordb as vectordb_mod
from . import rag_pipeline as rag_mod

load_dotenv()

cfg = Settings.from_env()
rag_bp = Blueprint("rag", __name__)

# Tekil servis örnekleri
db = vectordb_mod.VectorStore(cfg)
ingester = ingest_mod.Ingester(cfg, db)
rag = rag_mod.RAGPipeline(cfg, db)

def _bool(x, default=False):
    if x is None: return default
    x = str(x).strip().lower()
    return x in ("1", "true", "yes", "on")

@rag_bp.before_app_request
def _apply_limits():
    target = cfg.MAX_FILE_MB * 1024 * 1024
    if current_app.config.get("MAX_CONTENT_LENGTH") != target:
        current_app.config["MAX_CONTENT_LENGTH"] = target

# ---------- Health ----------
@rag_bp.get("/rag/health")
def health():
    return jsonify({
        "ok": True,
        "time": Settings.now_iso(),
        "model": cfg.OLLAMA_MODEL,
        "embed_model": cfg.EMBED_MODEL,
        "limits": {
            "max_file_mb": cfg.MAX_FILE_MB,
            "chunk_words": cfg.CHUNK_WORDS,
            "chunk_overlap": cfg.CHUNK_OVERLAP
        }
    })

# ---------- Files ----------
@rag_bp.post("/rag/files")
def add_file():
    if "file" not in request.files:
        return jsonify({"error": "form-data içinde 'file' alanı yok"}), 400
    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "geçersiz dosya"}), 400
    if not allowed_file(file.filename, cfg.ALLOWED_EXTS):
        return jsonify({"error": f"desteklenmeyen dosya. izinli: {sorted(cfg.ALLOWED_EXTS)}"}), 415

    try:
        doc = ingester.ingest_file(file)
        return jsonify({"success": True, "doc": doc}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"yükleme/indeksleme hatası: {e}"}), 500

@rag_bp.get("/rag/files")
def list_files():
    docs = db.list_documents()
    return jsonify({"count": len(docs), "docs": docs})

@rag_bp.delete("/rag/files/<doc_id>")
def delete_file(doc_id):
    if not db.document_exists(doc_id):
        return jsonify({"error": "doc not found"}), 404
    db.delete_document(doc_id)
    return jsonify({"success": True})

# ---------- Search / Ask ----------
@rag_bp.get("/rag/search")
def search_docs():
    query = (request.args.get("q") or "").strip()
    if not query:
        return jsonify({"error": "q parametresi zorunlu"}), 400
    try:
        k = int(request.args.get("k", cfg.TOPK_DOCS))
    except ValueError:
        k = cfg.TOPK_DOCS

    hybrid = _bool(request.args.get("hybrid"), default=False)
    group  = _bool(request.args.get("group"),  default=False)
    doc_id_filter = (request.args.get("doc_id") or "").strip() or None

    # Temel arama
    results = db.search_documents(query, k=max(k, 30), hybrid=hybrid)

    # doc_id filtresi
    if doc_id_filter:
        results = [r for r in results if r.get("doc_id") == doc_id_filter]

    if group:
        grouped = {}
        for r in results:
            did = r.get("doc_id")
            score = float(r.get("score", 0))
            if not did:
                continue
            if did not in grouped or score > grouped[did]["score"]:
                grouped[did] = {
                    "doc_id": did,
                    "title": r.get("title"),
                    "score": score
                }
        top_docs = sorted(grouped.values(), key=lambda x: x["score"], reverse=True)[:k]
        return jsonify({"query": query, "hybrid": hybrid, "top_docs": top_docs})

    # varsayılan: düz sonuç listesi
    return jsonify({"query": query, "k": k, "hybrid": hybrid, "results": results})


@rag_bp.post("/rag/ask")
def ask():
    data = request.get_json(silent=True) or {}
    doc_id = (data.get("doc_id") or "").strip()
    question = (data.get("question") or "").strip()
    try:
        k = int(data.get("k", cfg.TOPK_CHUNKS))
    except ValueError:
        k = cfg.TOPK_CHUNKS

    if not doc_id or not question:
        return jsonify({"error": "doc_id ve question zorunlu"}), 400
    if not db.document_exists(doc_id):
        return jsonify({"error": "doc not found"}), 404

    try:
        answer = rag.answer(doc_id=doc_id, question=question, k=k)
        return jsonify(answer)
    except Exception as e:
        return jsonify({"error": f"ask error: {e}"}), 500
