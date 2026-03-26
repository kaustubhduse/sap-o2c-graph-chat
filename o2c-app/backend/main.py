"""
FastAPI backend for the unified O2C application.
Uses the nl-to-sql LangChain pipeline for query processing.
"""
import sys
import os
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

# nl-to-sql lives only under this backend: o2c-app/backend/nl-to-sql
NL_TO_SQL_DIR = Path(__file__).resolve().parent / "nl-to-sql"
if not (NL_TO_SQL_DIR / "chain.py").is_file():
    raise RuntimeError(f"Expected nl-to-sql at {NL_TO_SQL_DIR} (missing chain.py).")
sys.path.insert(0, str(NL_TO_SQL_DIR))

from db import get_db
from chain import process_query

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# LangSmith tracing (optional)
if os.getenv("LANGCHAIN_API_KEY"):
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", "sap-o2c-nl-to-sql")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to MySQL on startup."""
    logger.info("Connecting to MySQL via LangChain...")
    db = get_db()
    tables = db.get_usable_table_names()
    logger.info(f"Database ready: {len(tables)} tables loaded")
    yield


app = FastAPI(
    title="SAP O2C Unified API",
    description="Graph visualization + NL-to-SQL chat (LangChain + Groq + MySQL)",
    version="2.0.0",
    lifespan=lifespan,
)


def _cors_allowed_origins() -> list[str]:
    """Comma-separated FRONTEND_URL / CORS_ORIGINS; trailing slashes stripped. Empty → allow all."""
    raw = (os.getenv("CORS_ORIGINS") or os.getenv("FRONTEND_URL") or "").strip()
    if not raw:
        return ["*"]
    return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]


_cors_origins = _cors_allowed_origins()
logger.info(f"CORS allow_origins: {_cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    message: str


class QueryResponse(BaseModel):
    answer: str
    sql: str | None = None
    data: str | None = None
    highlighted_nodes: list | None = None
    status: str
    result_empty: bool | None = None


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Process a natural language query through the LangChain pipeline."""
    logger.info(f"Query: {request.message}")
    result = process_query(request.message)
    logger.info(f"Status: {result['status']}")
    return result


@app.get("/api/health")
async def health():
    try:
        db = get_db()
        tables = db.get_usable_table_names()
        return {"status": "ok", "tables": len(tables), "engine": "langchain+groq+mysql"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
