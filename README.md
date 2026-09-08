# ARGUS — Autonomous AI Reliability & Recovery Platform

Full specification: [`docs/ARGUS_SPEC.md`](docs/ARGUS_SPEC.md) — read this
first, it's the source of truth for every phase of this build.

## Current status: Phase 1 complete and verified ✅

- FastAPI app boots (`backend/app/main.py`)
- Config loads with graceful fallback for every optional integration —
  LLM, LangSmith, Redis, Vector DB all work in "not configured" mode
  without crashing (`backend/app/config.py`)
- Structured JSON logging (`backend/app/logging_config.py`)
- 6 database models: Incident, MetricSnapshot, Diagnosis, RecoveryAction,
  Evaluation, AuditLog (`backend/app/database/models.py`)
- `/health` endpoint reporting the live status of every service
  individually — verified working
- **2/2 tests passing** (`backend/tests/test_health.py`)

Everything from here forward (simulation engine, ML detection, RAG,
LangGraph agents, MCP tools, human approval, LangSmith, frontend, MLOps)
is unbuilt — that's intentional. See `ANTIGRAVITY_TASKS.md` for the exact
phase-by-phase prompts to build it out in Google Antigravity.

## Quick start (Phase 1 only, right now)

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # edit if you have Postgres running, otherwise:
export DATABASE_URL="sqlite:///./dev.db"   # quick local override, no Postgres needed

uvicorn app.main:app --reload
```

Then visit `http://localhost:8000/health` — you'll see every integration's
real status (DB connected/not, LLM configured/not, etc.).

Run tests:
```bash
pytest tests/ -v
```

## Full stack with Docker

```bash
cp backend/.env.example backend/.env   # fill in what you have
docker-compose up --build
```

## Building it out with Google Antigravity

Open this folder as an Antigravity workspace, then work through
**`ANTIGRAVITY_TASKS.md`** one phase at a time — it mirrors
`docs/ARGUS_SPEC.md` Section 33 exactly. Do not skip ahead; do not let the
agent mark a phase "done" until its tests actually pass, per Section 34's
rules against fabricated results.

## Project structure

See `docs/ARGUS_SPEC.md` Section 5 for the complete intended structure —
the scaffold here matches it exactly so later phases have a clear home for
every new file.
