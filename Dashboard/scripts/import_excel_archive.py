"""Idempotently import the project's cleaned Excel archive into Supabase."""

from pathlib import Path
import sys

from dotenv import load_dotenv

# Running ``python scripts/import_excel_archive.py`` puts only scripts/ on
# sys.path. Add the project root so imports from src/ work from any directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from src.data_loader import load_historical_data
from src.supabase_store import import_excel_seed, is_configured


def main():
    if not is_configured():
        raise SystemExit("Set SUPABASE_URL and SUPABASE_SECRET_KEY in Dashboard/.env before importing.")
    archive = load_historical_data()
    if archive.empty:
        raise SystemExit("Dataset Excel tidak ditemukan atau tidak memiliki baris DKI yang valid.")
    inserted = import_excel_seed(archive)
    print(f"Import selesai: {inserted} baris baru dari {len(archive)} listing Excel valid. Aman dijalankan ulang.")


if __name__ == "__main__":
    main()
