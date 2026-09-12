# ARGUS Video Walkthrough Script (2–3 Minutes)

This script provides an exact, timestamped guide for recording a concise, high-impact demonstration of the **ARGUS Autonomous AI Reliability & Recovery Platform**. Every step references actual UI elements, endpoints, and data structures present in the codebase.

---

## Technical Setup & Starting State
- **URL**: `http://localhost:3000` (Docker Nginx) or `http://localhost:5173` (Vite dev server)
- **Backend**: FastAPI running at `http://localhost:8000` with PostgreSQL and ChromaDB connected
- **Resolution**: 1080p (1920x1080) in Dark Mode
- **Initial State**: Baseline healthy telemetry stream ticking (green indicators)

---

## Timed Walkthrough Script

### (0:00 – 0:20) Introduction & The Problem
- **Screen**: Start on the **Dashboard** (`/`).
- **UI Elements to Point At**:
  - Live Telemetry Grid (10 operational metric cards: Latency, Error Rate, Retrieval Score, Token Usage, Cost, etc.) ticking in healthy green status.
  - Top summary cards: Open Incidents, Mean Recovery Time, Detection F1.
- **Narrator Voiceover**:
  > "Modern GenAI pipelines—LLMs, RAG systems, and autonomous agents—fail silently. Traditional APM tools like Datadog or Prometheus only see generic HTTP status codes and endpoint latencies; they cannot detect vector embedding drift, silent hallucination surges, or recursive reasoning loops.
  > 
  > This is **ARGUS**, an autonomous AI reliability and self-healing platform built on LangGraph, Model Context Protocol (MCP), semantic RAG retrieval, and statistical ML anomaly ensembles."

---

### (0:20 – 0:50) Fault Injection & Live Dashboard Reaction
- **Screen**: Click **Simulation** in the top navigation bar (`/simulation`).
- **UI Elements to Point At**:
  - Point to the **Live Stream Status** banner showing `HEALTHY BASELINE`.
  - Scroll to the 6 Canonical Fault Cards: `LATENCY_SPIKE`, `LLM_FAILURE`, `RAG_DEGRADATION`, `TOOL_FAILURE`, `COST_SPIKE`, and `AGENT_LOOP`.
  - Click the purple **"Inject Mode"** button on the `RAG_DEGRADATION` card.
- **Visual Reaction**:
  - Show the **Live Stream Status** banner instantly flip from emerald green `HEALTHY BASELINE` to crimson `SYSTEM DEGRADED`.
  - Point to the metric cards: `RAG Retrieval Score` drops to `0.480` (below the 0.850 SLA threshold) and `Hallucination Score` surges to `0.550` (above the 0.100 threshold).
  - Click **Dashboard** in top nav: show the **Recent Incidents** table where the anomaly detector and dual-model ensemble classifier have automatically registered an incident: `RAG_DEGRADATION` with High severity and a non-trivial confidence score (e.g. 91%).
- **Narrator Voiceover**:
  > "Let’s inject a synthetic fault. On the Simulation page, I trigger `RAG_DEGRADATION`.
  > 
  > Instantly, our rolling Z-score and Isolation Forest ensemble flags the multivariate departure. The Live Stream Status flips to 'DEGRADED' as retrieval scores plummet below our 0.85 SLA threshold. On the Dashboard, ARGUS’s dual-model ensemble classifier has already registered an incident in PostgreSQL with 91% confidence, initiating autonomous diagnosis."

---

### (0:50 – 1:30) Deep Dive: Agent Trace, Gemini Diagnosis & Grounded Runbook
- **Screen**: In the Recent Incidents table, click on the newly registered `RAG_DEGRADATION` incident to open **Incident Detail** (`/incidents/{id}`).
- **UI Elements to Point At**:
  - **Metric Snapshot at Incident Time** table: Point out the 13 metrics. Highlight that `retrieval_score` (0.480) and `hallucination_score` (0.550) show red `BREACH` badges with their exact SLA thresholds, while normal metrics (`error_rate = 0.009`, `cpu_usage = 49.5%`) cleanly display green `OK` status.
  - Click the **"Diagnosis & Evidence"** tab:
    - Point to the **Root Cause Diagnosis** section powered by Google Gemini (`gemini-3.6-flash`).
    - Point to the **Runbook Citations** box: Show the exact cited runbook `RB-002: RAG Embedding Drift & Vector DB Degradation` retrieved via local ONNX ChromaDB dense embeddings (`all-MiniLM-L6-v2`).
  - Click the **"Agent Trace & Graph State"** tab:
    - Point to the LangGraph node execution flow: `DetectionNode` $\to$ `RunbookRetrievalNode` $\to$ `DiagnosisNode` $\to$ `RecoveryAgentNode` $\to$ `HumanApprovalGate`.
    - Show that execution is cleanly paused at `HumanApprovalGate` via a native LangGraph `interrupt()`.
- **Narrator Voiceover**:
  > "Drilling into the incident, the 13-metric snapshot precisely isolates the breached SLA targets without false positives.
  > 
  > In the Diagnosis tab, our Diagnosis Agent invoked Google Gemini 3.6 Flash, grounding its analysis in operational runbook RB-002 retrieved from ChromaDB using local ONNX MiniLM embeddings—with zero external embedding API cost.
  > 
  > In the Agent Trace tab, you can see the full LangGraph state machine. Because remediation carries operational risk, LangGraph cleanly halted at an interrupt gate, waiting for human operator authorization."

---

### (1:30 – 2:10) Counterfactual Recovery Simulator, Approval & MCP Tool Execution
- **Screen**: Click the **"Recovery Simulator & Approval"** tab on the incident detail page.
- **UI Elements to Point At**:
  - Point to the **Counterfactual Strategy Comparison** table:
    - `execute_rollback` / `reindex_vector_store`: Recommended (Recovery Probability: ~93%, Risk: MEDIUM, Reversible: Yes).
    - Alternative strategies with lower expected utilities and higher blast radius.
  - Point to the **Operator Approval Form**:
    - Select the recommended strategy.
    - Type into the Operator Notes field: `"Approved rollback for RAG index recovery - Lead SRE"`.
  - Click the emerald **"Approve & Execute via MCP"** button.
- **Visual Reaction**:
  - The button enters a brief loading state.
  - The **Execution Result Banner** appears: Status `success`, executed via MCP tool layer.
  - The **SLA Verification Result** box populates: `verified: true`, confirming post-execution retrieval score has returned above 0.850.
- **Narrator Voiceover**:
  > "Before touching production, ARGUS’s Recovery Agent simulates candidate strategies counterfactually, computing empirical recovery probability, reversibility, and blast radius.
  > 
  > As the on-call engineer, I select the recommended strategy and click 'Approve & Execute via MCP'.
  > 
  > The system resumes the LangGraph workflow—or executes via our deterministic dual-path fallback if the thread was rebooted—calling the standardized Model Context Protocol tool with immutable audit logging. Post-execution, the SLA Verification Node checks live telemetry, validating that the retrieval score has recovered to baseline."

---

### (2:10 – 2:40) Incident Resolution & Empirical Evaluation Benchmarks
- **Screen**:
  - Point to the top incident status header: The incident badge transitions to green **`RESOLVED & VERIFIED`**.
  - Click the **"Postmortem"** tab: Show the auto-generated markdown postmortem report (Root cause, timeline, actions taken, preventive recommendations) and mention its automated ingestion into ChromaDB and `dataset.jsonl`.
  - Click **Evaluation** in the top navigation bar (`/evaluation`).
- **UI Elements to Point At**:
  - Point to the **Version Comparison Table** (`v1_baseline` vs `v2_argus` across 22 scenarios):
    - **Detection F1**: $0.875 \to 0.973$ (+9.8%)
    - **Diagnosis Accuracy**: $45.5\% \to 100.0\%$ (+54.5%)
    - **Recovery Success**: $16.7\% \to 100.0\%$ (+83.3%)
    - **Unsafe Action Rate**: $33.3\% \to 0.0\%$ (Zero unsafe actions)
    - **MTTR**: $230.8\text{s} \to 42.0\text{s}$ (4.5x faster recovery)
  - Point to the **Honesty Caveat** note on synthetic in-distribution evaluation.
- **Narrator Voiceover**:
  > "The incident transitions to 'Resolved & Verified', and the Postmortem Agent indexes the resolution into our knowledge base for continuous learning.
  > 
  > On our Evaluation page, we benchmarked ARGUS against a rule-based baseline across 22 canonical failure scenarios: Detection F1 reached 0.973, Diagnosis Accuracy increased from 45.5% to 100%, Unsafe Actions dropped from 33% to zero, and MTTR plunged from 230 seconds down to 42 seconds."

---

### (2:40 – 3:00) Engineering Rigor & QA Retrospective (Closing)
- **Screen**: Return to the **Dashboard** (`/`) or show the clean terminal / Docker status.
- **Narrator Voiceover**:
  > "What makes ARGUS genuinely production-ready isn’t just the architecture, but the engineering rigor behind it. The system underwent two rounds of extensive manual QA where 22 confirmed bugs were identified and fixed at the root cause.
  > 
  > This included re-architecting MCP execution to support dual-path thread resumption, eliminating artificial confidence score clustering, and catching an SLA-breach false-positive regression introduced by our own earlier patch.
  > 
  > ARGUS is fully containerized, open-source, and available on GitHub."

---

## Recording Tips
1. **Pacing**: Speak at a measured, confident pace. Don't rush through the transitions.
2. **Cursor Movement**: Move the cursor deliberately to the exact UI elements mentioned before clicking.
3. **Audio Quality**: Record in a quiet room with minimal background noise.
