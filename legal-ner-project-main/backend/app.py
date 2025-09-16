# backend/app.py
import os
import sys
import json
import re
import sqlite3
import datetime
import logging
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import fitz  # PyMuPDF


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("legal-ner")


RUN_NER_FALLBACK = False
def _fallback_run_ner(text: str) -> List[Dict[str, Any]]:
    """Very simple spaCy-based fallback if inference.py is missing."""
    try:
        import spacy
        try:
            nlp = spacy.load("en_core_web_sm")
        except Exception:
            nlp = spacy.blank("en")  # no entities in pure blank model
        doc = nlp(text)
        ents = []
        for ent in doc.ents:
            ents.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
                "score": None,  # spaCy small model doesn’t expose per-entity score
            })
        return ents
    except Exception as e:
        log.exception("Fallback NER failed: %s", e)
        return []

def _fallback_ensure_nlp():
    # Nothing heavy to preload in fallback; keep for API parity
    return True

# make local imports work when running `python app.py`
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from inference import run_ner, ensure_nlp  # your custom model
    log.info("Using inference.py for NER.")
except Exception as e:
    log.warning("Could not import inference.py, using spaCy fallback. Reason: %s", e)
    RUN_NER_FALLBACK = True
    run_ner = _fallback_run_ner
    ensure_nlp = _fallback_ensure_nlp


# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "database"))
DB_PATH = os.path.join(DB_DIR, "legal.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
FRONTEND_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "frontend"))

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)


# DB Init

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
      CREATE TABLE IF NOT EXISTS documents(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        content TEXT,
        entities TEXT,
        created_at TEXT NOT NULL
      )
    """)
    conn.commit()
    conn.close()

init_db()


# FastAPI

app = FastAPI(title="Legal NER – PDF Extractor", version="1.0")

# CORS (you can restrict in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # e.g. ["http://localhost:8080"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve built frontend (optional)
if os.path.exists(FRONTEND_DIR):
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    log.info("Mounted frontend at /app from %s", FRONTEND_DIR)
else:
    log.info("Frontend directory not found at %s (skip mounting).", FRONTEND_DIR)

# Warm up model
try:
    ensure_nlp()
    MODEL_READY = True
except Exception as e:
    log.exception("ensure_nlp failed: %s", e)
    MODEL_READY = False

# -------------------------
# Models
# -------------------------
class DocItem(BaseModel):
    id: int
    filename: str
    content: str
    entities: List[Dict[str, Any]]
    created_at: str

# -------------------------
# Utils
# -------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using PyMuPDF."""
    text_chunks: List[str] = []
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                # try standard text first
                t = page.get_text("text")
                if not t.strip():
                    # fallback attempts
                    t = page.get_text("blocks") or page.get_text("raw")
                text_chunks.append(t or "")
    except Exception as e:
        log.exception("Error reading PDF: %s", e)
        raise HTTPException(status_code=500, detail=f"Error reading PDF: {e}")
    full_text = "\n".join(text_chunks)
    if not full_text.strip():
        log.warning("No text extracted from: %s", pdf_path)
    return full_text

# -------------------------
# Endpoints
# -------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_ready": MODEL_READY,
        "using_fallback": RUN_NER_FALLBACK,
    }

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", file.filename)
    save_path = os.path.join(UPLOAD_DIR, safe_name)

    try:
        content_bytes = await file.read()
        with open(save_path, "wb") as f:
            f.write(content_bytes)
        log.info("Saved PDF to %s", save_path)
    except Exception as e:
        log.exception("Failed to save file: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    content = extract_text_from_pdf(save_path)
    if not content.strip():
        # Return gracefully so frontend can show a friendly message
        return {
            "id": None,
            "filename": safe_name,
            "content": "",
            "entities": [],
            "created_at": datetime.datetime.utcnow().isoformat(),
            "warning": "No text extracted from PDF (it may be scanned).",
        }

    try:
        entities = run_ner(content) or []
    except Exception as e:
        log.exception("run_ner failed: %s", e)
        entities = []

    # Normalize entity fields
    norm_entities: List[Dict[str, Any]] = []
    for e in entities:
        norm_entities.append({
            "text": e.get("text") if isinstance(e, dict) else getattr(e, "text", ""),
            "label": e.get("label") if isinstance(e, dict) else getattr(e, "label_", ""),
            "start": e.get("start") if isinstance(e, dict) else getattr(e, "start_char", None),
            "end": e.get("end") if isinstance(e, dict) else getattr(e, "end_char", None),
            "score": e.get("score") if isinstance(e, dict) else None,
        })

    # Save to DB
    now = datetime.datetime.utcnow().isoformat()
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO documents(filename, content, entities, created_at) VALUES(?,?,?,?)",
            (safe_name, content, json.dumps(norm_entities, ensure_ascii=False), now),
        )
        conn.commit()
        doc_id = c.lastrowid
    except Exception as e:
        log.exception("DB insert failed: %s", e)
        raise HTTPException(status_code=500, detail=f"DB insert failed: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return {
        "id": doc_id,
        "filename": safe_name,
        "content": content,
        "entities": norm_entities,
        "created_at": now
    }

@app.get("/documents", response_model=List[DocItem])
def list_documents():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, filename, content, entities, created_at FROM documents ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    docs: List[Dict[str, Any]] = []
    for r in rows:
        docs.append({
            "id": r[0],
            "filename": r[1],
            "content": r[2],
            "entities": json.loads(r[3]) if r[3] else [],
            "created_at": r[4],
        })
    return docs

@app.get("/export.json")
def export_json():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, filename, content, entities, created_at FROM documents ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    data = [{
        "id": r[0],
        "filename": r[1],
        "content": r[2],
        "entities": json.loads(r[3]) if r[3] else [],
        "created_at": r[4],
    } for r in rows]
    return JSONResponse(data)

@app.get("/export.csv")
def export_csv():
    import csv, io
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, filename, content, entities, created_at FROM documents ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "filename", "created_at", "entity_text", "label", "start", "end"])
    for r in rows:
        doc_id, fname, content, entities_json, created_at = r
        try:
            ents = json.loads(entities_json) if entities_json else []
        except Exception:
            ents = []
        if not ents:
            writer.writerow([doc_id, fname, created_at, "", "", "", ""])
        else:
            for e in ents:
                writer.writerow([
                    doc_id, fname, created_at,
                    e.get("text",""), e.get("label",""),
                    e.get("start",""), e.get("end","")
                ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=export.csv"}
    )

# -------------------------
# Dev entrypoint
# -------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)


from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Legal NER – PDF Extractor", version="1.0")

# ✅ Allow frontend to call backend (CORS issue fix)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # production me specific domain dena
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Hello, FastAPI is running!"}

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    # file ka naam return kar rahe hain just for testing
    return {"filename": file.filename}
