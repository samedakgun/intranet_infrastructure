# src/routes/rag.py
from __future__ import annotations
import os, glob
from flask import Blueprint, request, jsonify, current_app
from dotenv import load_dotenv

from src.rag.config import Settings
from src.rag.utils import allowed_file
from src.rag import ingest as ingest_mod
from src.rag import vectordb as vectordb_mod
from src.rag import rag_pipeline as rag_mod

load_dotenv()  # .env varsa yükle

# ---- bootstrap ----
cfg = Settings.from_env()
rag_bp = Blueprint("rag", __name__)

# servisler (tekil instance)
db = vectordb_mod.VectorStore(cfg)
ingester = ingest_mod.Ingester(cfg, db)
rag = rag_mod.RAGPipeline(cfg, db)

def _bool(x, default=False):
    if x is None: return default
    x = str(x).strip().lower()
    return x in ("1", "true", "yes", "on")

@rag_bp.before_app_request
def _apply_limits():
    # (sadece ilk çağrıda set olur)
    current = current_app.config.get("MAX_CONTENT_LENGTH")
    target = cfg.MAX_FILE_MB * 1024 * 1024
    if not current or current != target:
        current_app.config["MAX_CONTENT_LENGTH"] = target

# ---------------- Health ----------------
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

# ---------------- Files -----------------
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

# ------------- Search / Ask -------------
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

    try:
        results = db.search_documents(query, k=k, hybrid=hybrid)
        return jsonify({"query": query, "k": k, "hybrid": hybrid, "results": results})
    except Exception as e:
        return jsonify({"error": f"search error: {e}"}), 500

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

# ------------- Reindex (opsiyonel) -------------
@rag_bp.post("/rag/reindex/<doc_id>")
def reindex_one(doc_id):
    folder = os.path.join(cfg.FILES_DIR, doc_id)
    if not os.path.isdir(folder):
        return jsonify({"error": "folder not found"}), 404

    cand = []
    for ext in cfg.ALLOWED_EXTS:
        cand.extend(glob.glob(os.path.join(folder, f"*.{ext}")))
    if not cand:
        return jsonify({"error": "no allowable file in folder"}), 400

    # eski indeks varsa sil
    if db.document_exists(doc_id):
        db.delete_document(doc_id)

    try:
        doc = ingester.ingest_from_path(cand[0], doc_id=doc_id)  # ingest.py içinde varsa; yoksa ingest_file + FileStorage mock gerekir
        return jsonify({"success": True, "doc": doc})
    except Exception as e:
        return jsonify({"error": f"reindex error: {e}"}), 500

@rag_bp.post("/rag/reindex/all")
def reindex_all():
    base = cfg.FILES_DIR
    if not os.path.isdir(base):
        return jsonify({"error": "files dir not found"}), 404

    indexed, skipped, errors = [], [], []
    for name in os.listdir(base):
        folder = os.path.join(base, name)
        if not os.path.isdir(folder):
            continue
        doc_id = name
        cand = []
        for ext in cfg.ALLOWED_EXTS:
            cand.extend(glob.glob(os.path.join(folder, f"*.{ext}")))
        if not cand:
            skipped.append({"doc_id": doc_id, "reason": "no allowable file"})
            continue

        # var olanı sil ve yeniden oluştur
        if db.document_exists(doc_id):
            db.delete_document(doc_id)
        try:
            doc = ingester.ingest_from_path(cand[0], doc_id=doc_id)
            indexed.append(doc["doc_id"])
        except Exception as e:
            errors.append({"doc_id": doc_id, "error": str(e)})

    return jsonify({"indexed": indexed, "skipped": skipped, "errors": errors})
