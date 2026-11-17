"""Idempotently import the active cleaned OLX dataset into Supabase."""

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
from src.supabase_store import import_dataset_seed, is_configured


def main():
    if not is_configured():
        raise SystemExit("Set SUPABASE_URL and SUPABASE_SECRET_KEY in Dashboard/.env before importing.")
    dataset = load_historical_data()
    if dataset.empty:
        raise SystemExit("Dataset OLX aktif tidak ditemukan atau tidak memiliki baris bersih DKI yang valid.")
    inserted = import_dataset_seed(dataset)
    print(f"Import selesai: {inserted} baris baru dari {len(dataset)} listing OLX bersih. Aman dijalankan ulang.")


if __name__ == "__main__":
    main()
