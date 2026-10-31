from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
EXPORT_DIR = DATA_DIR / "exports"
REPORT_DIR = PROJECT_ROOT / "reports"
DB_PATH = DATA_DIR / "factorymind.db"
SEED = 20261022
HORIZON_DAYS = 14
MINUTES_PER_DAY = 24 * 60
SHIFT_START = 8 * 60
SHIFT_END = 16 * 60
