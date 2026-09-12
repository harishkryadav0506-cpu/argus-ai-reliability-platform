# ARGUS — Autonomous AI Reliability & Recovery Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-1C3C3C?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Model Context Protocol](https://img.shields.io/badge/MCP-Protocol-4A154B)](https://modelcontextprotocol.io/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org)

> **ARGUS** is an autonomous AI reliability, failure detection, and self-healing platform engineered for production LLM, RAG, and agentic microservices. Powered by **LangGraph**, **Model Context Protocol (MCP)**, **statistical ML anomaly ensembles**, **local ONNX semantic RAG**, and **FastAPI**, ARGUS continuously monitors runtime telemetry, classifies subtle AI-specific failures, simulates counterfactual recoveries, gates high-risk remediations behind human approvals, executes actions via standardized tools, verifies post-recovery SLA baselines, and indexes postmortems for continuous organizational learning.

---

## 1. Problem

Production AI applications (LLM pipelines, RAG systems, tool-using autonomous agents) are fundamentally probabilistic and distributed. Traditional Application Performance Monitoring (APM) tools (Datadog, New Relic, Prometheus) treat AI services like standard HTTP microservices:
- They measure generic HTTP status codes and endpoint response times.
- They have **zero visibility** into semantic degradation, vector embedding drift, silent hallucination spikes, prompt explosion, tool parameter drift, or recursive agent loops.
- When an AI failure occurs, engineers are paged in the middle of the night to manually inspect vector store segments, decipher truncated model token responses, guess rollback trade-offs, and restart services without safety or SLA verification.

---

## 2. Why Existing AI Applications Fail

GenAI pipelines fail in ways fundamentally distinct from traditional software services:

| Failure Archetype | Runtime Symptoms | Real Root Cause |
| :--- | :--- | :--- |
| **LLM Provider Failure** | Error rate spikes ($>2.0\%$), truncated JSON, provider 500s | Upstream provider outage, rate limits, schema constraint violation, context exhaustion |
| **RAG Embedding Degradation** | Retrieval score drops ($<0.85$), hallucination index surges | Incompatible embedding model deployments, index corruption, chunk fragmentation |
| **Tool Execution Cascade** | Tool failure rate spikes ($>3.0\%$), downstream 502s | Breaking schema changes, parameter mismatch, API token invalidation, rate limits |
| **Runaway Cost / Token Spike** | Token usage surges ($>1500$/query), query cost exceeds $\$0.05$ | Unbounded chat context accumulation, recursive chain loops, runaway prompt expansions |
| **Circular Agent Reasoning Loop** | Latency $>10\text{s}$, loop count $>0$, CPU saturation | ReAct reflection stagnation without termination thresholds or progress criteria |
| **Latency Contention Spike** | Latency $>2.2\text{s}$, event loop delays, pool exhaustion | Thread pool contention, database pool starvation, blocking synchronous network calls |

---

## 3. Solution

**ARGUS** bridges the gap between observability and autonomous remediation:
1. **Telemetry & Statistical Anomaly Ensemble**: Continuously monitors 13 operational metrics, combining rolling statistical Z-scores ($2.8\sigma$) with multivariate Isolation Forests to catch subtle multi-dimensional anomalies before hard outages occur.
2. **Grounded Diagnosis via Semantic RAG**: Queries an embedded ChromaDB collection of operational runbooks using local ONNX dense embeddings (`all-MiniLM-L6-v2`) without external embedding API cost or network dependencies.
3. **Counterfactual Recovery Simulation**: Evaluates candidate recovery strategies using empirical probability distributions, risk blast-radius scoring, and reversibility bounds rather than blind execution.
4. **Human-in-the-Loop Approval Gate**: Halts execution using native LangGraph thread interrupts for any action classified as medium or high risk, requiring explicit operator sign-off.
5. **Standardized MCP Tool Execution**: Executes remediation through 13 standardized Model Context Protocol (MCP) tools, enforcing strict tool allowlisting and dual-path execution.
6. **SLA Telemetry Verification & Bounded Retries**: Directly validates post-execution metrics against baseline SLAs. If verification fails, safely loops back to diagnosis (bounded to 3 iterations).
7. **Continuous Learning & Dataset Export**: Converts verified incident postmortems into ChromaDB vectors and idempotent JSONL exports for fine-tuning diagnostic models.

---

## 4. Architecture

```mermaid
graph TD
    subgraph Monitored_System["Monitored AI System & Telemetry Stream"]
        App["Production AI / RAG / Agent Pipeline"] --> Sim["Simulation & Telemetry Engine"]
        Sim --> Stream["13-Metric Telemetry Stream<br/>(Latency, Error Rate, Retrieval Score, Token Usage...)"]
    end

    subgraph Detection_Layer["Detection & Classification Ensemble"]
        Stream --> ZScore["Rolling Z-Score (2.8σ)"]
        Stream --> IsoForest["Isolation Forest"]
        ZScore & IsoForest --> Detector["Anomaly Detector Ensemble (F1: 0.973)"]
        Detector --> Classifier["Dual-Model Ensemble Failure Classifier"]
        Classifier --> Ledger[("PostgreSQL Incident Ledger")]
    end

    subgraph Agentic_Core["LangGraph Cyclic Multi-Agent Workflow"]
        Ledger --> NodeDetect["Detection Node<br/>(DetectionAgent)"]
        NodeDetect --> NodeRAG["Runbook Retrieval Node<br/>(RAGRetrieval)"]
        NodeRAG <--> ChromaDB[("ChromaDB Vector Store<br/>Local ONNX all-MiniLM-L6-v2")]
        NodeRAG --> NodeDiag["Diagnosis Node<br/>(DiagnosisAgent / Gemini 3.6 Flash)"]
        NodeDiag --> NodeRec["Recovery Strategy Simulation<br/>(RecoveryAgent)"]
        NodeRec --> Gate{"Risk Assessment<br/>Gate"}
        Gate -- "High / Medium Risk" --> Interrupt["Human Approval Gate<br/>(LangGraph interrupt())"]
        Gate -- "Low Risk / Auto-Approved" --> NodeExec["MCP Action Execution Node"]
        Interrupt --> Operator["Human Operator<br/>(Web Dashboard / API)"]
        Operator -- "Approve / Reject" --> ResumeCmd["Command(resume=...) / MCP Dual-Path"]
        ResumeCmd --> NodeExec
        NodeExec <--> MCP["Model Context Protocol Server<br/>(13 Standardized Tools)"]
        NodeExec --> NodeVerif["SLA Verification Node<br/>(Post-Recovery Telemetry Check)"]
        NodeVerif -- "Breach (Retries < 3)" --> NodeDiag
        NodeVerif -- "Breach (Max Retries)" --> Escalate["Escalate to Human On-Call"]
        NodeVerif -- "SLA Verified (Pass)" --> NodeEval["Evaluation Node<br/>(Benchmark & Metrics)"]
        NodeEval --> NodePM["Postmortem Node<br/>(PostmortemAgent)"]
        NodePM --> Report["Structured Markdown Postmortem"]
        NodePM --> ChromaDB
        NodePM --> FineTune["data/fine_tuning/dataset.jsonl"]
    end

    subgraph Operator_UI["Engineering Web Dashboard"]
        WebUI["React 18 + TypeScript Dashboard"] <--> API["FastAPI REST Endpoints"]
        API <--> Agentic_Core
        API <--> Ledger
    end
```

---

## 5. System Workflow

The autonomous lifecycle operates in 8 sequential, self-verifying stages:

1. **Ingest & Stream**: Telemetry ticks are generated or ingested into the sliding-window buffer (last 120 points).
2. **Detect Anomaly**: The anomaly detector evaluates rolling statistical variance ($2.8\sigma$) alongside the Isolation Forest decision boundary.
3. **Classify Incident**: When anomalous deviation occurs, the failure classifier determines the fault mode, assigns severity, and persists an incident to PostgreSQL.
4. **Retrieve Runbooks**: `RAGRetrieval` queries ChromaDB using local ONNX embeddings, diversifying results across distinct source documents to retrieve authoritative operational runbooks.
5. **Diagnose Root Cause**: `DiagnosisAgent` synthesizes telemetry evidence with retrieved runbook chunks via Google Gemini (`gemini-3.6-flash`), citing runbook sections.
6. **Simulate Recovery**: `RecoveryAgent` counterfactually scores recovery options by computing $P(\text{recovery})$, risk blast radius, and expected utility.
7. **Gate & Execute via MCP**: If the selected action carries medium or high risk, LangGraph halts execution at an `interrupt()`. Upon operator approval, the action executes via standardized MCP tools.
8. **Verify & Learn**: The verification node checks live telemetry against SLA thresholds. When verified, `PostmortemAgent` indexes the resolution and appends to the fine-tuning dataset.

---

## 6. Agent Architecture

ARGUS organizes responsibilities into 5 specialized agents coordinated via a shared `ArgusState`:

1. **DetectionAgent**:
   - **Responsibility**: Multivariate statistical anomaly detection and classification.
   - **Mechanism**: Blends univariate rolling Z-score thresholds with an unsupervised Isolation Forest and multi-class logistic classifier.
2. **RAGRetrieval Agent**:
   - **Responsibility**: Semantic vector search over operational knowledge bases.
   - **Mechanism**: Embeds queries via local ONNX dense embeddings (`all-MiniLM-L6-v2`) and applies document-level source diversification over ChromaDB runbooks.
3. **DiagnosisAgent**:
   - **Responsibility**: Root cause identification grounded in empirical evidence.
   - **Mechanism**: Calls Google Gemini (`gemini-3.6-flash`) with structured JSON schema output, enforcing explicit runbook section citations and evidence matching.
4. **RecoveryAgent**:
   - **Responsibility**: Counterfactual simulation and remediation planning.
   - **Mechanism**: Computes recovery probability, risk penalty, reversibility, and blast radius for candidate strategies, formatting structured execution payloads.
5. **PostmortemAgent**:
   - **Responsibility**: Knowledge retention and continuous self-improvement.
   - **Mechanism**: Generates comprehensive incident postmortems (timeline, root cause, recovery actions, preventive actions), writes vectors to ChromaDB, and updates `dataset.jsonl`.

---

## 7. LangGraph Implementation

### Cyclic State Machine & Interrupt/Resume
ARGUS leverages LangGraph's stateful cyclic graph with an in-memory `MemorySaver` checkpointer:
- **Human Approval Gate**: Riskier actions invoke `interrupt({"approval_required": True, ...})`, serializing thread state and halting graph execution without blocking worker processes.
- **Resumption**: Operators submit approval via `POST /api/incidents/{id}/approve`. The backend invokes `argus_graph.invoke(Command(resume={"approved": True, ...}), config={"configurable": {"thread_id": incident_id}})`.

### Dual-Path Execution Fix
In real-world operations, approvals may occur after server reboots, across container lifecycles, or on pre-seeded records where an in-memory LangGraph thread is not halted. ARGUS implements a robust dual-path resolution in `incidents.py`:
- **Active Thread Path**: If `thread_state.next` is present, it resumes the native LangGraph interrupt.
- **Direct MCP Deterministic Path**: If no active thread is in memory, the backend directly executes the designated recovery action through the MCP tool layer, performs post-recovery SLA verification, updates the database, and commits audit logs.

---

## 8. Model Context Protocol (MCP) Integration

ARGUS implements a compliant Model Context Protocol (MCP) server containing 13 standardized tools partitioned into two strict operational privilege tiers:

### Read Tools (Diagnostic & Inspection)
- `read_system_metrics`: Retrieves sliding-window telemetry.
- `read_service_health`: Queries container and HTTP status endpoints.
- `read_vector_db_stats`: Inspects ChromaDB segment integrity and collection count.
- `read_llm_gateway_logs`: Reads LLM provider error and latency logs.
- `read_recent_audit_log`: Inspects historical administrative and tool actions.
- `read_active_incidents`: Returns open and investigating incident records.

### Action Tools (Remediation & Modification)
- `restart_service`: Recycles microservice container processes.
- `execute_rollback`: Reverts deployment revisions to last known stable release.
- `scale_replicas`: Scales container instance counts under contention.
- `flush_cache`: Flushes Redis / in-memory cache segments.
- `switch_model`: Switches upstream LLM model routing fallback.
- `trigger_backup`: Dispatches database and state snapshots.
- `update_alert_threshold`: Adjusts operational monitoring sensitivity.

**Security & Allowlisting**: Action tools cannot be triggered without an explicit `approval_status="approved"` token. Every invocation emits structured audit records to PostgreSQL before and after execution.

---

## 9. Retrieval-Augmented Generation (RAG)

- **Local ONNX Embedding Model**: Uses `all-MiniLM-L6-v2` via ChromaDB’s local ONNX embedding runtime. Generates 384-dimensional dense vectors locally with zero external API fees, zero quota limits, and sub-15ms vectorization.
- **Runbook Knowledge Base**: Pre-seeded with 10 operational runbooks (`RB-001` through `RB-010`) covering Latency Spikes, LLM Failures, RAG Degradation, Tool Cascades, Cost Explosions, Agent Reasoning Loops, Upstream Contention, Memory Leaks, and Unknown Anomalies.
- **Source Diversification**: Retrieval queries a candidate pool ($4 \times k$) and selects the highest-scoring chunk per distinct source file, preventing citations from collapsing into a single document.

---

## 10. Evaluation & Empirical Benchmarks

The benchmark suite (`app/evaluation/benchmark.py`) rigorously compares the v1 Rule-Based Heuristic Baseline against the v2 ARGUS Multi-Agent Platform across 22 controlled operational scenarios:

### Live Benchmark Results

| Evaluation Metric | v1 Rule-Based Baseline | v2 ARGUS LangGraph Platform | Delta / Improvement |
| :--- | :---: | :---: | :---: |
| **Detection F1 Score** | $0.875$ | $\mathbf{0.973}$ | $+9.8\%$ |
| **Detection Accuracy** | $81.8\%$ | $\mathbf{95.5\%}$ | $+13.6\%$ |
| **Detection Recall** | $77.8\%$ | $\mathbf{100.0\%}$ | $+22.2\%$ |
| **Diagnosis Accuracy** | $45.5\%$ | $\mathbf{100.0\%}$ | $+54.5\%$ |
| **RAG Retrieval Score** | *N/A (No RAG)* | $\mathbf{0.585}$ | $+0.585$ |
| **Recovery Success Rate** | $16.7\%$ | $\mathbf{100.0\%}$ | $+83.3\%$ |
| **Unsafe Action Rate** | $33.3\%$ | $\mathbf{0.0\%}$ | $-33.3\%$ *(Zero Unsafe Actions)* |
| **Mean Time to Recovery (MTTR)** | $230.8\text{s}$ | $\mathbf{42.0\text{s}}$ | $\mathbf{-188.8\text{s}}$ *(4.5× Faster)* |

> [!NOTE]
> **Evaluation Honesty Caveat**: The 100% diagnosis accuracy and 100% recovery success rate reflect performance on in-distribution synthetic scenarios where the ground-truth label matches the injected fault type — this validates that the end-to-end pipeline works correctly on canonical fault archetypes, not out-of-distribution or ambiguous real-world accuracy, which would be expected to be lower.

---

## 11. Failure Injection Engine

ARGUS includes a simulation engine modeling 6 canonical failure modes with realistic Gaussian distortions:

| Fault Mode | Injected Telemetry Signature | Breached SLA Targets |
| :--- | :--- | :--- |
| **`LATENCY_SPIKE`** | Latency: $\mu=8.5\text{s}$, CPU: $\mu=75.0\%$, API Success: $\mu=91.0\%$ | `latency > 2.20s`, `api_success_rate < 0.980` |
| **`LLM_FAILURE`** | Error Rate: $\mu=28.0\%$, API Success: $\mu=70.0\%$, Latency: $\mu=4.8\text{s}$ | `error_rate > 0.020`, `api_success_rate < 0.980` |
| **`RAG_DEGRADATION`** | Retrieval Score: $\mu=0.48$, Hallucination: $\mu=0.55$, Tokens: $\mu=1450$ | `retrieval_score < 0.850`, `hallucination_score > 0.100` |
| **`TOOL_FAILURE`** | Tool Failure Rate: $\mu=42.0\%$, Error Rate: $\mu=18.0\%$ | `tool_failure_rate > 0.030`, `error_rate > 0.020` |
| **`COST_SPIKE`** | Token Usage: $\mu=2900$, Request Volume: $\mu=190\text{ rps}$ | `token_usage > 1500`, `request_volume > 100` |
| **`AGENT_LOOP`** | Latency: $\mu=11.5\text{s}$, CPU: $\mu=92.0\%$, Loop Count: $4$ | `loop_count > 0`, `latency > 2.20s`, `cpu_usage > 80%` |

---

## 12. Human-in-the-Loop & Auditability

1. **State Machine Interrupts**: When a proposed remediation exceeds safe risk thresholds, the execution state is saved to the checkpoint ledger, and the incident moves to `investigating (pending approval)`.
2. **Operator Interface**: The incident detail view renders the recommended strategy, expected probability, risk level, and rationale alongside counterfactual alternatives.
3. **Immutable Audit Ledger**: Every action records an immutable audit entry in PostgreSQL containing `actor`, `action`, `incident_id`, `timestamp`, and execution output.

---

## 13. Security Posture (Section 34)

- **Zero Hardcoded Secrets**: All API keys, database credentials, and endpoints are sourced via environment variables and validated through Pydantic Settings.
- **Frontend Credential Isolation**: Sensitive credentials (`GOOGLE_API_KEY`, `LANGSMITH_API_KEY`) are isolated strictly within the backend Docker container and never exposed to browser client bundles.
- **No Arbitrary Shell Execution**: Recovery actions strictly execute predetermined, parameterized Python functions in the MCP server. No arbitrary bash, shell commands, or dynamic code execution is permitted.
- **Action Allowlisting**: Action tools validate strategy names and parameters against a rigid schema before execution.

---

## 14. Tech Stack

- **Backend Framework**: Python 3.11, FastAPI, Uvicorn, Pydantic v2
- **Agent Orchestration**: LangGraph, LangChain Core, Google Generative AI (`gemini-3.6-flash`)
- **Tool Protocol**: Model Context Protocol (MCP) Server Architecture
- **Vector Search & Embeddings**: ChromaDB, ONNX Runtime (`all-MiniLM-L6-v2`)
- **Machine Learning**: Scikit-Learn (Isolation Forest, Logistic Regression), NumPy
- **Relational Persistence**: PostgreSQL 16, SQLAlchemy 2.0, Alembic
- **Observability**: Optional LangSmith Tracing v2, Structured JSON Logging
- **Frontend**: React 18, TypeScript 5.5, Vite, Lucide Icons, Vanilla CSS Design System
- **Containerization**: Docker, Docker Compose, Nginx (Alpine)

---

## 15. Installation & Environment Setup

### 1. Clone Repository
```bash
git clone https://github.com/argus-ai/argus.git
cd argus
```

### 2. Configure Environment (`backend/.env`)
Create `backend/.env` with the following configuration:
```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.6-flash
GOOGLE_API_KEY=your_gemini_api_key_here
DATABASE_URL=postgresql://argus:argus@postgres:5432/argus

# Optional Observability
LANGSMITH_API_KEY=your_langsmith_key_here
LANGSMITH_PROJECT=ARGUS-dev
LANGSMITH_TRACING_V2=true

# Application Environment
ARGUS_ENV=development
LOG_LEVEL=INFO
```

---

## 16. Running Locally

ARGUS is fully containerized and orchestrated via Docker Compose:

```bash
docker-compose up --build
```

### Service Endpoints
- **Web Dashboard**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)
- **PostgreSQL Database**: `localhost:5432` (`argus`/`argus`)

---

## 17. Demo & Usage Guide

### Method A: One-Click End-to-End Demo (Section 29)
1. Open [http://localhost:3000](http://localhost:3000).
2. Click the purple **"Run ARGUS Demo (Section 29)"** button in the header.
3. Watch the real-time 14-step timeline progress through:
   *Healthy Baseline $\to$ Inject RAG Degradation $\to$ ML Anomaly Detected $\to$ Incident Registered $\to$ Telemetry Collected $\to$ Root Cause Diagnosed $\to$ Runbook Retrieved $\to$ Recovery Simulated $\to$ Risk Calculated $\to$ Human Approval Requested $\to$ MCP Executed $\to$ Telemetry Verified $\to$ Evaluated $\to$ Postmortem Indexed.*

### Method B: Manual Fault Injection & Recovery Flow
1. Navigate to **Simulation** (`/simulation`) and click **"Inject Mode"** on any fault card (e.g. `LATENCY_SPIKE`).
2. Observe live metric cards flip to red `BREACH` and the status banner change to `DEGRADED`.
3. Navigate to **Incidents** (`/incidents`), click on the generated incident, and review the **Metric Snapshot at Incident Time** table.
4. Switch to the **Recovery Simulator & Approval** tab, select the recommended strategy, enter operator notes, and click **"Approve & Execute via MCP"**.
5. Observe execution through MCP tools, SLA verification returning to normal, and the incident transitioning to `Resolved & Verified`.

---

## 18. API Documentation

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Live service health check (DB, LLM, MCP, VectorDB, LangSmith) |
| `GET` | `/api/metrics` | Returns current telemetry snapshot and sliding history |
| `POST` | `/api/simulation/inject` | Injects synthetic failure modes (`LATENCY_SPIKE`, etc.) |
| `POST` | `/api/simulation/reset` | Resets telemetry stream to normal baseline |
| `GET` | `/api/incidents` | Lists filtered incident records |
| `GET` | `/api/incidents/{id}` | Retrieves full incident details and snapshot metrics |
| `POST` | `/api/incidents/{id}/analyze` | Re-runs LangGraph multi-agent diagnosis and recovery workflow |
| `GET` | `/api/incidents/{id}/diagnosis` | Returns diagnosed root cause, confidence, and runbook citations |
| `GET` | `/api/incidents/{id}/recovery-options` | Returns counterfactually simulated recovery strategies |
| `POST` | `/api/incidents/{id}/approve` | Submits operator approval to resume recovery execution |
| `POST` | `/api/incidents/{id}/reject` | Rejects proposed recovery and escalates incident |
| `GET` | `/api/evaluation/benchmark` | Returns side-by-side benchmark comparison metrics (v1 vs v2) |
| `POST` | `/api/evaluation/benchmark/run` | Executes 22-scenario empirical benchmark suite |
| `POST` | `/api/demo/run` | Triggers Section 29 automated 14-step demonstration |

---

## 19. Testing

Run the full automated test suite using pytest inside the backend environment:
```bash
docker exec argus-backend pytest tests/test_phase8_evaluation.py tests/test_ml_detection.py tests/test_rag.py -v
```

### Coverage Highlights
- **ML Anomaly Detection**: Z-Score thresholding, Isolation Forest training, logistic classification.
- **Semantic RAG**: ChromaDB local vector storage, MiniLM ONNX embeddings, runbook source diversification.
- **LangGraph Multi-Agent Workflow**: Node transitions, state machine routing, interrupt/resume mechanics.
- **MCP Tool Layer**: Read/Action tool partition, approval enforcement, audit log emission.
- **Post-Recovery Verification**: Metric boundary evaluation, rollback triggers, bounded retries.

---

## 20. Benchmarking

To execute the offline evaluation benchmark suite and regenerate performance metrics:

```bash
# Option A: Direct script execution via virtual environment
python scripts/run_benchmark.py

# Option B: Inside running backend Docker container
docker exec argus-backend python -m app.evaluation.benchmark
```

Running `scripts/run_benchmark.py` evaluates both the v1 rule-based baseline and the v2 LangGraph multi-agent platform against the 22 canonical failure scenarios, prints the full Markdown comparison table directly to stdout, and writes a serialized JSON artifact to `data/evaluation/benchmark_report.json`.

---

## 21. Development & QA Process

The ARGUS platform underwent two rigorous rounds of comprehensive manual QA testing and regression auditing:

1. **Initial QA Pass**: An 18-item audit identified foundational bugs across the stack, including:
   - **Confidence Metric Clustering**: The batch incident generator had bypassed the live ensemble classifier, artificially assigning identical capped confidence scores ($98\%$) to disparate faults. Fixed by unifying all creation paths through the dual-model ensemble blend.
   - **MCP Execution Without Thread Checkpoint**: Clicking human approval on server-rebooted incidents threw errors because the in-memory LangGraph thread had expired. Fixed by architecting the dual-path execution layer.
   - **Data Serialization & Label Alignment**: Corrected fine-tuning dataset export serialization from strings to structured JSON objects (`{"recovery_verified": true}`) and disambiguated live vs. benchmark RAG retrieval labels.
2. **Follow-Up QA Pass & Regression Catch**: The second QA round audited the system under live stress testing, specifically catching a regression introduced by the team's own earlier fix:
   - **SLA Breach False-Positive Regression**: While removing hardcoded `"OK"` defaults, an overly aggressive title/category substring check (`isTrigger`) caused healthy metrics (e.g. `error_rate = 0.009` under `LLM_FAILURE`, or `retrieval_score = 0.862` under `RAG_DEGRADATION`) to be flagged as breaches. Fixed by implementing the strict, metric-specific `METRIC_SLA_RULES` table across all 13 dimensions with dedicated SLA target labels.
   - **Duplicate Incident Creation**: Live injection was generating duplicate incident pairs 20ms apart due to overlapping triggers between `simulation_engine.tick()` and `demo_service.py`. Resolved by adding a 30-second deduplication gate in `incident_service.py`.
   - **Analysis Persistence**: Fixed `analyze_incident` so graph executions reliably commit `Diagnosis` records to PostgreSQL and surface active spinner states in the UI.

---

## 22. Future Improvements

- **Distributed Checkpointer Persistence**: Migrate from the in-memory `MemorySaver` to a distributed Redis / PostgreSQL LangGraph checkpointer for horizontal multi-replica worker scaling.
- **Adaptive Dynamic SLA Boundaries**: Incorporate seasonal Holt-Winters or Prophet models to automatically modulate SLA breach thresholds based on time-of-day traffic seasonality.
- **Active MCP Client Bridge**: Extend the internal MCP server to connect to external third-party MCP servers (e.g. GitHub MCP server for automated pull-request rollbacks, Kubernetes MCP server for pod evictions).
- **Online Fine-Tuning Pipeline**: Automate periodic fine-tuning of compact local LLMs (e.g. Llama-3-8B-Instruct) directly from the curated `dataset.jsonl` export to achieve offline diagnostic autonomy.
