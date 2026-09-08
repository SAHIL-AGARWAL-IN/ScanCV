---
title: ScanCV ATS Resume Scorer
emoji: 🎯
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# ATS Resume Scorer

A full-stack web app that scores how well a resume survives an Applicant Tracking System (ATS), explains *why* it got that score, and tracks your progress as you improve it.

Upload a resume (PDF / DOCX), optionally paste a job description, and get:

- An **overall ATS score (0–100)** with a plain-English interpretation
- A **breakdown across five components** — formatting, keywords, content quality, skill validation, ATS compatibility
- **Skill validation against evidence**: skills you list are checked against your own project and experience bullets (exact + semantic match), so "padded" skill lists get flagged
- **JD comparison** — keyword match percentage, semantic similarity, missing keywords, skills gap
- **Prioritized, actionable feedback** — issues grouped by severity with how-to-fix guidance and example rewrites
- **PDF report export** and a persistent per-user **analysis history** with a score-over-time trend

## Architecture

```
┌────────────────────┐         ┌─────────────────────────────────────────┐
│   Streamlit UI     │  HTTP   │              FastAPI backend            │
│  (port 8501)       │────────▶│                (port 8000)              │
│                    │  JWT    │                                         │
│  views/            │         │  api/routes.py      REST endpoints      │
│  components/       │         │  api/auth.py        Supabase JWT verify │
│  (Plotly charts,   │         │                                       │
│   Material icons)  │         │  services/                               │
│                    │         │   resume_parser     text extraction      │
│  auth via          │         │   groq_parser       LLM structured parse │
│  Supabase JS SDK   │         │   ats_scorer        5-component scoring  │
│                    │         │   jd_matcher        JD comparison        │
└─────────┬──────────┘         │   feedback_engine   issue detection      │
          │                    │   pdf_export        WeasyPrint reports   │
          ▼                    └───────────────┬─────────────────────────┘
   Supabase Auth ◀── tokens ───────────────────┘
   (email/password,                        │ service_role key
    Google OAuth)                          ▼
                                    Supabase Postgres
                                    (analyses table)
```

**Why this split?** Streamlit gives a fast, Python-only UI; FastAPI keeps the CPU/LLM pipeline separate from the UI process, so a slow analysis never freezes the app. Supabase handles both auth (JWTs the backend verifies against the project's JWKS — no session table to maintain) and storage (Postgres via its REST API — no ORM boilerplate).

## How the scoring works

The pipeline in `backend/services/resume_analyzer.py` runs these stages:

1. **Parse** — text extraction with pdfplumber (PyPDF2 fallback), then Groq (`openai/gpt-oss-120b`) extracts structured data: skills, experience entries, education, projects. The LLM prompt requires JSON; a malformed response is retried once with a stricter prompt before failing.
2. **Score** — five weighted components (`SCORE_WEIGHTS` in `backend/core/config.py`):
   | Component | Max | What it checks |
   |---|---|---|
   | Formatting | 20 | section presence, bullet density, summary length |
   | Keywords | 25 | skill/keyword coverage; fuzzy + alias matching against the JD when one is provided |
   | Content | 25 | action verbs, quantified achievements (`40%`, `$2M`, "grew by 3x"), grammar penalty |
   | Skill validation | 15 | each listed skill verified against project/experience bullets via substring + embedding cosine similarity |
   | ATS compatibility | 15 | penalties for street addresses/zip codes (privacy), table-drawing characters, too-short sections |
3. **Aggregate** — components are blended (skills & keywords 40%, content 30%, formatting 15%, ATS compat 15%), then bonuses (validated skills ≥90%, clean grammar) and penalties (missing JD keywords) are applied.
4. **Explain** — the feedback engine turns detected issues into severity-tagged cards (what's wrong, where it appears, how to fix, example rewrite), and the LLM writes the human-readable summary.

> ⚠️ **Honesty note:** the score is a heuristic informed by widely documented ATS parsing behavior — it is *not* a replication of any commercial ATS. It's most useful for relative comparison (before/after edits, resume A vs. resume B), not as an absolute predictor.

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| API | FastAPI | async, typed request/response models, automatic `/docs` |
| UI | Streamlit | pure-Python UI; Plotly for gauge/radar/trend charts |
| LLM | Groq API (`openai/gpt-oss-120b`) | fast structured extraction at low cost |
| NLP | spaCy `en_core_web_md` | NER for location/privacy detection |
| Embeddings | Sentence Transformers `all-MiniLM-L6-v2` | semantic skill↔evidence and resume↔JD similarity |
| Matching | RapidFuzz | typo-tolerant keyword matching (JD "pyton" ↔ resume "python") |
| Auth + DB | Supabase | managed Postgres + JWT auth; backend verifies ES256 tokens via JWKS |
| PDF export | WeasyPrint + Jinja2 | server-rendered reports from HTML templates |

## Project structure

```
ai-resume-ats/
├── backend/
│   ├── api/               REST routes, JWT auth dependency
│   ├── core/              config + env loading
│   ├── database/          Supabase REST client
│   ├── models/            Pydantic request/response schemas
│   ├── services/          parsing, scoring, matching, feedback, PDF export
│   └── utils/             logging, fuzzy matching, file helpers
├── frontend/
│   ├── views/             scorer, history, landing pages
│   ├── components/        score display, dashboard, feedback cards
│   ├── services/          API client
│   └── assets/            styles.css (design tokens + components)
├── tests/                 pytest suite (offline — no keys needed)
├── jupyter notebooks/     research and dataset prep (not used at runtime)
├── requirements.txt       combined backend + frontend dependencies
└── .env.example           template for environment variables
```

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd ai-resume-ats
python -m venv venv
source venv/bin/activate         # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_md
```

WeasyPrint needs system libraries on Linux:

```bash
# Fedora
sudo dnf install -y cairo pango gdk-pixbuf2 libffi
# Debian / Ubuntu
sudo apt install -y libcairo2 libpango-1.0-0 libpangoft2-1.0-0 libffi-dev
```

On Windows, `python-magic-bin` (already in requirements) bundles the libmagic DLL.

### 3. Configure environment variables

```bash
cp .env.example .env
```

You need:

- A **Supabase** project — `SUPABASE_URL`, `SUPABASE_KEY` (service role), `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET` from Project Settings → API.
- A **Groq** API key from [console.groq.com](https://console.groq.com).
- The `analyses` table (id uuid, user_id uuid, filename text, ats_score int, keyword_match int, analysis_result jsonb, created_at timestamptz).
- (Optional) Google OAuth in the Supabase dashboard for Google sign-in.

The Streamlit frontend also reads Supabase config from `frontend/.streamlit/secrets.toml` (copy `secrets.toml.example`).

### 4. Run the backend

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: `http://localhost:8000/docs`. On Windows, if you hit native-library load failures, see `backend/logs/` and ensure the venv's Scripts dir is first on PATH.

### 5. Run the frontend

```bash
streamlit run frontend/streamlit_app.py
```

Opens at `http://localhost:8501`.

### 6. Run the tests

```bash
python -m pytest tests/ -v
```

49 tests cover the scoring engine (component scores, clamping, aggregation), keyword matching (aliases, fuzzy thresholds), file validation (size limits, MIME checks, the Windows .docx fallback), and JWT auth (forged-token verification, expiry, audience, algorithm restriction). They run fully offline — no Supabase, Groq, or model downloads required.

## Screenshots

<!-- TODO: add 2-3 screenshots — score dashboard (gauge + radar), feedback tabs, history trend -->

## Notes

- **Never commit `.env` or `secrets.toml`** — they hold API keys. Both are in `.gitignore`; check before you push.
- The first run downloads the Sentence Transformer model (~80 MB). It's cached afterwards.
- If you don't have a Groq key yet, the scoring still works — only the LLM-written suggestions section will be empty.
- `jupyter notebooks/` is for experimentation and isn't required to run the app.
