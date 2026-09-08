# ARGUS — Autonomous AI Reliability & Recovery Platform

> This is the canonical specification for ARGUS. Feed this file to Antigravity
> (or read it yourself) before starting any phase of implementation. Do not
> deviate from the phase order in Section 33 — implement one phase at a time,
> run tests after each phase, and do not mark anything "done" until it
> actually runs and passes.

You are an expert AI Engineer, GenAI Engineer, Agentic AI Engineer, Backend Engineer, MLOps Engineer, and Software Architect.

Build a production-style portfolio project called:

**ARGUS — Autonomous AI Reliability & Recovery Platform**

The goal is to create an AI system that monitors AI/LLM/RAG/Agent applications, detects failures or degradation, investigates root causes, retrieves relevant historical incidents/runbooks, evaluates possible recovery strategies, requests human approval for risky actions, executes safe recovery actions through MCP tools, verifies whether recovery worked, and records the complete incident for future learning.

This must NOT be a generic chatbot.

It must demonstrate:

* Machine Learning
* Deep Learning/NLP concepts where useful
* LLMs
* RAG
* LangChain
* LangGraph
* MCP
* LangSmith
* LLM evaluation
* Fine-tuning readiness
* FastAPI
* PostgreSQL
* Vector database
* Redis where useful
* MLOps
* Observability
* Testing
* Human-in-the-loop
* Agentic workflows
* Failure analysis
* Recovery automation
* Production-oriented architecture

---

# 1. CORE PRODUCT IDEA

ARGUS monitors an AI application.

Example monitored application:

```text
User
  ↓
AI Application
  ↓
LLM
  ↓
RAG
  ↓
Vector DB
  ↓
External Tools/APIs
```

Suppose the application starts experiencing:

* increased latency
* increased token usage
* rising API errors
* retrieval degradation
* hallucinations
* low answer relevance
* tool failures
* repeated agent loops
* high cost
* model/API failures

ARGUS should detect the anomaly and create an incident.

Then:

```text
Incident
   ↓
Failure Detection
   ↓
Failure Classification
   ↓
Root Cause Investigation
   ↓
Historical Incident / Runbook Retrieval
   ↓
Recovery Strategy Generation
   ↓
Recovery Simulation / Risk Assessment
   ↓
Human Approval if required
   ↓
Execute Recovery
   ↓
Verify Recovery
   ↓
LLM/Agent Evaluation
   ↓
Incident Resolution
   ↓
Postmortem
   ↓
Store Learning
```

---

# 2. MOST IMPORTANT DESIGN PRINCIPLE

ARGUS must not blindly trust the LLM.

Every important decision must have:

* evidence
* confidence score
* tool results
* evaluation
* validation
* fallback behavior
* human approval when required

Never allow the LLM to directly execute arbitrary shell commands.

Use allowlisted tools only.

---

# 3. HIGH-LEVEL ARCHITECTURE

```text
                    ┌─────────────────────┐
                    │     Web Dashboard   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      FastAPI        │
                    │       Backend       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   LangGraph        │
                    │  ARGUS Supervisor   │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             ▼                 ▼                 ▼
      Detection Agent   Diagnosis Agent   Recovery Agent
             │                 │                 │
             └─────────────────┼─────────────────┘
                               │
                               ▼
                         MCP Tool Layer
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
    Metrics Tool          Logs Tool            Git Tool
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                               ▼
                          RAG Knowledge
                               │
                               ▼
                       Historical Incidents
                       Runbooks / Documents
                               │
                               ▼
                          PostgreSQL
                               │
                               ▼
                         Vector Database

                       ┌───────────────┐
                       │  LangSmith    │
                       │               │
                       │ Tracing       │
                       │ Evaluation    │
                       │ Datasets      │
                       │ Experiments   │
                       │ Monitoring    │
                       └───────────────┘
```

---

# 4. TECH STACK

Backend: Python 3.11+, FastAPI, Pydantic, SQLAlchemy, PostgreSQL

AI: LangChain, LangGraph, configurable LLM provider, embeddings, RAG, structured outputs

Observability/Evaluation: LangSmith

MCP: MCP-compatible server/tool architecture, Python MCP implementation

Vector DB: ChromaDB or FAISS for local dev; architect retrieval layer to be swappable for Qdrant / pgvector / Pinecone later

Caching/state: Redis if useful — app must still work without Redis in local dev

Frontend: React + TypeScript + Vite (inspect existing frontend before replacing anything)

Testing: pytest, pytest-asyncio, integration tests, agent workflow tests

Deployment: Docker-ready, Docker Compose-ready — must NOT require Docker for local development

---

# 5. PROJECT STRUCTURE

```text
argus/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/routes/
│   │   │   ├── health.py
│   │   │   ├── incidents.py
│   │   │   ├── agents.py
│   │   │   ├── evaluations.py
│   │   │   ├── metrics.py
│   │   │   └── recovery.py
│   │   ├── agents/
│   │   │   ├── supervisor.py
│   │   │   ├── detection_agent.py
│   │   │   ├── diagnosis_agent.py
│   │   │   ├── recovery_agent.py
│   │   │   ├── evaluation_agent.py
│   │   │   └── postmortem_agent.py
│   │   ├── graph/
│   │   │   ├── state.py
│   │   │   ├── graph.py
│   │   │   └── nodes.py
│   │   ├── rag/
│   │   │   ├── ingestion.py
│   │   │   ├── retriever.py
│   │   │   ├── embeddings.py
│   │   │   └── knowledge_base.py
│   │   ├── mcp/
│   │   │   ├── server.py
│   │   │   ├── metrics_tools.py
│   │   │   ├── logs_tools.py
│   │   │   ├── deployment_tools.py
│   │   │   └── incident_tools.py
│   │   ├── evaluation/
│   │   │   ├── evaluators.py
│   │   │   ├── datasets.py
│   │   │   ├── metrics.py
│   │   │   └── benchmark.py
│   │   ├── ml/
│   │   │   ├── anomaly_detection.py
│   │   │   ├── failure_prediction.py
│   │   │   └── feature_engineering.py
│   │   ├── database/
│   │   │   ├── models.py
│   │   │   ├── session.py
│   │   │   └── repositories.py
│   │   ├── services/
│   │   │   ├── incident_service.py
│   │   │   ├── recovery_service.py
│   │   │   ├── evaluation_service.py
│   │   │   └── monitoring_service.py
│   │   ├── config.py
│   │   └── logging_config.py
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/{components,pages,services,hooks,types}
│   └── package.json
├── data/{incidents,runbooks,logs,evaluation}
├── docs/{architecture,api,agents,mcp,evaluation,deployment,failure-analysis}.md
├── scripts/{seed_data.py,ingest_knowledge.py,run_benchmark.py}
├── docker-compose.yml
├── Dockerfile
├── README.md
└── .gitignore
```

---

# 6. ENVIRONMENT CONFIGURATION

`.env.example` — never hardcode secrets:

```text
LLM_PROVIDER=
LLM_MODEL=
OPENAI_API_KEY=

LANGSMITH_API_KEY=
LANGSMITH_PROJECT=
LANGSMITH_TRACING_V2=true

DATABASE_URL=

REDIS_URL=

VECTOR_DB_PATH=

ARGUS_ENV=development
```

App must start even when optional integrations are unavailable (no LangSmith key → still runs; no Redis → fallback mode; no external monitoring API → simulator mode). Never expose API keys to frontend code.

---

# 7. DEMO / SIMULATION MODE

Built-in synthetic production environment so recruiters can run ARGUS without real infrastructure.

Simulated metrics: latency, error_rate, token_usage, retrieval_score, hallucination_score, tool_failure_rate, request_volume, cpu_usage, memory_usage, api_success_rate.

Example:
```text
Normal:   latency=1.2s  error_rate=0.5%  retrieval_score=0.91
Incident: latency=8.5s  error_rate=14%   retrieval_score=0.53  token_usage=+230%
```

Buttons: Generate Normal Traffic / Inject Latency Incident / Inject LLM Failure / Inject RAG Degradation / Inject Tool Failure / Inject Cost Spike / Inject Agent Loop.

---

# 8. ML FAILURE DETECTION

Baseline first: statistical thresholds, rolling mean/std, z-score, Isolation Forest if useful. Architect so a trained model can replace the baseline later.

Output:
```json
{
  "anomaly_detected": true,
  "severity": "high",
  "confidence": 0.94,
  "affected_metrics": ["latency", "error_rate"]
}
```

---

# 9. FAILURE CLASSIFICATION

Categories: LLM_FAILURE, RAG_DEGRADATION, RETRIEVAL_FAILURE, TOOL_FAILURE, API_FAILURE, LATENCY_SPIKE, COST_SPIKE, AGENT_LOOP, DATA_QUALITY, UNKNOWN.

Return category + confidence + evidence. Never return only an LLM-generated label.

---

# 10. LANGGRAPH WORKFLOW

State fields: incident, metrics, logs, evidence, failure_type, failure_confidence, root_cause, retrieved_runbooks, recovery_options, risk_score, selected_strategy, approval_required, approval_status, execution_result, verification_result, evaluation_result, final_status.

```text
START → Detect → Classify → Collect Evidence → Retrieve Knowledge → Diagnose
      → Generate Recovery Options → Risk Assessment → Human Approval?
        ├── YES → Approval → Execute
        └── NO  → Execute
                     → Verify → Evaluate → Postmortem → END
```

Conditional routing: low confidence → Human Review; high risk → Human Approval; verification failure → re-diagnose (bounded retries — prevent infinite loops).

---

# 11. RAG SYSTEM

Knowledge base: runbooks, previous incidents, troubleshooting guides, architecture docs, deployment procedures, known failure patterns.

RAG returns: document, chunk, source, relevance_score, metadata. Diagnosis agent must cite retrieved evidence internally — never claim knowledge unsupported by retrieval.

---

# 12. MCP LAYER

Tools: get_system_metrics, get_recent_logs, get_incident_history, get_deployment_history, get_service_health, search_runbooks, simulate_rollback, execute_rollback, restart_service, switch_model, reindex_vector_store, create_incident, update_incident.

**Separate READ tools from WRITE/ACTION tools.** Action tools require: allowlist, validation, risk classification, audit logging. Never expose arbitrary command execution.

---

# 13. HUMAN-IN-THE-LOOP

High-risk actions MUST require approval. Low-risk read-only actions can auto-execute. Approval UI shows: action, risk, confidence, expected recovery probability, potential impact, evidence count.

---

# 14. RECOVERY STRATEGY ENGINE

Generate multiple strategies per incident, each with success probability + risk, grounded in historical incidents / rules / simulation / model output — never an LLM inventing numbers ungrounded. Label estimated values clearly.

---

# 15. COUNTERFACTUAL RECOVERY SIMULATOR (signature feature)

Before executing recovery, simulate possible outcomes for each strategy (recovery probability per option) and recommend the safest high-confidence option. Show expected benefit, risk, confidence, evidence, reversibility.

---

# 16. VERIFICATION

After executing recovery, do NOT assume success — compare before/after metrics and explicitly set `recovery_verified: true/false`. If false, return to diagnosis with a bounded retry count.

---

# 17. LANGSMITH INTEGRATION

Full tracing across Supervisor → Detection → Diagnosis → Retriever → Recovery → Tools → Evaluation, capturing inputs/outputs/latency/token usage/model/tool calls/errors/metadata (incident_id, failure_type, severity, environment, agent_name, recovery_strategy).

---

# 18. LANGSMITH EVALUATION

Datasets/metrics for: Diagnosis (correctness, relevance, groundedness), RAG (retrieval relevance, context quality, faithfulness), Agent (tool selection accuracy, trajectory quality, task completion), Recovery (success rate, unsafe action rate, verification success). Build a benchmark pipeline to compare agent versions (v1 vs v2).

---

# 19. LOCAL EVALUATION (must work without LangSmith credentials)

Metrics: Detection Accuracy/Precision/Recall/F1, Diagnosis Accuracy, RAG Retrieval Score, Groundedness, Recovery Success Rate, Unsafe Action Rate, Mean Recovery Time, Average Latency, Average Token Cost. Generate a report. **Never fabricate benchmark results — the application must calculate them for real.**

---

# 20. FAILURE INJECTION TESTING

Automated tests for: LLM timeout, RAG retrieval degradation, tool failure, API 500, latency spike, cost spike, hallucinated diagnosis, low-confidence diagnosis, unsafe recovery attempt, recovery verification failure.

---

# 21. SECURITY

Environment variables, API auth architecture, input validation, tool allowlisting, action authorization, audit logging, rate-limiting architecture, no arbitrary shell execution, no secrets in logs, no API keys in frontend. Document all of this in the README.

---

# 22. DATABASE MODELS

**Incident**: id, title, description, severity, status, failure_type, confidence, created_at, resolved_at
**MetricSnapshot**: id, incident_id, metric_name, value, timestamp
**Diagnosis**: id, incident_id, root_cause, confidence, evidence, created_at
**RecoveryAction**: id, incident_id, strategy, risk, approval_status, execution_status, result, created_at
**Evaluation**: id, incident_id, metric, score, details, created_at
**AuditLog**: id, incident_id, actor, action, result, timestamp

---

# 23. API ENDPOINTS

```text
GET  /health
GET  /api/incidents
GET  /api/incidents/{id}
POST /api/incidents/simulate
POST /api/incidents/{id}/analyze
GET  /api/incidents/{id}/diagnosis
GET  /api/incidents/{id}/recovery-options
POST /api/incidents/{id}/approve
POST /api/incidents/{id}/reject
POST /api/incidents/{id}/execute
GET  /api/incidents/{id}/evaluation
GET  /api/metrics
POST /api/simulation/inject
POST /api/evaluation/run
GET  /api/evaluation/benchmark
```

Use proper Pydantic request/response schemas.

---

# 24. FRONTEND DASHBOARD

Professional engineering dashboard — not a basic CRUD app. Pages: Dashboard (system overview), Incidents (list/filter), Incident Details (timeline, metrics, logs, root cause, evidence, agent trace, recovery options, risk, approval, execution, verification, evaluation), Agent Trace (visualize pipeline), Evaluation (charts), Simulation (injection buttons), Settings (model/env/LangSmith/DB/vector-DB/MCP status — never expose secrets).

---

# 25. OBSERVABILITY

Structured logging with timestamp, request_id, incident_id, agent, action, duration, status, error. Health info for LLM/PostgreSQL/Vector DB/LangSmith/MCP.

---

# 26. POSTMORTEM GENERATION

Structure: Incident Summary, Impact, Detection, Root Cause, Evidence, Recovery Action, Why This Action Was Selected, Verification, Timeline, Lessons Learned, Recommended Preventive Actions. Store in DB, export as Markdown.

---

# 27. LEARNING FROM PREVIOUS INCIDENTS

New incident → retrieve similar incidents → compare root causes/strategies → use historical outcomes. Call this **experience-based retrieval / historical learning** — do not claim the LLM has "learned" unless actual fine-tuning is implemented.

---

# 28. FINE-TUNING READINESS

Do not fine-tune in the first implementation. Generate a clean dataset format from resolved incidents in `data/fine_tuning/`:
```json
{"incident": "...", "evidence": "...", "root_cause": "...", "recovery": "...", "verification": "..."}
```
Document how this could later be used to fine-tune a specialized diagnosis model.

---

# 29. DEMO SCENARIO ("Run ARGUS Demo" button)

Start simulated healthy system → inject RAG degradation → detect anomaly → create incident → collect metrics/logs → diagnose → retrieve historical incident → generate recovery strategies → calculate risk → request human approval → execute simulated recovery → verify → run evaluation → generate postmortem. Entire workflow visible on dashboard.

---

# 30. README

Sections: Problem, Why Existing AI Applications Fail, Solution, Architecture, System Workflow, Agent Architecture, LangGraph, MCP, RAG, LangSmith, Evaluation, Failure Injection, Human-in-the-Loop, Security, Tech Stack, Installation, Environment Setup, Running Locally, Demo, API Documentation, Testing, Benchmarking, MLOps, Future Improvements. Include Mermaid diagrams. Add screenshots only after UI is actually implemented — never fabricate screenshots or metrics.

---

# 31. TESTING REQUIREMENTS

Run pytest + frontend tests/build, fix all errors. Test: backend startup, DB connection, RAG ingestion, retrieval, agent graph, MCP tools, simulation, incident creation, diagnosis, approval, recovery, verification, evaluation — plus failure cases.

---

# 32. ERROR HANDLING

Fail gracefully for every optional dependency:
- LLM unavailable → "ARGUS switched to fallback diagnostic mode."
- Vector DB unavailable → "Historical evidence disabled."
- MCP tool unavailable → "Recovery action blocked."
- LangSmith unavailable → "Local logging remains active."

Never crash the whole app because one optional service is down.

---

# 33. DEVELOPMENT STRATEGY — WORK IN PHASES, DO NOT SKIP AHEAD

**Phase 1** — Project setup: backend, frontend, configuration, database, health endpoint. Run tests.
**Phase 2** — Simulation engine: metrics, logs, failure injection, incident creation. Run tests.
**Phase 3** — ML detection: anomaly detection, failure classification. Run tests.
**Phase 4** — RAG: documents, ingestion, embeddings, retrieval, historical incidents. Run tests.
**Phase 5** — LangGraph: state, agents, conditional routing, recovery workflow. Run tests.
**Phase 6** — MCP: read tools, action tools, permissions, audit logging. Run tests.
**Phase 7** — Human approval + recovery: approval UI, execution, verification. Run tests.
**Phase 8** — LangSmith: tracing, metadata, datasets, evaluation, experiment support. Run tests.
**Phase 9** — Frontend: dashboard, incident page, trace page, evaluation page, simulation page. Run tests/build.
**Phase 10** — MLOps + production hardening: structured logs, Docker, health checks, CI/CD config, documentation.
**Phase 11** — Final benchmark and demo.

---

# 34. IMPORTANT CODING RULES

1. Do not hardcode API keys.
2. Do not fabricate evaluation metrics.
3. Do not fabricate LangSmith results.
4. Do not use arbitrary shell execution.
5. Do not create fake AI features that only display static text.
6. Every dashboard metric must come from actual backend data.
7. Every agent must have a clear responsibility.
8. Use structured outputs.
9. Validate tool inputs.
10. Add retries with limits.
11. Prevent infinite agent loops.
12. Log important actions.
13. Add tests for every critical workflow.
14. Keep components modular.
15. Use type hints.
16. Use clear docstrings.
17. Handle errors gracefully.
18. Keep secrets server-side.
19. Make integrations optional for local development.
20. Do not replace working code unnecessarily.

---

# 35. FINAL QUALITY BAR

Not "the app runs" — but Real Problem → Real Architecture → Real Agents → Real Tools → Real RAG → Real Evaluation → Real Observability → Real Failure Injection → Real Recovery Workflow → Real Human Approval → Real Verification → Real Benchmark. Should feel like a miniature production AI reliability platform, not a college demo.

---

# 36. FINAL COMMAND (give this to Antigravity first)

First inspect the existing project and environment. Do NOT delete or overwrite existing work without understanding it. Create a short implementation plan. Then implement **Phase 1 only**. Run tests. Show me: (1) what files were created/modified, (2) what was implemented, (3) commands used, (4) test results, (5) any errors, (6) what should be implemented next. Then continue phase-by-phase. Do not claim a feature is complete until it actually works.

At the end, provide: complete architecture, working local application, test results, benchmark results, README, `.env.example`, Docker configuration, deployment instructions, demo instructions, resume-ready project description, list of future improvements.

The project name must remain: **ARGUS — Autonomous AI Reliability & Recovery Platform**

---

# 37. ADDENDUM — Implementation Notes

> These notes clarify and extend Sections 1-36 above for this specific build.
> They do not override anything in Sections 1-36 — read both together.
> Wherever Sections 1-36 say "OPENAI_API_KEY" or reference OpenAI as the
> example LLM provider, use **Gemini** instead for this implementation (see
> 37.1). The rest of this addendum covers data sourcing (37.2-37.4).

## 37.1 — LLM Provider: Use Gemini, not OpenAI

Wherever the spec above references an LLM provider/API key (Sections 4, 6,
17, 34), implement it using **Google's Gemini API**, not OpenAI:

- Environment variable: `GOOGLE_API_KEY` (from Google AI Studio —
  https://aistudio.google.com — free tier, no billing required to start)
- `LLM_PROVIDER=gemini`, `LLM_MODEL=gemini-2.0-flash` as the default in
  `.env.example`
- LangChain integration: `langchain-google-genai`'s `ChatGoogleGenerativeAI`
- Keep the provider abstraction generic (per Section 4's "configurable LLM
  provider") so a second provider (e.g. Groq, for a cost/latency
  comparison in the Phase 8 benchmark) can be added later without
  rewriting agent code — but Gemini is the default and primary provider
  for this build.
- Embeddings for RAG (Section 11): prefer a **local, free** embedding
  model (`sentence-transformers`) over a paid embeddings API, so the RAG
  pipeline has zero marginal cost. Only use Gemini's embedding endpoint if
  local embedding quality proves insufficient during Phase 4 testing.

## 37.2 — Prefer Real Data Over Synthetic, Wherever Feasible

Section 7 describes a synthetic simulation mode — keep that (it's still
necessary for the demo/recruiter experience and for generating labeled
training data on demand). But wherever real data can be used *instead of or
alongside* synthetic data without requiring real production infrastructure,
prefer it:

- **Runbooks (Section 11)**: Don't invent failure patterns from nothing.
  Base runbook content on **real, documented failure patterns** from public
  sources — e.g. real post-mortems and known-issues threads from
  LangChain/LlamaIndex/vector-DB GitHub repos, real OpenAI/Anthropic/Google
  API status-page incident write-ups, real RAG-degradation case studies
  from engineering blogs. Research these first, then draft runbooks
  grounded in them (see 37.3 for the drafting workflow).
- **Failure signatures**: where possible, base the *shape* of injected
  synthetic faults (Section 7) on real documented failure modes (e.g. a
  real embedding-dimension-mismatch incident, a real rate-limit cascade)
  rather than arbitrary random noise, so detection/classification is being
  trained and evaluated against realistic patterns, not invented ones.
- **Evaluation dataset (Section 19)**: where a real, published incident
  report can be adapted into a golden-dataset test case (with the specific
  numbers anonymized/adjusted if needed), prefer that over a fully
  invented case.
- Metrics themselves (latency, error_rate, token_usage — the actual
  time-series numbers) remain synthetic/simulated per Section 7, since
  there is no real production system to monitor — that's expected and
  fine. "Prefer real data" applies to the *content/knowledge* layer
  (runbooks, failure patterns, evaluation cases), not to fabricating a
  fake real production deployment.

## 37.3 — Let the LLM Draft Content, With Human Review

For runbooks, documentation, and any other written knowledge-base content
(Section 11): use the LLM (Gemini) to **draft** this content based on the
real sources gathered per 37.2, rather than hand-writing every document.
Workflow:
1. Research/gather real reference material for a failure category
2. Prompt the LLM to draft a runbook in the Section 11 format
   (Incident / Symptoms / Root Cause / Recommended Recovery), grounded in
   the gathered material
3. Present the draft for human review/edit before it's ingested into the
   vector store — do not auto-ingest unreviewed LLM output as ground-truth
   knowledge, since the diagnosis agent will treat it as trusted evidence
   per Section 11's "must cite retrieved evidence" rule

## 37.4 — Historical Incidents: Bootstrap, Don't Fabricate

Per Section 27, ARGUS uses "experience-based retrieval" over historical
incidents. For this build:

- **Do not pre-seed a fake incident history.** The historical-incidents
  knowledge base starts empty (or near-empty, aside from reviewed runbooks
  from 37.3).
- The system **accumulates real historical incidents itself**, over time,
  as a natural side effect of normal use: every incident that runs through
  the full Section 1 lifecycle (detect → diagnose → recover → verify →
  postmortem) and reaches `resolved` status gets written to the database
  (Section 22's `Incident` table) and then ingested into the RAG knowledge
  base (Section 11) as a retrievable historical case for future incidents
  to learn from.
- This means retrieval quality legitimately improves the more the
  simulation is run — early incidents will have thin/no historical
  context (retrieval returns runbooks only), while later incidents benefit
  from real accumulated history. This progression is expected and worth
  measuring explicitly in the Phase 8 evaluation (e.g. compare diagnosis
  accuracy on the first 5 vs. last 5 incidents in an eval run) — it's a
  genuine, honest signal of the "learning" the system is doing, in
  contrast to Section 27's warning against claiming fake self-learning.

## 37.5 — Fine-Tuning Dataset: Auto-Generate, Don't Hand-Write

Per Section 28, fine-tuning itself stays optional/deferred, but the
dataset-generation step should not be a manual one-off task:

- Write a script (`scripts/generate_finetune_dataset.py`, alongside
  `scripts/run_benchmark.py` from Section 5) that queries the database for
  all `resolved` incidents (Section 22 tables: `Incident` joined with its
  `Diagnosis` and `RecoveryAction` and the verification result) and
  **automatically exports** them into the JSON format specified in
  Section 28 (`incident`, `evidence`, `root_cause`, `recovery`,
  `verification`).
- This script should be safe to re-run at any time (e.g. after every N new
  resolved incidents) and simply append/refresh `data/fine_tuning/dataset.jsonl`
  — no manual curation step required to keep the dataset current.
- This ties directly into 37.4: as historical incidents accumulate through
  real usage, the fine-tuning dataset grows automatically from the same
  underlying data, with zero duplicate effort.

