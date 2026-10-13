import os
import sys
from pathlib import Path

os.environ.setdefault("GEMINI_API_KEY", "pytest-validation-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
