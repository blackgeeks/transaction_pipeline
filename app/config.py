import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "jobs.db"

ALLOWED_EXT = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm", ".aiff"}
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", 100))
MAX_DURATION_SEC = int(os.getenv("MAX_DURATION_SEC", 3 * 60 * 60))
CHUNK_SEC = int(os.getenv("CHUNK_SEC", 600))

BACKEND = os.getenv("TRANSCRIBER", "whisper")
MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")
DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE", "int8")

WORKERS = int(os.getenv("WORKERS", 2))
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", 3))
API_KEY = os.getenv("API_KEY", "")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
