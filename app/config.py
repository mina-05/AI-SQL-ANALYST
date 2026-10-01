import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent


def _path(value: str) -> str:
    p = Path(value)
    return str(p if p.is_absolute() else BASE_DIR / p)


# MySQL (the database being analysed)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "analyst_ro")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "company")
MAX_ROWS = int(os.getenv("MAX_ROWS", "500"))

# LLM (Ollama)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

# RAG over business documents
KNOWLEDGE_DIR = _path(os.getenv("KNOWLEDGE_DIR", "knowledge"))
RAG_MODE = os.getenv("RAG_MODE", "keyword")  # "keyword" or "embeddings"

# Agent + memory
AGENT_MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "6"))
HISTORY_TURNS = int(os.getenv("HISTORY_TURNS", "4"))

# App accounts, query history (SQLite file)
APP_DB_PATH = _path(os.getenv("APP_DB_PATH", "data/app.db"))
ALLOW_REGISTRATION = os.getenv("ALLOW_REGISTRATION", "true").lower() == "true"
TOKEN_HOURS = int(os.getenv("TOKEN_HOURS", "12"))

SECRET_KEY = os.getenv("SECRET_KEY", "")
SECRET_KEY_IS_RANDOM = not SECRET_KEY or SECRET_KEY.startswith("change")
if SECRET_KEY_IS_RANDOM:
    SECRET_KEY = secrets.token_urlsafe(48)  # logins reset on every restart
