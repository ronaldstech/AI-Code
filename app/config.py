import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

PROJECT_CONFIG = BASE_DIR / "project.json"

OLLAMA_URL = "http://127.0.0.1:11434"

OLLAMA_CHAT_URL = f"{OLLAMA_URL}/api/chat"

MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

OLLAMA_TIMEOUT = 300

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "local_coding_ai")