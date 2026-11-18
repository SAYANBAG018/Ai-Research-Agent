# Research Studio — React + FastAPI

A modern React/Tailwind dashboard for the existing Python multi-agent research pipeline. The Python search, scraping, source-screening, writing, critic and export modules remain the research engine. FastAPI exposes the workflow to React and streams progress events using Server-Sent Events (SSE).

## Project layout

```text
research-react-app/
├── backend/
│   ├── main.py                 # FastAPI endpoints + background jobs + SSE
│   ├── agents.py               # Existing LangChain agents/chains
│   ├── pipeline.py             # Existing pipeline + optional progress callback
│   ├── tools.py                # Updated Tavily/search/scraping tools
│   ├── research_quality.py     # Source screening
│   ├── report_export.py       # Markdown/PDF export
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    ├── package.json
    └── .env.example
```

## 1. Configure the backend

Use Python 3.10+ (Python 3.11 is a good default).

**Windows PowerShell**

```powershell
cd research-react-app\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `backend/.env` and add valid `GROQ_API_KEY` and `TAVILY_API_KEY` values. The current `agents.py` explicitly requires the Groq key; web search requires the Tavily key.

**macOS / Linux**

```bash
cd research-react-app/backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

If you want the Playwright scraper fallback, install its browser once after installing requirements:

```bash
python -m playwright install chromium
```

Playwright is an optional fallback in `tools.py`; the other extraction paths can still be used without its browser installed.

## 2. Start the FastAPI backend

Run this from the `backend` directory so the existing pipeline modules and generated report directory resolve consistently:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Check `http://localhost:8000/api/health` and open the interactive API docs at `http://localhost:8000/docs`.

## 3. Start the React frontend

In a second terminal:

```bash
cd research-react-app/frontend
npm install
```

Copy the frontend environment file:

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# macOS / Linux
cp .env.example .env
```

Then run:

```bash
npm run dev
```

Open `http://localhost:5173`.

## API overview

- `GET /api/health` — backend health check.
- `POST /api/research` — accepts `{ "topic": "..." }` and returns a `job_id`.
- `GET /api/jobs/{job_id}` — returns job status and completed report metadata.
- `GET /api/jobs/{job_id}/events` — SSE stream of pipeline stage updates.
- `GET /api/jobs/{job_id}/download/markdown` — downloads the Markdown export.
- `GET /api/jobs/{job_id}/download/pdf` — downloads the PDF export.

## Important notes

- The API stores job state in process memory. Restarting the backend clears job history; use a database/Redis queue if you later deploy multiple workers or need durable jobs.
- This starter allows one in-process background thread per research request. Add authentication, rate limits and a durable task queue before exposing it publicly.
- The SSE stream reports pipeline-stage progress. The underlying current scraper runs its selected URLs concurrently, but does not emit a separate event for each URL.
- Source-domain screening and successful extraction are not factual verification. Review report citations and evidence before relying on findings.
- Do not commit `.env` or publish API keys.

## Build the frontend for production

```bash
cd frontend
npm run build
```

The production bundle is created in `frontend/dist`. Deploy it to a static host and set `VITE_API_URL` to the deployed FastAPI origin. Update backend `CORS_ORIGINS` to include the exact frontend origin.
