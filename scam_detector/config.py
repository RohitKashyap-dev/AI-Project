import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PREDICTIONS_DIR = DATA_DIR / "predictions"
LOGS_DIR = PROJECT_ROOT / "logs"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"

DEFAULT_DATASET_PATH = RAW_DATA_DIR / "dataset.csv"
DEFAULT_PREDICTIONS_PATH = PREDICTIONS_DIR / "predictions.csv"
DEFAULT_DRY_PREDICTIONS_PATH = PREDICTIONS_DIR / "predictions_dry.csv"
LOG_FILE_PATH = LOGS_DIR / "scam_analyzer.log"

MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-3.1-flash-lite")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.0"))
MAX_EVAL_EXAMPLES = int(os.environ.get("MAX_EVAL_EXAMPLES", "1000"))

LOGS_DIR.mkdir(parents=True, exist_ok=True)
PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
