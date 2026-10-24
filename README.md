# Wind Forecast Analytics

A professional, high-reliability analytics dashboard designed for UK electricity utilities and energy trading desks. The platform evaluates national UK wind generation forecasts against actual metered generation from official Elexon BMRS datasets for **January 2026** to inform power purchasing and imbalance risk decisions.

---

## 1. Business Objective

Energy traders and utility portfolio managers must evaluate Day-Ahead wind power forecasts before entering market commitments. Discrepancies between forecast and metered generation expose utilities to system buy/sell imbalance prices administered under the UK Balancing and Settlement Code (BSC).

This dashboard provides:
1. **Accuracy Auditing:** Quantifies Day-Ahead forecast accuracy through Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and Forecast Bias.
2. **Temporal Insights:** Side-by-side time-series visualizations contrasting actuals and forecasts on an identical UTC timeline.
3. **Cutoff Compliance:** Enforces market gate closures (e.g. Day-Ahead 17:00 UTC on D-1) to eliminate look-ahead bias and guarantee that only forecasts that were physically available at decision time are evaluated.
4. **Data Provenance & Traceability:** Detailed per-interval audit table with publication timestamps, individual signed/absolute errors, and one-click CSV export.

---

## 2. Technology Stack

- **Backend:**
  - **Python 3.12.10**
  - **FastAPI 0.162.0** (High-performance async ASGI web framework)
  - **Uvicorn 0.54.0** (Production ASGI web server)
  - **HTTPX 0.28.1** (Async HTTP client with connection pooling and timeouts)
  - **Pydantic 2.14.1** (Robust request validation and schema serialization)
  - **Pytest 9.1.1** (Unit and integration test suite)
  - *Standard Library (zero pandas dependency):* `datetime`, `math`, `statistics`, `zoneinfo`, `collections`.
- **Frontend:**
  - **React 19.3.1** (Modern component UI)
  - **Vite 8.3.5** (Fast development server and optimized rollup bundler)
  - **Vanilla CSS3** (Custom design system with midnight navy and emerald green accents, accessible contrast, responsive layout)
  - **Interactive Responsive SVG Visualizations** (Dual-series generation curve, signed error bar stems, crosshair inspection, zero external chart bundle bloat)
- **Containerization & Deployment:**
  - **Docker** (Multi-stage build)
  - **Docker Compose**

---

## 3. Project Structure

```
wind-forecast-analytics/
├── frontend/
│   ├── public/
│   │   └── favicon.svg
│   ├── src/
│   │   ├── components/
│   │   │   ├── DashboardHeader.jsx      # Header with health status & UTC timezone
│   │   │   ├── DateRangeFilter.jsx       # Period selection, Jan 2026 presets & policy picker
│   │   │   ├── MetricCard.jsx            # Summary KPI card (MAE, RMSE, Bias, Matched Count)
│   │   │   ├── GenerationChart.jsx       # Actual vs Forecast SVG time-series chart
│   │   │   ├── ForecastErrorChart.jsx    # Signed forecast error distribution chart
│   │   │   ├── GenerationTable.jsx       # Paginated interval table with CSV download
│   │   │   ├── LoadingState.jsx          # Accessible loading skeleton
│   │   │   └── ErrorState.jsx            # Error feedback and retry handler
│   │   ├── services/
│   │   │   └── api.js                    # Fetch client for backend API
│   │   ├── utils/
│   │   │   └── formatters.js             # MW units, signed numbers, and UTC date formatters
│   │   ├── App.jsx                       # Main application state orchestration
│   │   ├── main.jsx                      # React 19 entry point
│   │   └── index.css                     # Design system tokens and styling
│   ├── index.html                        # HTML entry point with meta tags
│   ├── package.json                      # Frontend scripts and dependencies
│   ├── eslint.config.js                  # ESLint configuration
│   └── vite.config.js                    # Vite configuration with /api backend proxy
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                       # FastAPI application entry & static SPA serving
│   │   ├── config.py                     # Environment variables, URLs, and policy defaults
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py                 # Endpoints (/api/health, /api/analysis)
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── elexon_client.py          # Async HTTP client for BMRS streams + cache
│   │   │   ├── data_processing.py        # Timestamp normalization, filtering, cutoff engine
│   │   │   └── metrics.py                # Pure Python MAE, RMSE, Bias calculations
│   │   └── schemas/
│   │       ├── __init__.py
│   │       └── responses.py              # Pydantic schemas for API responses
│   ├── tests/
│   │   ├── test_metrics.py               # Unit tests for statistical formulas
│   │   ├── test_data_processing.py       # Unit tests for cutoff policy & deduplication
│   │   └── test_api.py                   # API integration & error propagation tests
│   └── requirements.txt                  # Minimal verified Python dependencies
│
├── docs/
│   └── architecture.md                   # System architecture and Mermaid diagrams
├── .env.example                          # Environment variable configuration template
├── .gitignore                            # Git exclusion rules
├── .dockerignore                         # Docker build context exclusions
├── Dockerfile                            # Multi-stage container build
├── docker-compose.yml                    # Local container orchestration
└── README.md                             # Comprehensive technical documentation
```

---

## 4. Official Elexon Data Sources & Schema

The application connects to the official Elexon BMRS API endpoints:

1. **Actual Generation:**
   - URL: `https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream`
   - Parameters: `settlementDateFrom`, `settlementDateTo`
   - Filter: `fuelType == "WIND"`
   - Delivery Timestamp: `startTime` (UTC)
   - Value: `generation` in **Megawatts (MW)**
2. **Forecast Generation:**
   - URL: `https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream`
   - Parameters: `publishDateTimeFrom`, `publishDateTimeTo`
   - Delivery Timestamp: `startTime` (UTC)
   - Publication Timestamp: `publishTime` (UTC)
   - Value: `generation` in **Megawatts (MW)**

---

## 5. Forecast Cutoff Policies & Assumptions

In electricity trading, Day-Ahead positions are taken prior to physical delivery. The application enforces a strict cutoff threshold: **any forecast published after the cutoff is strictly ineligible**.

Supported Cutoff Policies:
- **`day_ahead_1200` (Default Auction Cutoff):** Cutoff is 12:00:00 UTC on the day prior to delivery ($D - 1$), matching EPEX SPOT Day-Ahead power auction clearing.
- **`day_ahead_1700` (Gate Closure):** Cutoff is 17:00:00 UTC on the day prior to delivery ($D - 1$), matching bilateral contract physical notification gate closure.
- **`gate_closure_1h`:** Cutoff is 1 hour prior to delivery interval start ($T_{\text{delivery}} - 1\text{h}$), matching UK Balancing Mechanism operational gate closure.
- **`latest_prior`:** Latest forecast published prior to or at delivery commencement ($T_{\text{delivery}}$).

### Tie-Breaking & Deduplication
If multiple forecasts share the identical latest publication time for the same delivery interval, ties are broken deterministically by secondary sorting on `(publishTime, generation, dataset)`. Silently picking arbitrary records is explicitly prohibited.

---

## 6. Error Definitions & Accuracy Metric Formulas

For each delivery interval $i$ where both forecast $F_i$ and actual $A_i$ are available:
$$\text{Error}_i = F_i - A_i$$

1. **Mean Absolute Error (MAE):**
   $$\text{MAE} = \frac{1}{N} \sum_{i=1}^N |F_i - A_i|$$
2. **Root Mean Squared Error (RMSE):**
   $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^N (F_i - A_i)^2}$$
3. **Forecast Bias (Mean Error):**
   $$\text{Bias} = \frac{1}{N} \sum_{i=1}^N (F_i - A_i)$$
   - Positive Bias ($> 0$): Systemic overforecasting.
   - Negative Bias ($< 0$): Systemic underforecasting.

---

## 7. Missing-Data & Defensible Resolution Handling

- **Resolution Disparity:** Metered actuals (`FUELHH`) operate at half-hourly resolution (48 settlement periods/day = 1,488 actual records for Jan 2026), whereas forecasts (`WINDFOR`) operate at hourly resolution (24 hours/day = 744 forecast intervals for Jan 2026).
- **Hourly Energy-Weighted Averaging (Recommended Default):**
  Each hour averages both 30-minute settlement periods ($\bar{A}_h = \frac{A_1 + A_2}{2}$ MW), matching the true electrical energy generated ($E = \bar{P} \times 1\text{h} = A_1 \times 0.5\text{h} + A_2 \times 0.5\text{h}$). This achieves **100.0% data coverage** (744 matched hours out of 744) and utilizes **100.0% of all 1,488 actual records** without discarding any observations.
- **Half-Hourly Settlement Period Mode:**
  Applies the Day-Ahead 1-hour block forecast to each 30-minute settlement period, enabling 100% coverage at the Balancing Mechanism settlement resolution (1,488 matched intervals).
- **Exact Timestamp Mode:**
  Strict string matching (:00 only), leaving :30 as unforecasted (50% coverage).
- **Empty Periods:** If no matched records exist, MAE, RMSE, and Bias safely return `null`, preventing division-by-zero errors.

---

## 8. Prerequisites & Environment Setup

- **Python:** 3.12.10 (virtual environment located at `.venv`)
- **Node.js:** 24.21.0 or higher
- **npm:** 11.19.0 or higher

### Environment Configuration
Copy `.env.example` to `.env` (optional):
```bash
cp .env.example .env
```

---

## 9. Startup Instructions (Local Development)

### Option A: Running Both Services Locally

**1. Start the FastAPI Backend (Terminal 1):**
```powershell
# From project root:
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
The API documentation is available at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

**2. Start the React Frontend (Terminal 2):**
```powershell
cd frontend
npm run dev
```
The React development dashboard is available at: [http://localhost:5173](http://localhost:5173) (Vite automatically proxies `/api` requests to `http://127.0.0.1:8000`).

---

### Option B: Unified Single-Server Mode
Because the React production build is located in `frontend/dist/`, running FastAPI directly serves both the API and the single-page application on port 8000:
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in any browser.

---

## 10. Test and Lint Commands

### Run Backend Tests:
```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -v
```

### Run Frontend ESLint:
```powershell
cd frontend
npm run lint
```

### Run Frontend Production Build:
```powershell
cd frontend
npm run build
```

---

## 11. Docker Instructions

### Building and Running with Docker:
```bash
docker build -t wind-forecast-analytics:latest .
docker run -p 8000:8000 --name wind-forecast-app wind-forecast-analytics:latest
```

### Or with Docker Compose:
```bash
docker compose up --build
```
Access the application at [http://localhost:8000](http://localhost:8000).

*Note on Docker Status:* On this Windows workstation, the Docker CLI is installed (`Docker version 29.8.1`), but the Docker Desktop daemon was not running during development (`pipe/dockerDesktopLinuxEngine` not found). The multi-stage `Dockerfile` and `docker-compose.yml` have been crafted to standards and are ready for deployment.

---

## 12. Deployment Instructions

### Cloud / PaaS Hosting (Render, Railway, Fly.io, AWS ECS, GCP Cloud Run)
1. Set the Docker build target using the included root `Dockerfile`.
2. Configure environment variables in your hosting provider:
   - `PORT=8000`
   - `DEFAULT_START_DATE=2026-01-01`
   - `DEFAULT_END_DATE=2026-01-31`
   - `DEFAULT_CUTOFF_POLICY=day_ahead_1200`
   - `DEFAULT_RESOLUTION=hourly`
   - `ELEXON_BASE_URL=https://data.elexon.co.uk/bmrs/api/v1`
3. Health check route: `GET /api/health`

---

## 13. Data Presentation & Rounding Integrity

- **Full-Precision Core Calculations:** Backend metrics and observation errors are computed at native floating-point precision and rounded only during response serialization (`round(..., 2)`).
- **Presentation Arithmetic Consistency:** In the UI table, row values dynamically synchronize their decimal places so that displayed Signed Error strictly equals displayed Forecast minus displayed Actual, and displayed Absolute Error equals `|Signed Error|` without visual 1 MW rounding discrepancies.
- **CSV Data Integrity:** Raw, unrounded metric values are exported to CSV for reproducible statistical auditing.

---

## 14. AI Tools Used & Contribution

- **Antigravity AI (Pair Programming Assistant):**
  - Architected the standard-library data processing pipeline without pandas to respect Windows Application Control restrictions.
  - Implemented the deterministic Day-Ahead cutoff selection engine and metrics formulas.
  - Resolved the 50% vs 100% resolution disparity with mathematically defensible energy-weighted averaging and block mapping.
  - Designed the executive responsive SVG charts and data table with pagination and CSV export.
  - Developed test suites covering edge cases, missing data, and upstream API error propagation.

---

## 15. Known Limitations & Next Steps

1. **Upstream Rate Limiting:** While Elexon's BMRS API stream endpoints are public and responsive, extreme date ranges (e.g. multi-year queries) could benefit from persistent database storage (e.g. PostgreSQL/TimescaleDB).
2. **Regional Zonal Breakdown:** The current implementation processes national totals. Expanding to regional transmission zones (DNO license areas) would provide granular local visibility.
