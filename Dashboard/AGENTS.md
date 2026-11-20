# AutoMatch — Agent Memory File

> Read this file first. Skip scanning `data/` or raw assets unless explicitly asked.

---

## File Map

| File | Purpose |
|------|---------|
| `app.py` | Streamlit entry point. Sets page config, applies theme, renders sidebar brand + `st.page_link` nav, and runs the active page. |
| `src/styles.py` | All CSS injected via `apply_theme()`. Sidebar, cards, KPI, tabs, buttons, responsive rules. Edit here for global visual changes. |
| `src/ui_components.py` | Reusable components: `kpi_card()`, `page_header()`, `insight_card()`, `section_card()`, `price_deviation_barometer()`, `get_lucide_icon()`. Design tokens (`NAVY`, `TEAL`, `CHART_COLORS`) live here too. |
| `pages/ikhtisar_pasar.py` | Page 1 — Market overview: hero banner, 4 KPIs, brand/region/fuel charts, insight cards. |
| `pages/eksplorasi_data.py` | Page 2 — Data exploration: price histogram, top makes, body-type, year vs price, km vs price, region bar. |
| `pages/preprocessing_segmentasi.py` | Page 3 — Preprocessing funnel + K-Means segmentation PCA scatter. |
| `pages/evaluasi_model.py` | Page 4 — Model evaluation: MAE/RMSE/R² KPIs, Actual vs Predicted, Residual plot, Feature Importance. |
| `pages/cek_harga_iklan.py` | Page 5 — Price checker: form input → ML estimate → gauge barometer → comparable listings. |
| `pages/kesimpulan.py` | Page 6 — Conclusions & recommendations: insight cards + recommendation list. |
| `src/data_loader.py` | Loads & caches `data/archive.parquet` and model metadata JSON. |
| `src/model_utils.py` | ML prediction helpers: `predict_price()`, `get_feature_importance()`, `cluster_market_segments()`. |
| `tests/` | 37 pytest tests. Run `.\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short` before every push. |
| `assets/` | Logo PNGs and hero image. Do not rename files; paths are hardcoded in `app.py`. |

---

## Design System — Chronicle / Shadcn UI Style

### Color Palette (Blue Monochromatic)

```
Background page:  #F8FAFC
Surface (card):   #FFFFFF
Border:           #E2E8F0
Text primary:     #0F172A
Text muted:       #475569 / #64748B
Accent blue:      #2563EB  (primary)
                  #1E40AF  (dark)
                  #3B82F6  (medium)
                  #60A5FA  (light)
                  #93C5FD  (lighter)
Amber (median):   #F59E0B  (keep for annotation lines only)
```

### Card Rules

- `background: #FFFFFF`
- `border: 1px solid #E2E8F0`
- `border-radius: 10px`
- `box-shadow: none`
- Use `st.container(border=True)` to group chart + title together — no floating titles outside a card.

### Sidebar Rules

- Background: `#F8FAFC`, right border `1px solid #E2E8F0`
- Brand icon: `background: #EFF6FF`, SVG stroke `#2563EB`
- Inactive links: color `#64748B`
- Active pill: background `#E2E8F0`, color `#0F172A`, font-weight `700`
- No institutional footer (IPB / STA1381) — it is hidden via `.am-sidebar-footer { display:none }`.

### Icons — Mandatory Lucide SVG

- **Never use OS emoji** (🚗 🏷️ 📈 etc.) anywhere — not in page titles, KPI labels, badges, or markdown.
- Always use `get_lucide_icon(name, size=16, color="#64748B")` from `src/ui_components.py`.
- Available slugs: `car`, `tag`, `banknote`, `calendar`, `trending-up`, `bar-chart-2`, `search`, `check-circle`, `settings`, `activity`, `target`, `gauge`, `trophy`, `map-pin`, `zap`, `info`, `pie-chart`, `layers`, `git-branch`, `database`, `sliders`, `cpu`, `award`, `arrow-up-right`, `arrow-down-right`, `minus`, `layout-dashboard`.

### Typography

```
Headings:   "Plus Jakarta Sans", Inter, system-ui — font-weight 800, letter-spacing -0.025em
Body:       Inter, "Segoe UI", system-ui
KPI label:  0.78rem, weight 500, #64748B
KPI value:  1.75rem, weight 700, #0F172A
```

### Chart Colors (Plotly)

Always use this blue palette — no teal (`#008B8B`), no old navy (`#0B2A5B`):

```python
CHART_COLORS = ["#2563EB", "#3B82F6", "#60A5FA", "#1E40AF", "#93C5FD", "#94A3B8", "#475569", "#1D4ED8"]
```

Amber `#F59E0B` is allowed **only** for median/reference lines.

---

## Token-Saving Rules

1. **Read `AGENTS.md` first** — do not scan `data/` or `assets/` unless the user explicitly asks.
2. Edit only the files relevant to the request. For color changes: `src/ui_components.py` + affected `pages/*.py`. For global style: `src/styles.py` only.
3. Run `pytest tests/ -q --tb=short` before any `git push`. All 37 tests must pass.
4. Git write ops (`add`, `commit`, `push`) require `BypassSandbox: true` on Windows.
5. Use `;` not `&&` in PowerShell command chains.

---

## Git

- Remote: `https://github.com/DzulfikarNajib/PSD.git`
- Branch: `main`
- Venv: `.\.venv\Scripts\python.exe`
