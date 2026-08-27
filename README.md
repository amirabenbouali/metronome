# Metronome

City pulse dashboard: traffic, transit, weather, and event data fused into a per-zone score, shown on a live map.

## Stack

- **Backend**: FastAPI (Python), async SQLAlchemy
- **Database**: Postgres + PostGIS
- **Frontend**: React + Vite + TypeScript, MapLibre GL (tiles via [OpenFreeMap](https://openfreemap.org), free and no API key required)

## Local development

### 1. Database

```bash
cp .env.example .env
docker compose up -d postgres
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Health check: `curl http://localhost:8000/health`

### 3. Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open http://localhost:5173

## Repo layout

```
backend/
  app/
    api/routes/   # FastAPI routers
    core/         # settings
    db/           # SQLAlchemy engine/session/base
    models/       # ORM models (PostGIS geometry columns go here)
    schemas/      # Pydantic schemas
    services/     # ingestion + scoring logic
frontend/
  src/
    components/   # MapView, panels, etc.
    lib/          # API client
docker-compose.yml  # Postgres/PostGIS for local dev
```
