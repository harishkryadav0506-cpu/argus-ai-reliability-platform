# ARGUS Walkthrough Demo Script (2–3 Minutes)

This script provides an exact, timestamped guide for recording a concise, high-impact demonstration of the **ARGUS Autonomous AI Reliability & Recovery Platform**.

---

## Video Specifications
- **Target Duration**: 2 minutes 30 seconds (maximum 3 minutes).
- **Resolution**: 1080p (1920x1080) or 1440p (2560x1440).
- **Audio**: Clear microphone voiceover, dark-mode screen capture.
- **Starting State**:
  - Backend running: `uvicorn app.main:app --port 8000` (in `backend/`).
  - Frontend running: `npm run dev` (in `frontend/`, open at `http://localhost:5173`).

---

## Walkthrough Breakdown

### 0:00 – 0:30 | The Hook & Problem Statement
- **Visual**: Start on `http://localhost:5173` (Dashboard view). Hover over the 10 live telemetry cards (latency, retrieval score, error rate, CPU utilization) while the telemetry stream ticks normally in emerald status.
- **Voiceover**:
  > "Modern GenAI and agentic applications fail silently: vector indexes corrupt, prompt chains loop endlessly, and LLM APIs degrade without throwing traditional HTTP crashes. Traditional APM tools like Datadog only see high latency or 500s—they can't diagnose embedding drift, retrieve operational runbooks, or safely execute stateful rollbacks.
  >
  > This is **ARGUS**—an autonomous AI reliability and self-healing platform built with LangGraph, Model Context Protocol (MCP), semantic RAG retrieval, and statistical anomaly ensembles."

---

### 0:30 – 1:15 | One-Click Section 29 Demo & Autonomous Detection
- **Visual**: Click the gradient **"Run ARGUS Demo (Section 29)"** button in the top action bar.
- **Visual Feedback**:
  - The 14-step interactive timeline banner expands.
  - Telemetry changes: Latency and token count rise, while `Retrieval Score` drops from `0.92` to `0.48` (warning amber/crimson indicator).
  - Step 1 through Step 4 illuminate: `Healthy Baseline` → `Inject RAG Degradation` → `ML Anomaly Detected` → `Incident Registered`.
  - Step 5 through 7 illuminate: `Telemetry & Logs Collected` → `Root Cause Diagnosed` → `RAG Runbook Retrieved`.
- **Voiceover**:
  > "With a single click, we trigger the Section 29 benchmark scenario. ARGUS injects a synthetic RAG degradation fault.
  >
  > Immediately, an ensemble of rolling Z-score detectors and Isolation Forests identifies the multivariate departure. The failure classifier predicts `RAG_DEGRADATION` with over 94% confidence, and registers an incident in PostgreSQL.
  >
  > Next, our Diagnosis Agent analyzes the telemetry and queries ChromaDB with local sentence-transformer embeddings, retrieving operational runbook `RB-002` covering embedding drift and HNSW index corruption."

---

### 1:15 – 1:55 | Counterfactual Simulation & Human-in-the-Loop MCP Execution
- **Visual**: Click **"Investigate Incident"** on the banner to navigate directly to `/incidents/{id}` (or navigate via the sidebar).
- **Visual Feedback**:
  - Point to the **Counterfactual Recovery Simulator** table showing candidate strategies:
    - `reindex_vector_store` ($P_{rec} = 0.88$, Risk: MEDIUM, Reversible: True).
    - `switch_model` ($P_{rec} = 0.65$).
    - `restart_service` ($P_{rec} = 0.45$, Risk: HIGH).
  - Point to the **Approval Gate**: LangGraph paused using native `interrupt()`.
  - Click **"Approve & Execute via MCP"**.
  - Show the live result: MCP tool `reindex_vector_store` executes, writes pre/post `AuditLog` rows, and returns status `success`.
- **Voiceover**:
  > "Before touching production, ARGUS's Recovery Engine runs a counterfactual simulation, calculating empirical recovery probabilities, reversibility bounds, and blast radius.
  >
  > Because modifying vector shards carries risk, LangGraph cleanly halts at a native interrupt gate. As an operator, I review the counterfactual trade-offs and approve the action.
  >
  > ARGUS executes `reindex_vector_store` through a standardized Model Context Protocol (MCP) server. Notice high-risk tools enforce authorization checks internally and write immutable audit logs before and after execution."

---

### 1:55 – 2:30 | Verification, Automated Learning & Benchmark Results
- **Visual**:
  - Point out the **Verification Result** card: Post-recovery telemetry verified ($SLA \ge 0.85$, recovery verified = true).
  - Point out the generated markdown **Postmortem Report** and note the automated ingestion into the historical incidents vector store.
  - Navigate to **Evaluation** (`/evaluation`).
  - Highlight the side-by-side version comparison table (`v1_baseline` vs `v2_argus`).
- **Voiceover**:
  > "Post-execution, ARGUS verifies the telemetry against operational SLAs. With retrieval scores restored to 0.92, the incident resolves. The Postmortem Agent drafts a root-cause report and automatically indexes the entire resolution into ChromaDB so future incidents benefit from this experience.
  >
  > On our Evaluation page, we measured ARGUS across 15 real simulated failure scenarios:
  > - Detection F1 increased from 0.85 to 0.96.
  > - Diagnosis accuracy jumped from 46.7% to 93.3%.
  > - Unsafe action rate dropped to 0%, while Mean Time to Recovery (MTTR) decreased by 180 seconds."

---

### 2:30 – 2:45 | Wrap-Up & Call to Action
- **Visual**: Navigate to **Settings** (`/settings`) showing live service health checks (`FastAPI`, `Postgres`, `ChromaDB`, `MCP Server`, `LLM Provider`) with zero exposed secrets.
- **Voiceover**:
  > "ARGUS is fully containerized with Docker Compose, tested end-to-end via GitHub Actions CI, and production-hardened with sliding-window rate limiting.
  >
  > Check out the complete source code, evaluation reports, and deployment instructions on GitHub."

---

## Recording Checklist
- [ ] Backend running on `:8000` with test database seeded or in-memory fallback active.
- [ ] Frontend running on `:5173` without browser console errors.
- [ ] Browser zoom set to 90% or 100% for optimal information density.
- [ ] Dark mode active.
