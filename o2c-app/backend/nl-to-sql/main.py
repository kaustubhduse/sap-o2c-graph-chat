"""
FastAPI server for the NL-to-SQL pipeline.
Replaces the old query_engine — now powered by LangChain + Groq + MySQL.
"""
import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

from db import get_db
from chain import process_query

load_dotenv()

# Optional: LangSmith tracing
if os.getenv("LANGCHAIN_API_KEY"):
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", "sap-o2c-nl-to-sql")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to database on startup."""
    logger.info("Connecting to MySQL database...")
    db = get_db()
    tables = db.get_usable_table_names()
    logger.info(f"Database ready: {len(tables)} tables")
    yield


app = FastAPI(
    title="SAP O2C NL-to-SQL API",
    description="Natural language to SQL query interface for SAP O2C data (LangChain + Groq)",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ────────────────────────────────────────
class QueryRequest(BaseModel):
    message: str


class QueryResponse(BaseModel):
    answer: str
    sql: str | None = None
    data: str | None = None
    highlighted_nodes: list | None = None
    status: str


# ── Endpoints ────────────────────────────────────────────────────────
@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Process a natural language query through the LangChain pipeline."""
    logger.info(f"Query: {request.message}")
    result = process_query(request.message)
    logger.info(f"Status: {result['status']}")
    return result


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    try:
        db = get_db()
        tables = db.get_usable_table_names()
        return {"status": "ok", "tables": len(tables), "engine": "langchain+groq"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/api/tables")
async def list_tables():
    """List all available tables and their descriptions."""
    from utils import TABLE_DESCRIPTIONS
    db = get_db()
    tables = db.get_usable_table_names()
    return {
        "tables": [
            {"name": t, "description": TABLE_DESCRIPTIONS.get(t, "")}
            for t in tables
        ]
    }
