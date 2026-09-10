# ARGUS Deployment & Production Operations Guide (Phase 10)

This document provides production deployment, containerization, and operations instructions for **ARGUS — Autonomous AI Reliability & Recovery Platform** per `docs/ARGUS_SPEC.md` Sections 21, 25, and 33.

---

## 1. System Architecture

```text
┌────────────────────────────────────────────────────────┐
│               Web Browser / Engineer                   │
└───────────────────────────┬────────────────────────────┘
                            │ (Port 3000)
                            ▼
┌────────────────────────────────────────────────────────┐
│             Nginx Frontend Container                   │
│   - React 18 + TypeScript + Vite Static Assets         │
│   - Reverse Proxy: /api/ & /health -> backend:8000     │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP
                            ▼
┌────────────────────────────────────────────────────────┐
│             FastAPI Backend Container                  │
│   - RateLimitMiddleware (Sliding Window per IP)        │
│   - LangGraph State Machine Supervisor                 │
│   - MCP Tool Server (13 Tools, Allowlist Enforced)     │
│   - Local ONNX Embeddings (all-MiniLM-L6-v2)           │
│   - Structured JSON Logging (Section 25)               │
└───────────────┬────────────────────────┬───────────────┘
                │                        │
                ▼                        ▼
┌───────────────────────────┐ ┌───────────────────────────┐
│     PostgreSQL 16         │ │        ChromaDB           │
│  (Incidents, Recoveries,  │ │  (Runbooks & Historical   │
│   Audits, Metric Snapshots│ │   Resolved Incidents)     │
└───────────────────────────┘ └───────────────────────────┘
```

---

## 2. Environment Configuration (`.env`)

Create a `.env` file in `backend/` based on the configuration options below:

```bash
# Core Application Environment
ARGUS_ENV=production
APP_NAME=ARGUS
LOG_LEVEL=INFO

# PostgreSQL Database (Optional for local dev — falls back gracefully to in-memory)
DATABASE_URL=postgresql://argus:argus@localhost:5432/argus

# LLM Provider Configuration (Section 37.1)
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash
GOOGLE_API_KEY=your_google_ai_studio_api_key_here

# LangSmith Observability (Optional — falls back to local structured JSON logging)
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=argus-ai-reliability

# Vector Database Path
VECTOR_DB_PATH=data/vector_store

# Redis Cache (Optional)
REDIS_URL=
```

---

## 3. Local Development (Without Docker)

ARGUS is architected to run seamlessly on a local workstation without requiring Docker.

### 3.1 Start the Backend
```bash
# Navigate to backend and create/activate virtual environment
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI backend with live reload
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend boots at `http://127.0.0.1:8000`:
- Swagger API Docs: `http://127.0.0.1:8000/docs`
- Health Endpoint: `http://127.0.0.1:8000/health`
- Live Telemetry Stream: `http://127.0.0.1:8000/api/metrics`

### 3.2 Start the Frontend
```bash
# Open a new terminal in frontend/
cd frontend

# Install Node dependencies
npm install

# Start Vite development server with proxy to backend:8000
npm run dev
```

Access the UI dashboard at `http://localhost:3000`.

---

## 4. Production Deployment with Docker Compose

Deploy the complete multi-service stack with a single command:

```bash
docker compose up --build -d
```

### 4.1 Orchestrated Services & Healthchecks

| Service | Container Name | Port Mapping | Healthcheck Command | Dependency Order |
| :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL** | `argus-postgres` | `5432:5432` | `pg_isready -U argus` | Base service |
| **FastAPI Backend** | `argus-backend` | `8000:8000` | `python urllib GET /health` | `postgres: service_healthy` |
| **Nginx Frontend** | `argus-frontend` | `3000:80` | `wget -q -O /dev/null /` | `backend: service_healthy` |

Check container health status:
```bash
docker compose ps
```

View aggregated logs:
```bash
docker compose logs -f backend
```

Stop stack:
```bash
docker compose down
```

---

## 5. Security & Safety Review (Section 21 Checklist)

| Security Domain | Implementation | Verification |
| :--- | :--- | :--- |
| **No API Keys in Frontend** | Frontend strictly accesses relative routes (`/api/*`, `/health`). Backend masks keys in health reports. | Confirmed via source inspection and build bundle analysis. |
| **No Arbitrary Shell Execution** | Destructive shell execution is forbidden. All agent actions execute exclusively through allowlisted MCP tools. | Verified via `backend/app/mcp/server.py`. |
| **Action Authorization Gates** | High-risk tools (`restart_service`, `execute_rollback`) refuse execution without `approved=True`. LangGraph interrupts until human consent. | Enforced in tool functions and verified via `test_high_risk_tool_blocked_without_approval`. |
| **Audit Logging** | Immutable `AuditLog` rows recorded before and after execution of every action tool. | Enforced via `record_audit_log()` in database and memory. |
| **Rate Limiting** | `RateLimitMiddleware` enforces sliding-window limit (default 240 req/min per IP) returning HTTP 429 when breached. | Verified in `test_rate_limit.py`. |
| **No Secrets in Logs** | `JSONFormatter` filters and formats only structured metadata (`agent`, `action`, `duration`, `incident_id`, `status`). | Verified in `backend/app/logging_config.py`. |

---

## 6. Verification & Health Monitoring

Verify deployment health after boot:

```bash
# 1. Check overall infrastructure status
curl -s http://localhost:8000/health | jq .

# 2. Check telemetry stream
curl -s http://localhost:8000/api/metrics?limit=1 | jq .

# 3. Check rate limiting headers
curl -I http://localhost:8000/api/metrics
```

Expected Response from `/health`:
```json
{
  "status": "OK",
  "environment": "production",
  "services": {
    "database": "OK",
    "llm": { "status": "CONFIGURED (gemini-2.0-flash)" },
    "langsmith": { "status": "NOT_CONFIGURED (local logging only)" },
    "redis": { "status": "NOT_CONFIGURED (in-memory fallback)" },
    "vector_db": { "status": "OK", "path": "data/vector_store" },
    "mcp": { "status": "ACTIVE (13 tools registered)", "allowlist": "ENFORCED" }
  }
}
```
