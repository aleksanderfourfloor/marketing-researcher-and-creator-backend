# Competitor Analysis API

FastAPI backend for a competitor analysis tool: SQLite + AskNews API for data, Celery + Redis for background jobs, OpenAI/Anthropic for AI insights, PDF/CSV export.

## Tech Stack

- **Framework**: FastAPI
- **Database**: SQLite with SQLAlchemy ORM (async: aiosqlite)
- **Data source**: AskNews API (news, web content, market presence)
- **AI**: OpenAI GPT-4 or Anthropic Claude
- **Background jobs**: Celery + Redis
- **Export**: PDF (reportlab), CSV/ZIP

## Setup

1. **Create virtualenv and install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Environment**

   Copy `.env.example` to `.env` and set:

   - `DATABASE_URL` – SQLite path (default: `sqlite+aiosqlite:///./competitor_analysis.db`)
   - `ASKNEWS_CLIENT_ID` / `ASKNEWS_CLIENT_SECRET` – AskNews API
   - `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` – for AI insights
   - `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` – Redis URL (e.g. `redis://localhost:6379/0`)
   - `CORS_ORIGINS` – frontend origin (e.g. `http://localhost:3000`)

3. **Run API**

   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

   Tables are created on startup. Docs: http://localhost:8000/docs

4. **Run Celery worker** (optional, for background analysis)

   ```bash
   celery -A app.tasks.analysis_tasks worker -l info
   ```

   Requires Redis. If Redis is not running, `POST /api/analysis/run` still creates the run; the task will not execute until a worker is available.

## Project Structure

```
app/
├── main (via app/__init__.py)  # FastAPI app, CORS, lifespan
├── config.py                   # Pydantic Settings
├── database.py                 # Async engine + sync engine for Celery
├── models/                     # SQLAlchemy: competitors, analysis_runs, news_mentions, etc.
├── schemas/                    # Pydantic: request/response
├── api/                        # Routes: competitors, analysis, insights, export
├── services/                   # AskNews, NewsService, WebExtraction, Intelligence
├── ai/                         # InsightsGenerator, NewsAnalyzer (LLM)
├── tasks/                      # Celery: run_full_analysis, collect_news, etc.
└── export/                     # PDFGenerator, CSVExporter
alembic/                        # Migrations (optional; tables created on startup)
```

## API Overview

| Method | Endpoint                               | Description                           |
| ------ | -------------------------------------- | ------------------------------------- |
| POST   | `/api/competitors`                     | Create competitor                     |
| GET    | `/api/competitors`                     | List competitors                      |
| GET    | `/api/competitors/{id}`                | Get competitor                        |
| PUT    | `/api/competitors/{id}`                | Update competitor                     |
| DELETE | `/api/competitors/{id}`                | Delete competitor                     |
| POST   | `/api/competitors/bulk`                | Bulk create (JSON)                    |
| POST   | `/api/competitors/bulk/csv`            | Bulk upload CSV                       |
| POST   | `/api/analysis/run`                    | Start analysis (enqueues Celery task) |
| GET    | `/api/analysis`                        | List analyses                         |
| GET    | `/api/analysis/{id}`                   | Get analysis                          |
| GET    | `/api/analysis/{id}/status`            | Status only                           |
| GET    | `/api/insights/{analysis_id}`          | Get insights                          |
| POST   | `/api/insights/generate/{analysis_id}` | Trigger AI insight generation         |
| GET    | `/api/export/{analysis_id}/pdf`        | Download PDF report                   |
| GET    | `/api/export/{analysis_id}/csv`        | Download ZIP of CSVs                  |
| GET    | `/api/health`                          | Health check                          |

## Success Criteria

- [x] Database models with relationships
- [x] AskNews service (news search, web content, sentiment, trends)
- [x] Competitors CRUD + bulk CSV
- [x] Analysis run + background task pipeline
- [x] AI insights and differentiation opportunities
- [x] PDF and CSV/ZIP export
- [x] Error handling and CORS
