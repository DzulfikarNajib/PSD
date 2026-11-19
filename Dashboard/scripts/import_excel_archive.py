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
from src.supabase_store import is_configured, replace_dataset_seed


def main():
    if not is_configured():
        raise SystemExit("Set SUPABASE_URL and SUPABASE_SECRET_KEY in Dashboard/.env before importing.")
    dataset = load_historical_data()
    if dataset.empty:
        raise SystemExit("Dataset OLX aktif tidak ditemukan atau tidak memiliki baris bersih DKI yang valid.")
    result = replace_dataset_seed(dataset)
    print(
        f"Sinkronisasi selesai: {result['dataset_rows_synced']} listing OLX bersih dipublikasikan; "
        f"{result['old_excel_rows_removed']} baris arsip Excel lama dan "
        f"{result['old_dataset_rows_removed']} seed OLX lama dihapus. "
        "Snapshot listing terbaru (olx_refresh) tetap disimpan terpisah."
    )


if __name__ == "__main__":
    main()
