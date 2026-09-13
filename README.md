# DocSchema Agent

Multi-step **document → structured data** agent with verification, confidence flags, and CSV/JSON export.

Upload an invoice (or similar), extract schema fields, review uncertain cells, export CRM-ready data.

Sister to [ActionGate](https://github.com/muhammadbinriaz/actiongate-console): ActionGate *acts* with approval; DocSchema *extracts* with review.

## Demo story (60–90 seconds)

1. Open the app → upload `sample/invoice-orbitly.txt` (or paste text).
2. Agent classifies as **invoice**, extracts fields (vendor, amount, due date, line items).
3. Uncertain fields are flagged — edit one cell.
4. Export **JSON** or **CSV**.

## Stack

- **Frontend** — Next.js (App Router) + Tailwind
- **Backend** — FastAPI + extraction pipeline
- **DB** — PostgreSQL (jobs + extractions)
- **LLM** — Groq by default (OpenAI optional)
- **Docker Compose** — Postgres on **5434** (avoids DocBot 5432 / ActionGate 5433)

## Quickstart

### 1. Database

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
cp .env.example .env
# set GROQ_API_KEY
uv sync
# Windows App Control DLL issues:
#   .venv\Scripts\python.exe run_server.py
uv run uvicorn app.main:app --reload --port 8001
```

### 3. Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev -- --port 3012
```

Open [http://localhost:3012](http://localhost:3012).

## API (v1)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/jobs` | Create extraction job (text or upload) |
| GET | `/api/v1/jobs/{id}` | Job status + fields |
| PATCH | `/api/v1/jobs/{id}/fields/{key}` | Human edit a field |
| POST | `/api/v1/jobs/{id}/confirm` | Mark reviewed |
| GET | `/api/v1/jobs/{id}/export?format=json\|csv` | Download |

## License

Private portfolio piece.
