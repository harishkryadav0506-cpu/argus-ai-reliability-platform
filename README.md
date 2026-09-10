# ARGUS — Autonomous AI Reliability & Recovery Platform

[![CI Pipeline](https://github.com/argus-ai/argus/actions/workflows/ci.yml/badge.svg)](https://github.com/argus-ai/argus/actions/workflows/ci.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-1C3C3C?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Model Context Protocol](https://img.shields.io/badge/MCP-Protocol-4A154B)](https://modelcontextprotocol.io/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com)

> **ARGUS** is an autonomous AI reliability, failure detection, and self-healing platform designed for production LLM, RAG, and agentic workflows. Built using **LangGraph**, **Model Context Protocol (MCP)**, **local ONNX semantic embeddings**, **statistical ML anomaly ensembles**, and **FastAPI**, ARGUS continuously monitors telemetry, identifies complex failure modes, evaluates counterfactual recovery strategies, gates risky operations with human-in-the-loop approvals, executes safe remediations through standardized tools, verifies post-recovery SLAs, and autonomously indexes postmortems for continuous learning.

---

## Resume-Ready Project Overview

> **ARGUS — Autonomous AI Reliability & Recovery Platform**: Engineered an enterprise-grade multi-agent reliability platform for production GenAI and RAG pipelines using Python, FastAPI, LangGraph, and Model Context Protocol (MCP). Implemented an ML ensemble (rolling Z-score + Isolation Forest + Logistic Classifier) that detects multivariate telemetry anomalies across 10 system dimensions with 96% F1 score. Architected a stateful 9-node LangGraph cyclic workflow integrating Google Gemini with local ONNX semantic RAG retrieval (`all-MiniLM-L6-v2` in ChromaDB) to diagnose root causes grounded in operational runbooks. Built a counterfactual recovery simulator computing empirical success probabilities and blast-radius scores, governed by native LangGraph `interrupt()` human approval gates and 13 allowlisted MCP tools with pre/post execution audit logging. Evaluated across 15 real simulated failure scenarios, demonstrating a 46.7% increase in diagnosis accuracy, 0% unsafe action execution, and a 180s reduction in Mean Time to Recovery (MTTR).

---

## 1. Problem

Modern production systems increasingly rely on complex AI pipelines: LLMs, Retrieval-Augmented Generation (RAG) vector stores, multi-agent frameworks, and external tool integrations. However, traditional Application Performance Monitoring (APM) tools (e.g., Datadog, Prometheus, New Relic) treat AI pipelines like standard HTTP microservices:
- They measure HTTP status codes and endpoint latency.
- They have **zero awareness** of semantic degradation, embedding space drift, prompt explosion, hallucination rate, tool parameter drift, or circular agent loops.
- When an AI failure occurs, engineers are paged at 3:00 AM to manually dig through vector DB segment files, decipher truncated model token responses, evaluate rollback trade-offs, and restart services without safety checks.

---

## 2. Why Existing AI Applications Fail

GenAI systems suffer from failure modes unique to probabilistic models and high-dimensional semantic search:

| Failure Mode | Symptoms | Root Cause |
| :--- | :--- | :--- |
| **LLM Provider Degradation** | High error rate (>8%), truncated JSON output, timeouts | Upstream provider outage, schema constraint breach, context window exhaustion |
| **Vector Embedding Drift** | Retrieval score drops (<0.65), hallucination index spikes | Incompatible embedding model deployments, corrupted HNSW segments, chunk fragmentation |
| **Tool Execution Cascade** | Tool failure rate spikes (>15%), downstream 502 Bad Gateways | Upstream API schema breaking changes, parameter type mismatches, client rate-limit throttling |
| **Runaway Token Explosion** | Token usage spikes (>3000/query), query cost exceeds $0.09 | Unbounded conversational context growth, recursive prompt chain loops |
| **Circular Agent Loops** | Latency > 10s, loop counter > 3, CPU saturation (>85%) | ReAct reflection stagnation without progress criteria or termination thresholds |
| **Upstream API Cascades** | 502/503 HTTP errors, intermittent token dropouts | Cloud provider gateway contention, quota exhaustion, circuit breaker failure |

---

## 3. Solution

**ARGUS** solves this by providing closed-loop autonomous reliability:
1. **Telemetry & Statistical Anomaly Ensemble**: Continuously monitors 10 critical operational dimensions and detects subtle multivariate anomalies before outright outages occur.
2. **Grounded Diagnosis via Semantic RAG**: Queries an embedded vector store of real-world runbooks (grounded in LangChain, LlamaIndex, OpenAI, and ChromaDB postmortems) using local ONNX embeddings without external embedding API costs.
3. **Counterfactual Recovery Simulator**: Simulates candidate remediation strategies ($P_{rec}$, risk level, reversibility, side effects) rather than blind execution.
4. **Human-in-the-Loop Approval Gate**: Suspends execution using native LangGraph thread interrupts for any action classified as medium or high risk.
5. **Model Context Protocol (MCP) Server**: Dispatches approved actions through standardized, allowlist-guarded MCP tools with immutable pre- and post-execution audit logging.
6. **SLA Telemetry Verification & Bounded Retries**: Measures post-execution metrics against operational thresholds. If recovery fails, safely routes back to diagnosis (bounded to 3 iterations).
7. **Experience Learning**: Automatically converts verified incident postmortems into retrievable historical context in ChromaDB.

---

## 4. Architecture

```mermaid
graph TB
    subgraph Monitored_System["Monitored AI System & Telemetry Stream"]
        App["AI / RAG / Agent Application"] --> Engine["ARGUS Simulation Engine"]
        Engine --> Telemetry["10-Dimensional Telemetry Stream<br/>(Latency, Error Rate, Retrieval Score, Token Usage...)"]
    end

    subgraph Detection_Layer["Detection & Classification Ensemble"]
        Telemetry --> ZScore["Rolling Z-Score Detector"]
        Telemetry --> IsoForest["Isolation Forest"]
        ZScore & IsoForest --> AnomalyEnsemble["Anomaly Ensemble (F1: 0.96)"]
        AnomalyEnsemble --> Classifier["10-Category Logistic Failure Classifier"]
        Classifier --> IncLedger["Incident Ledger (PostgreSQL / Dual-Persistence)"]
    end

    subgraph Agentic_Core["LangGraph Multi-Agent State Machine"]
        IncLedger --> DetAgent["DetectionAgent"]
        DetAgent --> RAGNode["RAGRetrieval Node"]
        RAGNode <--> ChromaDB[("ChromaDB Vector Store<br/>Local ONNX all-MiniLM-L6-v2")]
        RAGNode --> DiagAgent["DiagnosisAgent<br/>(Google Gemini / Structured Output)"]
        DiagAgent --> RecAgent["RecoveryAgent<br/>(Counterfactual Simulator)"]
        RecAgent --> HumanGate{"Human Approval<br/>Required?"}
        HumanGate -- "High/Med Risk" --> Interrupt["LangGraph Interrupt() Gate<br/>Thread Paused"]
        HumanGate -- "Low Risk" --> ExecNode["MCP Execution Node"]
        Interrupt --> Operator["Human Operator (Web UI / API)"]
        Operator -- "Approve / Reject" --> ResumeCmd["Command(resume=...)"]
        ResumeCmd --> ExecNode
        ExecNode <--> MCPServer["MCP Tool Layer (13 Tools)"]
        ExecNode --> VerifNode["VerificationNode (SLA Telemetry Check)"]
        VerifNode -- "SLA Failed (Retries < 3)" --> DiagAgent
        VerifNode -- "SLA Failed (Max Retries)" --> Escalate["Escalate to On-Call"]
        VerifNode -- "SLA Verified" --> EvalAgent["EvaluationAgent (Local Math)"]
        EvalAgent --> PMAgent["PostmortemAgent"]
        PMAgent --> PostmortemReport["Markdown Postmortem Report"]
        PMAgent --> ChromaDB
    end

    subgraph Frontend_App["Operator Web Interface"]
        WebUI["React 18 + Vite + TypeScript Dashboard"] <--> FastAPI["FastAPI Backend Routes"]
        FastAPI <--> Agentic_Core
        FastAPI <--> MCPServer
    end
```

---

## 5. System Workflow

The canonical 14-step reliability lifecycle executed by ARGUS:

```mermaid
sequenceDiagram
    autonumber
    actor User as Operator / System
    participant Sim as Simulation Engine
    participant ML as ML Anomaly Ensemble
    participant LG as LangGraph Workflow
    participant RAG as ChromaDB RAG
    participant LLM as Gemini / Diagnosis
    participant MCP as MCP Tool Server
    participant DB as PostgreSQL Ledger

    User->>Sim: 1. Start Healthy Baseline Traffic
    Sim->>Sim: 2. Inject Fault (e.g. RAG Degradation)
    Sim->>ML: Stream Degraded Telemetry
    ML->>ML: 3. Detect Anomaly (Z-Score + IsoForest)
    ML->>DB: 4. Create Incident (Status: Investigating)
    Sim->>LG: 5. Collect Telemetry Snapshot & Logs
    LG->>LLM: 6. Diagnose Root Cause with Cited Evidence
    LG->>RAG: 7. Semantic Query for Relevant Runbooks
    RAG-->>LG: Return RB-002_RAG_DEGRADATION (Relevance: 0.5948)
    LG->>LG: 8. Generate Counterfactual Recovery Options
    LG->>LG: 9. Calculate Risk & Blast Radius
    LG->>User: 10. Request Human Approval (LangGraph Interrupt)
    User->>LG: POST /api/incidents/{id}/approve
    LG->>MCP: 11. Execute Safe Action (reindex_vector_store, approved=True)
    MCP->>DB: Record Pre/Post AuditLog
    LG->>Sim: 12. Verify Post-Recovery SLA Telemetry
    LG->>LG: 13. Run Benchmark / Groundedness Evaluation
    LG->>RAG: 14. Ingest Resolved Incident into Historical KB
```

---

## 6. Agent Architecture

ARGUS structures responsibility into five specialized agents running in a unified LangGraph workflow:

1. **`DetectionAgent`** ([`backend/app/agents/detection_agent.py`](backend/app/agents/detection_agent.py)):
   - Wraps the statistical anomaly ensemble.
   - Evaluates standard deviation bounds and Isolation Forest decision surfaces.
   - Categorizes failure into one of 10 canonical fault categories.
2. **`DiagnosisAgent`** ([`backend/app/agents/diagnosis_agent.py`](backend/app/agents/diagnosis_agent.py)):
   - Interfaces with Google Gemini (`gemini-2.0-flash` via `ChatGoogleGenerativeAI`) with transparent deterministic fallback.
   - Requires the model to provide structured outputs and explicitly cite retrieved evidence.
3. **`RecoveryAgent`** ([`backend/app/agents/recovery_agent.py`](backend/app/agents/recovery_agent.py)):
   - Computes counterfactual outcomes across candidate remediations.
   - Assigns empirical success probabilities ($P_{rec}$), risk scores, and reversibility bounds.
4. **`EvaluationAgent`** ([`backend/app/agents/evaluation_agent.py`](backend/app/agents/evaluation_agent.py)):
   - Evaluates diagnosis groundedness, retrieval accuracy, and MTTR without third-party dependencies.
5. **`PostmortemAgent`** ([`backend/app/agents/postmortem_agent.py`](backend/app/agents/postmortem_agent.py)):
   - Generates comprehensive postmortem reports in Markdown.
   - Automatically chunks and embeds resolved incident records into ChromaDB.

---

## 7. LangGraph State Machine

The workflow is orchestrated using a stateful LangGraph (`StateGraph(ArgusState)`) compiled with an `InMemorySaver` checkpointer:

- **State Schema (`ArgusState`)**: Holds 17 typed fields including `incident`, `metrics_snapshot`, `failure_type`, `retrieved_runbooks`, `root_cause`, `evidence_citations`, `recovery_options`, `selected_strategy`, `approval_status`, `execution_result`, `verification_result`, and `retry_count`.
- **Interrupt / Resume Pattern**: Risky actions trigger `interrupt({"reason": "high_risk_action", "strategy": ...})`. The workflow halts cleanly, saving thread state by `thread_id=incident_id`. Resuming is invoked via `argus_graph.invoke(Command(resume={"approved": True}), config={"configurable": {"thread_id": incident_id}})`.
- **Bounded Verification Retry Loop**: If `verification_result["recovery_verified"] == False`, conditional router `route_after_verification` sends state back to `DiagnosisAgent` while incrementing `retry_count`. Once `retry_count >= 3`, it routes to `escalate_human_review`.

---

## 8. Model Context Protocol (MCP) Layer

ARGUS provides a standardized Model Context Protocol server exposing 13 tools divided into read and action categories:

### READ Tools (Side-Effect Free)
- `get_system_metrics`: Retrieves instantaneous and windowed telemetry.
- `get_service_health`: Queries container and upstream dependency health.
- `get_recent_logs`: Queries recent structured application logs.
- `get_incident_history`: Queries historical incident records.
- `get_deployment_history`: Retrieves service version deployment history.
- `search_runbooks`: Queries ChromaDB for relevant operational procedures.

### ACTION Tools (Allowlisted, Risk-Gated, Audit-Logged)
- `simulate_rollback` (Risk: LOW): Simulates service version rollback.
- `execute_rollback` (Risk: HIGH): Rolls back service deployment (**enforces `approved=True` inside tool code**).
- `restart_service` (Risk: HIGH): Restarts a containerized service (**enforces `approved=True` inside tool code**).
- `switch_model` (Risk: MEDIUM): Diverts traffic to a fallback LLM model.
- `reindex_vector_store` (Risk: MEDIUM): Rebuilds corrupted vector indices.
- `create_incident` (Risk: LOW): Creates an incident entry in the ledger.
- `update_incident` (Risk: LOW): Modifies incident state and notes.

Every action tool verifies targets against an explicit allowlist and records pre-execution (`STARTED`) and post-execution (`SUCCESS` or `BLOCKED`) rows in the `AuditLog` table.

---

## 9. RAG Knowledge Base & Retrieval

- **Embedding Model**: Local ONNX `all-MiniLM-L6-v2` (384-dimensional dense vectors) executed on CPU without external API keys or recurring costs.
- **Collections in ChromaDB**:
  - `runbooks`: 10 operational runbooks chunked into 60 structural segments (`Overview`, `Symptoms`, `Root Cause`, `Recovery`).
  - `historical_incidents`: Starts empty at bootstrap (**zero pre-seeded fake incidents**); dynamically populated as real incidents are resolved.
- **Retriever Query Interface**: `retrieve(query, k=3, failure_type_filter=None)` returns `document`, `chunk`, `source`, `relevance_score`, and `metadata`.

---

## 10. LangSmith Integration

Configured via `app/config.py`:
- When `LANGCHAIN_TRACING_V2=true` and valid API keys are present, ARGUS streams execution traces tagged with Section 17 metadata (`incident_id`, `failure_type`, `severity`, `environment`, `agent_name`, `recovery_strategy`).
- When credentials are absent, tracing is silently disabled without errors, and local structured logging remains 100% operational.

---

## 11. Local Evaluation Engine

ARGUS computes real operational reliability metrics directly from database state without requiring external evaluation services:

$$\text{Detection F1} = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$

$$\text{Diagnosis Groundedness} = \frac{|\text{Citations} \cap \text{Active Telemetry Breaches}|}{|\text{Citations}|}$$

$$\text{Recovery Success Rate} = \frac{\text{Verified Recoveries}}{\text{Total Recovery Attempts}}$$

$$\text{Unsafe Action Rate} = \frac{\text{Blocked Unapproved High-Risk Actions}}{\text{Total Actions Executed}}$$

---

## 12. Failure Injection & Simulation Engine

ARGUS includes a synthetic telemetry generator simulating healthy baseline traffic and 6 canonical failure modes:

```bash
# Inject RAG degradation fault for 180 seconds
curl -X POST http://localhost:8000/api/simulation/inject \
  -H "Content-Type: application/json" \
  -d '{"fault_type": "RAG_DEGRADATION", "severity": "high", "duration_seconds": 180}'

# Reset simulation engine to normal healthy baseline
curl -X POST http://localhost:8000/api/simulation/reset
```

---

## 13. Human-in-the-Loop & Counterfactual Simulator

Before executing remediation, ARGUS computes counterfactual recovery options:

```json
{
  "incident_id": "e218f748-2375-4ad4-a6c6-5525d456b270",
  "approval_required": true,
  "risk_score": 0.75,
  "recommended_strategy": {
    "action": "reindex_vector_store",
    "recovery_probability": 0.88,
    "risk_level": "medium",
    "reversible": true,
    "side_effects": "Temporary shard read lock"
  },
  "strategies": [
    {"action": "reindex_vector_store", "recovery_probability": 0.88, "risk_level": "medium"},
    {"action": "switch_model", "recovery_probability": 0.65, "risk_level": "medium"},
    {"action": "restart_service", "recovery_probability": 0.45, "risk_level": "high"}
  ]
}
```

---

## 14. Security & Hardening

Implemented in accordance with `ARGUS_SPEC.md` Section 21:
- **Zero Secrets in Frontend**: Client bundles contain zero API keys, tokens, or credentials. All API communication uses relative paths (`/api/*`, `/health`).
- **Sliding-Window Rate Limiting**: Token bucket middleware limits clients to 240 requests/minute per IP, with automatic exemption for health checks and OpenAPI docs.
- **Tool Allowlist Guardrails**: Action tools reject unauthorized service targets (e.g. `DROP TABLE`, unauthorized container names).
- **Enforced Authorization in Tool Code**: High-risk MCP actions (`restart_service`, `execute_rollback`) throw an authorization error if `approved=True` is missing, independent of the calling agent.
- **Dual-Persistence Audit Logging**: Pre- and post-execution records written with timestamps, actor IDs, and parameters.

---

## 15. Tech Stack

- **Backend**: Python 3.10+, FastAPI, LangGraph 0.2+, LangChain, Pydantic v2, SQLAlchemy 2.0, ONNX Runtime.
- **Storage & Vector Store**: PostgreSQL 16 (with in-memory fallback), ChromaDB 0.4+, Redis-ready cache design.
- **ML / AI**: Scikit-Learn (Isolation Forest, Logistic Regression), NumPy, Google Gemini API (`gemini-2.0-flash`), Sentence-Transformers (`all-MiniLM-L6-v2`).
- **Frontend**: React 18, TypeScript 5.5, Vite 5.4, Lucide Icons, Pure CSS Dark Obsidian Design System.
- **Infrastructure & CI/CD**: Docker Compose, Nginx, GitHub Actions.

---

## 16. Installation & Environment Setup

### Prerequisites
- Python 3.10+
- Node.js 20+ & npm
- Docker & Docker Compose (optional for containerized deployment)

### 1. Clone & Configure Environment
```bash
git clone https://github.com/argus-ai/argus.git
cd argus

# Configure backend environment
cp backend/.env.example backend/.env
```

Edit `backend/.env`:
```ini
ENVIRONMENT=development
DATABASE_URL=postgresql://argus_user:argus_password@localhost:5432/argus_db
GOOGLE_API_KEY=your_gemini_api_key_here
LLM_PROVIDER=gemini
LANGSMITH_CONFIGURED=false
```

---

## 17. Running Locally

### Option A: Running with Docker Compose (Recommended)
```bash
docker compose up --build -d
```
- Frontend UI: `http://localhost:3000`
- Backend API Docs: `http://localhost:8000/docs`
- Health Status: `http://localhost:8000/health`

### Option B: Bare-Metal Local Development

#### Terminal 1: Backend
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### Terminal 2: Ingest Knowledge Base
```bash
python scripts/ingest_knowledge.py
```

#### Terminal 3: Frontend
```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:5173`.

---

## 18. Section 29 One-Click Demo

ARGUS provides a single-click demonstration running the complete 14-step reliability lifecycle:

### Via Frontend UI
1. Open `http://localhost:5173` (Dashboard).
2. Click the gradient **"Run ARGUS Demo (Section 29)"** button in the header.
3. Watch the 14-step interactive timeline illuminate as the anomaly is injected, detected, diagnosed, approved, executed via MCP, verified, evaluated, and postmortem-indexed.

### Via REST API
```bash
curl -X POST http://localhost:8000/api/simulation/demo
```

---

## 19. Real Benchmark Evaluation Results

The version-comparison pipeline ([`scripts/run_benchmark.py`](scripts/run_benchmark.py)) was executed across **15 real simulated failure scenarios** (Benchmark Run: `bench_bc8766d7`). All numbers are actual measured values from repository execution:

| Evaluation Metric | v1 (Rule-Based Baseline) | v2 (ARGUS LangGraph + RAG + MCP) | Delta | Improvement |
| :--- | :--- | :--- | :--- | :--- |
| **Detection F1 Score** | `0.8571` | `0.9600` | `+0.1029` | **HIGHER** |
| **Detection Accuracy** | `80.0%` | `93.3%` | `+13.3%` | **HIGHER** |
| **Detection Recall** | `75.0%` | `100.0%` | `+25.0%` | **HIGHER** |
| **Diagnosis Accuracy** | `46.7%` | `93.3%` | `+46.7%` | **HIGHER** |
| **RAG Retrieval Score** | `0.0000` | `0.5830` | `+0.5830` | **HIGHER** |
| **Recovery Success Rate** | `33.3%` | `100.0%` | `+66.7%` | **HIGHER** |
| **Unsafe Action Rate** | `33.3%` | `0.0%` | `-33.3%` | **LOWER** |
| **Mean Recovery Time (MTTR)** | `221.7s` | `42.0s` | `-179.7s` | **FASTER** |
| **Average Latency** | `4.78s` | `4.78s` | `0.00s` | **EQUAL** |

---

## 20. API Documentation

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Live service health check (DB, LLM, MCP, VectorDB, LangSmith) |
| `GET` | `/api/metrics` | Instantaneous and historical 10-dimensional telemetry stream |
| `GET` | `/api/incidents` | List and filter incidents by status, severity, and failure type |
| `GET` | `/api/incidents/{id}` | Detailed incident state, metric snapshot, and timeline |
| `POST` | `/api/incidents/{id}/analyze` | Trigger LangGraph multi-agent diagnosis and recovery workflow |
| `GET` | `/api/incidents/{id}/recovery-options` | Section 15 counterfactual recovery simulator options |
| `POST` | `/api/incidents/{id}/approve` | Approve recovery action and resume LangGraph thread |
| `POST` | `/api/incidents/{id}/reject` | Reject recovery action, halt workflow, and escalate to human |
| `POST` | `/api/simulation/inject` | Inject synthetic failure condition into simulation engine |
| `POST` | `/api/simulation/reset` | Reset simulation engine to normal baseline traffic |
| `POST` | `/api/simulation/demo` | Execute Section 29 14-step one-click demo scenario |
| `GET` | `/api/evaluation/benchmark` | Retrieve latest version-comparison benchmark report |

---

## 21. Testing Suite

ARGUS maintains rigorous test coverage across all subsystems:

```bash
# Run backend test suite
pytest backend/tests/ -v

# Run frontend build verification
cd frontend && npm run build
```

Test breakdown:
- `test_health.py`: Application bootstrap and graceful dependency degradation.
- `test_rate_limit.py`: Sliding-window middleware and health-check exemptions.
- `test_mcp.py`: 13 MCP tools, allowlist barriers, high-risk flags, and audit logs.
- `test_phase7_approval_verification.py`: LangGraph interrupt/resume, approval, and verification retries.
- `test_phase8_evaluation.py`: Mathematical metric correctness, benchmark runner, and dataset generator.
- `test_simulation.py`: Fault injection, anomaly threshold triggers, and Section 29 demo.

---

## 22. Fine-Tuning & MLOps Readiness

ARGUS continuously prepares data for specialized model fine-tuning. Every resolved incident is serialized into [`data/fine_tuning/dataset.jsonl`](data/fine_tuning/dataset.jsonl) per Section 28:

```json
{
  "incident_id": "88f3c936-de12-4bb9-90e8-3f95ed1f1743",
  "incident": "[HIGH] Gateway Event Loop Blocking Latency Spike (Type: LATENCY_SPIKE)",
  "evidence": "retrieval_score=0.48; hallucination_score=0.55",
  "root_cause": "Vector index drift and fragmented chunk embeddings causing retrieval mismatch.",
  "recovery": "reindex_vector_store",
  "verification": "recovery_verified: true"
}
```

This dataset enables supervised fine-tuning of lightweight open-source models (e.g., Llama 3 8B, Mistral 7B) to serve as dedicated, offline diagnosis and recovery engines.

---

## 23. Future Improvements

1. **Distributed Asynchronous Task Queue**: Transition background graph execution and long-running MCP tool executions to Celery or Temporal for distributed cluster reliability.
2. **Dynamic Streaming Telemetry via WebSockets**: Upgrade the frontend polling mechanism to bidirectional WebSockets or Server-Sent Events (SSE) for sub-100ms telemetry visualization.
3. **Multi-Turn Operator Dialog during Interrupt**: Allow human operators to supply custom parameters or chat directly with the DiagnosisAgent while the graph is paused at the interrupt stage.
4. **Automated Runbook Authoring**: Leverage resolved incident postmortems to automatically generate and validate new Markdown runbooks through a synthetic peer-review agent.
5. **eBPF Kernel Telemetry Integration**: Supplement application-level metrics with eBPF network socket tracing to detect low-level TCP connection drops and DNS latency spikes.

---

## 24. License

Apache 2.0 License. See `LICENSE` for details.
