# LinkedIn AI Coach

**Grammarly for your LinkedIn profile.** Paste your profile text and get a
multi-dimensional score, ML-calibrated overall rating, career-match prediction, an
AI writing assistant (Gemini), and prioritized recommendations.

> Not affiliated with LinkedIn. **No scraping** — analysis runs on text you paste.

```
┌ frontend/  React + TypeScript + TailwindCSS + Recharts
└ backend/   FastAPI + SQLAlchemy + scikit-learn (RandomForest) + Gemini
```

## Features

- **Eight scores** (each deterministic, with its formula + factor breakdown shown): Overall ·
  Completeness · Technical Strength · Recruiter Appeal · **ATS Score** · **Leadership** · Networking ·
  Career Readiness. ATS and Leadership are transparent lenses over the same signals; `overall` keeps
  its calibrated rule+ML blend.
- **ML overall score** — `RandomForestRegressor` over **16 engineered features**, trained to a
  defensible rubric (LinkedIn All-Star + recruiter heuristics) and blended 50/50 with rule-based
  signals. Calibrated to recruiter-realistic bands (CV R² ≈ 0.98). See `backend/ml/MODEL_CARD.md`.
- **Career prediction** — % match for Data Scientist, Data Analyst, AI Engineer, Software Developer, Business Analyst, ML Engineer
- **Four input modes** — paste text; **import from a compliant URL** (GitHub via the official
  API, a portfolio site, or a job posting — never LinkedIn); or **upload a file**:
  a PDF resume / "Save to PDF", a `.txt`, or your **LinkedIn data-export `.zip`** (Settings →
  Get a copy of your data). The zip's CSVs are rebuilt into sectioned text and flow through the
  same pipeline. Endpoints: `POST /api/v1/analyze/upload`, `POST /api/v1/fetch`.
- **AI writing assistant** — improved headline + About section via a pluggable provider:
  **Gemini** (default) or **Azure OpenAI** (`AI_PROVIDER`), with a deterministic template
  fallback when neither is configured
- **Impact-prioritized recommendations** — strengths, weaknesses, and fixes ranked by their
  estimated effect on your overall score (e.g. "Expand your About → ~+12 pts"), each with a
  concrete, copy-pasteable **worked example** (rewritten headline, quantified bullet, named certs)
- **Export your report** — download a **server-generated recruiter-style PDF** (ReportLab:
  executive summary, score breakdown *with formulas*, dimension & career charts, ATS readiness,
  skill-gap, learning roadmap, recruiter feedback), or export **Markdown** / **JSON**, or **Print**
- **Dashboard** — score cards, radar chart, career bar chart, recommendation panels

## Quick start

### 1. Backend (port 8000)

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate        # Windows Git Bash
#  source .venv/bin/activate         # macOS / Linux
pip install -r requirements.txt
python -m ml.train                   # Phase 2: trains ml/model.pkl
cp .env.example .env                 # optional: add GEMINI_API_KEY for real AI
uvicorn main:app --reload --port 8000
```

API docs at `http://localhost:8000/docs`.

### 2. Frontend (port 5173)

```bash
cd frontend
npm install
cp .env.example .env                 # VITE_API_BASE=http://localhost:8000/api/v1
npm run dev
```

Open `http://localhost:5173`, go to **Analyze**, paste a profile (or click
"Load a sample profile"), and view the dashboard.

## Deploy (single service, no Docker)

In production the FastAPI backend **also serves the built React app**, so it's one
deployable service on one port. When `frontend/dist/` exists, `/` serves the app and
`/api/v1/*`, `/health`, `/docs` serve the API; otherwise `/` returns JSON (dev mode).

**Build, then start:**

```bash
bash build.sh                                   # installs deps, trains model, builds frontend
cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

`build.sh` requires Python **and** Node on the host. The model (`ml/model.pkl`) and the
frontend build (`frontend/dist/`) are generated here — both are git-ignored.

**On a PaaS (Render / Railway / etc.):**

| Setting | Value |
| --- | --- |
| Build command | `bash build.sh` |
| Start command | `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT` (or use the `Procfile`) |
| Env vars | `GEMINI_API_KEY` (optional), `GEMINI_MODEL=gemini-flash-latest` |

Same-origin requests mean **no CORS config needed**. If you instead host the frontend
separately, set `frontend/.env.production` → `VITE_API_BASE=https://<backend>/api/v1`
and add that frontend origin to `CORS_ORIGINS` on the backend.

> Note: the default DB is SQLite (file-based) — fine for a demo, but on hosts with an
> ephemeral filesystem the data resets on restart. Point `DATABASE_URL` at Postgres to persist.

### Cloud providers (abstraction-first, local fallback)

Every external dependency runs locally by default and "lights up" on Azure when the
matching env vars are set — no code change, no Azure account required for local dev:

| Capability | Local default | Azure (env-selected) | Switch |
| --- | --- | --- | --- |
| AI text generation | Gemini / deterministic templates | **Azure OpenAI** (REST, no extra SDK) | `AI_PROVIDER=azure` + `AZURE_OPENAI_*` |
| Report storage | local filesystem (`var/artifacts`) | **Azure Blob Storage** | `AZURE_BLOB_CONNECTION_STRING` (+ `pip install azure-storage-blob`) |
| Database | SQLite | Azure Database for PostgreSQL | `DATABASE_URL=postgresql+psycopg://…` |

`GET /health` reports the live `ai_provider` and `artifact_store`. Providers live behind
small interfaces (`services/ai_providers.py`, `services/storage.py`) so a different backend
slots in without touching routes or business logic.

## Architecture

Clean, layered, dependency-injected. The dependency rule points inward:
`routes → services → (utils / ml / models / database)`. Inner layers never
import FastAPI.

```
backend/
├── main.py                 # app assembly (CORS, routers, table creation)
├── config.py               # pydantic-settings (env-driven)
├── database/               # SQLAlchemy engine, Base, get_db (SQLite→Postgres)
├── models/                 # orm.py · schemas.py (Pydantic) · domain.py (dataclasses)
├── utils/                  # parser.py · text.py · constants.py (skills/roles)
├── ml/                     # features · train · predictor · model.pkl
├── services/               # scoring · recommendation · career · analysis · report
│                           # ai_service + ai_providers (Gemini | Azure OpenAI)
│                           # scrape_service (compliant fetch) · storage (local | Azure Blob)
└── routes/                 # health · analyze · assistant · career · sources · deps

frontend/
└── src/
    ├── pages/              # LandingPage · AnalyzePage · DashboardPage
    ├── components/         # ScoreGauge · ScoreCard · ScoreRadar · CareerChart · …
    ├── api/client.ts       # axios client (typed)
    ├── types/analysis.ts   # mirrors backend contract
    └── lib/format.ts       # score → color/label helpers
```

## API (`/api/v1`)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/analyze` | Full pipeline → dashboard payload |
| `POST` | `/analyze/upload` | Analyze an uploaded PDF / `.txt` / LinkedIn export `.zip` |
| `POST` | `/fetch` | Import profile text from a **compliant** source — GitHub (official API), a portfolio site, or a job posting (no LinkedIn) |
| `POST` | `/report/pdf` | Recruiter-style PDF from an analysis result (full fidelity) |
| `GET` | `/analyses/{id}/report.pdf` | Recruiter-style PDF for a stored analysis (cached in the artifact store) |
| `GET` | `/analyses/{id}` | Fetch stored analysis |
| `GET` | `/analyses` | History |
| `POST` | `/assistant/headline` | Improved headline |
| `POST` | `/assistant/about` | Improved About section |
| `POST` | `/career/predict` | Role-match percentages |
| `GET` | `/health` | Readiness (ai/ml status) |

## ML pipeline

No real LinkedIn data exists (scraping is against LinkedIn's ToS), so the model is
trained to a transparent **rubric** rather than to scraped labels:

```
ml/synthesize.py   realistic profile TEXT across the quality spectrum
   → utils/parser   the real runtime parser
   → ml/features    the real 16-feature extractor (train == serve, no drift)
   → ml/rubric      All-Star + recruiter "teacher" label (recruiter-realistic bands)
   → ml/train       RandomForest, 5-fold CV, archetype calibration → ml/model.pkl
```

`python -m ml.train` prints CV MAE/R², a per-archetype calibration table, and
feature importances. Details and limitations live in `backend/ml/MODEL_CARD.md`.

Run the test suite (scoring monotonicity, rubric bands, API contract):

```bash
cd backend && pytest -q
```

## Phases

1. **MVP (rule-based)** — parser, 6 calibrated scores, recommendations, career matcher, full UI. ✅
2. **ML** — rubric-labeled synthetic profiles + `RandomForestRegressor` (16 features) → `model.pkl`,
   blended into overall, with CV + calibration + tests. ✅
3. **AI** — Gemini headline/About/advice with fallback. ✅ (set `GEMINI_API_KEY`)

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | _(unset)_ | Enables Gemini writing assistant |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Generation model |
| `DATABASE_URL` | `sqlite:///./linkedin_coach.db` | Swap for Postgres URL |
| `ML_MODEL_PATH` | `ml/model.pkl` | Trained model location |
| `CORS_ORIGINS` | `localhost:5173` | Allowed frontend origins |

## Roadmap / extension points

- **PostgreSQL**: change `DATABASE_URL`; add Alembic migrations.
- **LinkedIn ingestion**: `source_type` already supports `url`/`export`; wire a
  compliant provider or the official export in `utils/parser.py` (return type is
  the only contract).
- **Browser extension**: can POST captured text to `/analyze` unchanged.
