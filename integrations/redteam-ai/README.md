# RedTeam AI

Automated reconnaissance and red-teaming agent system.

## Stack

- **Backend**: Python FastAPI + Celery + Redis + SQLite
- **Frontend**: Next.js 16 + React 19 + Tailwind CSS v4
- **Tools**: subfinder, httpx, naabu

## Quick Start

### Docker (recommended)

```bash
docker compose up --build
```

- API: http://localhost:8000
- Dashboard: http://localhost:3000

### Manual

**Backend:**

```bash
cd api
python -m venv venv && source venv/bin/activate
pip install -e ".[test]"
# Terminal 1: uvicorn main:app --reload --port 8000
# Terminal 2: celery -A worker.celery worker --loglevel=info
# Terminal 3: redis-server
```

**Frontend:**

```bash
cd dashboard
cp .env.example .env.local
npm install
npm run dev
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Health check |
| `GET /scan?domain=` | Queue a recon scan |
| `GET /result/{task_id}` | Poll scan result |
| `GET /history` | View all past scans |
| `GET /agent?task=` | Run an AI agent |

## Agents

- **ReconAgent** — Multi-step recon: subdomain enum → HTTP probe → port scan
- **ReportAgent** — Generate structured security reports
- **OrchestratorAgent** — Full workflow: recon + report
