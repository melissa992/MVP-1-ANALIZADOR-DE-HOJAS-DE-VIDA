import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

STORAGE_DIR = Path(os.getenv("APP_STORAGE_DIR", "temp_storage"))
