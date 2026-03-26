"""
Configuration for the chat interface backend.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent  # Dodge-AI root
ENTITIES_DIR = PROJECT_ROOT / "data-processing" / "output" / "entities"
GRAPH_DIR = PROJECT_ROOT / "graph-builder" / "output"

# Groq API
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3-32b")

# Query limits
MAX_RESULT_ROWS = 50
MAX_SQL_RETRIES = 2
