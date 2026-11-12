# AutoMatch

Interactive Streamlit decision support for exploring OLX Indonesia used-car listings, filtering cars in DKI Jakarta, comparing asking prices, and evaluating an optional regression model.

## 1. Project overview

Used-car buyers face listings with inconsistent specifications and limited price context. This application helps users explore the observed market, find listings by budget and vehicle attributes, compare similar advertisements, and review a data-based asking-price estimate when training data qualifies. It is decision support, not a vehicle inspection or a guarantee that a car is suitable to buy.

## 2. Data overview

- **Source:** The preserved Excel scrape is the seed archive. Every successful manual OLX refresh is appended as a timestamped Supabase snapshot. Search and model preparation combine the sources after URL/ID deduplication; source and observation counts remain visible.
- **Geography:** Five DKI Jakarta administrative cities (Central, South, East, West, North); Kepulauan Seribu and locations outside DKI are excluded.
- **Observation unit:** An API listing observation at `fetched_at`. The same `listing_id` may recur in history at a later time.
- **Fields:** Listing ID, make/model/variant, asking price and source text, year, mileage range and derived km, engine capacity and derived cc, fuel, transmission, body type, color, location, listing/image URLs, post time, seller type, and fetch time.
- **Coverage:** Current observation count, unique listing count, geographic and time coverage are calculated from the local CSVs; they are not hard-coded.
- **Interpretation:** OLX values are asking prices, not verified transaction values. Engine condition, accident/service history, and document status are not verified by the dataset.

## 3. Exploratory data analysis

Pahami Pasar uses the full validated historical DKI dataset for EDA and clearly labels it as an archive, not active inventory. Cari Mobil lets users switch between the latest OLX snapshot and historical archive. Cek Harga prefers current snapshot comparables and shows historical references separately when fewer than three current matches exist. Historical URLs may no longer work and have no collection date.

## 4. Data preprocessing

The API response is read from `raw`; expected columns are normalized while original text fields are retained. Prices accept Indonesian thousands separators. Year, mileage, and engine capacity are converted for analysis. A mileage range is represented by its midpoint (for example, 20,000–30,000 km becomes 25,000 km). Liter capacity is converted to cc (1.5 L becomes 1,500 cc); source text remains available beside the derived field.

The supplied workbook is preserved. A derived CSV maps its 19 source fields to the app schema. EDA/model rows require DKI Jakarta province plus one of five cities; Kepulauan Seribu and other cities are excluded. URL_Detail is normalized into listing_id and deduplicated. Prices below Rp1 million are excluded as implausible for a car; non-exact year labels are missing, mileage ranges use midpoints, and engine capacity bands use representative values. Excel has no capture date and is never assigned one. OLX refreshes are stored with a snapshot ID and Asia/Jakarta capture time. Repeated observations remain in the snapshot history for time analysis; search and training use one latest row per normalized listing identity.

## 5. Modeling

The optional target is `price` (asking price). Candidate features are make, model, year, mileage, engine capacity, transmission, fuel, and body type; variant is not used in v1 because its consistency has not been established. The app compares Linear Regression, Decision Tree Regressor, and Random Forest Regressor with imputation and one-hot encoding in scikit-learn pipelines.

Training is user-triggered and uses the validated combined archive, with one latest observation per normalized listing identity. A baseline requires at least 100 unique listings, 3 makes, and 5 models. The threshold is a conservative project gate, not a statistical guarantee of model quality. Evaluation uses a fixed-seed 80/20 holdout and reports MAE, RMSE, and R². The best pipeline is selected by lowest holdout MAE and refit on all eligible unique observations. Refresh never trains automatically. Predictions are withheld until a saved model and ready metadata exist.

Older model files without the current validation metadata version are treated as unvalidated and are not used for prediction. They remain on disk until a qualifying local training run replaces them.

Feature importance is shown only for tree models and describes model association, not cause and effect. Metrics from limited or changing marketplace snapshots should be treated cautiously.

## 6. Key insights

Pahami Pasar uses the combined unique archive for distributions and relationships; snapshot trends use timestamped OLX observations only. Beranda uses the latest saved DKI listing snapshot. Cari Mobil distinguishes the combined archive, latest snapshot, and Excel seed. Historical ads may no longer be active. The workbook is dominated by DKI Jakarta and does not represent every price or buyer segment in the full market.

## 7. Conclusion and recommendations

Use the app to narrow search and create price context, then independently inspect the vehicle, verify paperwork, and review service and accident records with qualified help. Asking-price comparisons and model estimates are references only. Future work can improve geographic query coverage, variant normalization, richer uncertainty estimates, and validated persistent storage.

## Project structure

```text
app.py                         Localized multipage navigation entry point
home.py                        Buyer-oriented home and manual refresh
pages/1_Explore_Market.py      EDA, snapshots, and quick links to search
pages/2_Find_Your_Car.py       Search, filters, comparison
pages/3_Price_Checker.py       Asking-price comparables and optional model
pages/4_Tentang_Proyek.py      Seven data-science project components
src/api_handler.py            Datawebot request and refresh orchestration
src/preprocessing.py          Parsing, validation, location, CSV writes
src/data_loader.py            CSV loading and snapshot timestamps
src/supabase_store.py         Supabase snapshot storage and archive import
src/modeling.py               Eligibility, evaluation, prediction
src/styles.py / src/ui.py      Theme and reusable presentation helpers
data/olx_live.csv              Latest valid DKI Jakarta snapshot
data/olx_history.csv           Append-only snapshot observations
data/PSD_DATA_MOBIL_JAKARTA_FULL.xlsx  Preserved historical source workbook
data/PSD_DATA_MOBIL_JAKARTA_FULL.csv   Derived CSV used by EDA and model
supabase/migrations/           Safe schema changes for persistent source labels and Excel seed rows
scripts/import_excel_archive.py Idempotent, explicit Excel-to-Supabase import (no OLX request)
models/                        Saved pipeline and evaluation metadata
tests/                         Mocked/local tests; no paid API calls
```

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env`; set `SUPABASE_URL` and `SUPABASE_SECRET_KEY`. Set `DATAWEBOT_API_KEY` only if you intend to refresh locally. Never commit `.env`.
4. Start the app: `streamlit run app.py`.
5. Listings refresh only after **Refresh Listings** is pressed. The app allows one to five OLX result pages per request (default one); larger page counts can use more API credits. Datawebot currently documents a five-page maximum for this OLX endpoint.

Run local, mocked tests with `pytest -q`. The paid live API smoke check is excluded from pytest. It requires explicit opt-in with `DATAWEBOT_LIVE_TEST=1` and running `python test_api.py`; this can consume Datawebot credits.

### Supabase archive setup

1. In Supabase SQL Editor, run `supabase/migrations/20261112_allow_excel_seed.sql`. This only allows unknown Excel capture dates and adds a source label; it does not delete existing rows.
2. Set `SUPABASE_URL` and a server-only `SUPABASE_SECRET_KEY` in local `.env` (or Streamlit Cloud Secrets).
3. Run `.venv/Scripts/python.exe scripts/import_excel_archive.py` once to seed the existing cleaned Excel archive. The fixed seed snapshot ID and conflict handling make reruns idempotent; it issues no Datawebot request.
4. Successful manual refreshes append OLX observations. Search combines the seed and snapshots, deduplicates by normalized URL/ID, and prefers the most recent OLX observation. The original XLSX remains unchanged.

## Secrets and deployment

Provide `DATAWEBOT_API_KEY` through the host's secret manager, not source code or committed files. The refresh control is manual and public to anyone who can reach the app; it changes the shared dataset and spends the shared API balance. For a public service, add authenticated administrator accounts and server-side rate limits before exposing refresh. Keep `.env` out of version control. The app reads and writes CSVs and model artifacts relative to its project directory. Hosted filesystems may be ephemeral: configure a persistent volume or external durable storage before relying on history, live data, or trained artifacts after restarts. Confirm the host's file-size, backup, and write-permission limits. If persistence is unavailable, rehydrate from a trusted store; the app does not fabricate replacement listings.
