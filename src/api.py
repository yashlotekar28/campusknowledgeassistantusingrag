"""FastAPI backend server for the Campus Knowledge Assistant."""

import shutil
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from src.assistant import CampusKnowledgeAssistant
from src.config import config, PROJECT_ROOT

try:
    from google import genai
except ImportError:
    genai = None

app = FastAPI(
    title="MIT AOE Campus Knowledge Assistant API",
    version="1.0.0",
    description="RAG backend API supporting official and personal document queries with hybrid search.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

assistant = CampusKnowledgeAssistant()


class QueryRequest(BaseModel):
    question: str
    scope: Optional[str] = "all"
    top_k: Optional[int] = 3


class SettingsRequest(BaseModel):
    gemini_api_key: str
    gemini_model: Optional[str] = None


@app.post("/api/query")
async def handle_query(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    result = assistant.ask(
        question=req.question.strip(),
        top_k=req.top_k or 3,
        scope=req.scope or "all",
    )
    return result


@app.post("/api/upload")
async def handle_upload(
    file: UploadFile = File(...),
    scope: str = Form("personal"),
):
    valid_exts = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg"}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in valid_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{file_ext}'. Supported: {', '.join(valid_exts)}",
        )

    upload_dir = Path("data/uploads") / scope
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / file.filename

    with open(destination, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        ingest_result = assistant.ingest_document(destination, doc_scope=scope)
        return {
            "status": "success",
            "message": f"Successfully indexed {file.filename}",
            "details": ingest_result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents")
async def list_documents():
    docs = assistant.vector_db.list_documents()
    return {"documents": docs, "total_documents": len(docs)}


@app.get("/api/stats")
async def get_stats():
    return {
        "total_chunks": assistant.vector_db.count(),
        "model": config.gemini_model,
        "embedding_model": config.embedding_model_name,
        "collection": config.collection_name,
        "has_api_key": bool(config.gemini_api_key and config.gemini_api_key != "your_gemini_api_key_here"),
    }


@app.post("/api/settings")
async def update_settings(req: SettingsRequest):
    key = req.gemini_api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API Key cannot be empty.")

    config.gemini_api_key = key
    assistant.generator.api_key = key
    if genai:
        assistant.generator.client = genai.Client(api_key=key)

    # Persist to .env
    env_path = PROJECT_ROOT / ".env"
    lines = []
    found = False
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("GEMINI_API_KEY="):
                lines.append(f"GEMINI_API_KEY={key}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"GEMINI_API_KEY={key}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {"status": "success", "message": "API Key saved and active!"}


# Mount the frontend static files
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
