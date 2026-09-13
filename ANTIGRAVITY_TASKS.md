# Building ARGUS in Google Antigravity — Task Playbook

This scaffold already has **Phase 1 fully implemented and verified**:
- FastAPI app boots (`app/main.py`)
- Config loads with graceful defaults for every optional integration (`app/config.py`)
- Structured JSON logging (`app/logging_config.py`)
- Database session + 6 models: Incident, MetricSnapshot, Diagnosis,
  RecoveryAction, Evaluation, AuditLog (`app/database/`)
- `/health` endpoint reporting per-service status without ever crashing
- 2 passing tests confirming all of the above (`tests/test_health.py`)

**Verified locally**: `pytest tests/test_health.py -v` → 2 passed.

Start Antigravity from **Phase 2** onward using the prompts below. Feed one
phase at a time. Review the Artifact (plan + diff + test output) before
approving and moving to the next. Commit to git after every phase.

---

## Phase 0 — Orientation (give this first, exactly as spec Section 36 says)

```
Read docs/ARGUS_SPEC.md fully, including Section 37 (Addendum) at the
end — this is the canonical specification for this project, and Section
37 adds important clarifications about the LLM provider (Gemini, not
OpenAI) and data-sourcing approach that apply across every phase. Then
inspect the existing backend/ folder. Phase 1 is already implemented and
verified (app boots, /health works, DB models exist, 2 tests pass). Do
NOT modify or replace any Phase 1 code without first explaining why it's
necessary. Confirm you understand the full architecture, the Section 33
phase plan, and the Section 37 addendum, then give me a short
implementation plan for Phase 2 only. Do not implement anything yet.
```

## Phase 2 — Simulation Engine
```
Implement Phase 2 per docs/ARGUS_SPEC.md Sections 7 and 33: a simulation
engine that generates synthetic metrics (latency, error_rate, token_usage,
retrieval_score, hallucination_score, tool_failure_rate, request_volume,
cpu_usage, memory_usage, api_success_rate) for a simulated AI application,
plus fault-injection functions for: latency incident, LLM failure, RAG
degradation, tool failure, cost spike, agent loop. Wire this into new
endpoints POST /api/simulation/inject and a background task that
continuously generates "normal" traffic when no fault is active. When a
fault is injected and metrics cross a threshold, call a (stubbed for now)
incident_service.create_incident() function — implement incident creation
in app/services/incident_service.py using the Incident model from Phase 1.
Add tests for: normal traffic generation, each fault type, and incident
creation. Run pytest and show me the results.
```

## Phase 3 — ML Failure Detection
```
Implement Phase 3 per Section 8-9: in app/ml/anomaly_detection.py, build a
baseline detector using rolling mean/std + z-score thresholds on the
simulated metrics from Phase 2 (add Isolation Forest as a second signal,
not a replacement — ensemble the two). It must return the exact JSON shape
from Section 8 (anomaly_detected, severity, confidence, affected_metrics).
In app/ml/failure_prediction.py, implement failure classification into the
10 categories from Section 9, returning category + confidence + evidence
— never an LLM label alone at this phase (no LLM calls yet, that's Phase
5). Wire detection into the simulation loop from Phase 2 so a real anomaly
triggers real incident creation. Add tests with known synthetic
normal/abnormal metric windows and assert correct classification. Run
pytest and show me precision/recall on your test set.
```

## Phase 4 — RAG
```
Implement Phase 4 per Section 11 and Section 37.2-37.3: research real,
documented failure patterns for each of the 10 failure categories from
Section 9 (real GitHub issues/postmortems from LangChain, LlamaIndex,
vector-DB projects; real API status-page incident write-ups from
OpenAI/Anthropic/Google; real RAG-degradation case studies from
engineering blogs). For each category, use Gemini to DRAFT a runbook in
the Incident/Symptoms/Root-Cause/Recovery format from Section 11,
grounded in the real source material you found — then present each draft
to me for review before it's treated as final. Save the reviewed runbooks
as markdown files in data/runbooks/. In app/rag/ingestion.py, chunk and
embed these documents using a LOCAL embedding model
(sentence-transformers — no paid embeddings API, per Section 37.1) into
ChromaDB (app/rag/embeddings.py, app/rag/knowledge_base.py). In
app/rag/retriever.py, implement retrieve(query, k=3) returning document,
chunk, source, relevance_score, metadata per Section 11. Per Section
37.4, do NOT pre-seed any fake historical incidents — the historical-
incident side of the knowledge base starts empty and will be populated
later (Phase 5+) only from real incidents that actually complete the
lifecycle in this system. Write scripts/ingest_knowledge.py as the CLI
entrypoint for ingesting the reviewed runbooks. Add tests verifying
retrieval returns relevant runbooks for known failure signatures. Run
pytest and show me example retrieval results, plus the runbook drafts
for my review before finalizing them.
```

## Phase 5 — LangGraph Agents
```
Implement Phase 5 per Section 10: build the LangGraph state machine in
app/graph/graph.py using the state schema from app/graph/state.py (fields
listed in Section 10). Implement each agent as its own module in
app/agents/: detection_agent.py (wraps Phase 3's ML detector),
diagnosis_agent.py (calls an LLM via app/config.py's LLM_PROVIDER — support
at least two providers behind a common interface using LangChain's chat
model abstraction: ChatGoogleGenerativeAI for "gemini" and ChatGroq for
"groq", selected by config so switching providers is a one-line .env
change, not a code change — use LangChain's structured output parsing —
with retrieved RAG context from Phase 4 as grounding, and requires the
LLM to cite which retrieved evidence supports its root_cause), recovery_agent.py (generates multiple strategies with
grounded success probabilities per Section 14, not LLM-invented numbers),
evaluation_agent.py, and postmortem_agent.py. Per Section 37.4, add a step
in postmortem_agent.py (or a service it calls) that, once an incident
reaches `resolved` status, automatically ingests it into the same RAG
knowledge base from Phase 4 as a retrievable historical incident — this
is how the historical-incident side of retrieval bootstraps itself from
real usage instead of being pre-seeded. Wire the exact conditional
routing from Section 10: low confidence → human review, high risk → human
approval, failed verification → re-diagnose with a MAX_RETRIES=3 bound to
prevent infinite loops. If no LLM_PROVIDER is configured (see
app/config.py's llm_configured), diagnosis_agent must fall back to a
rule-based diagnosis using only the RAG-retrieved runbook match — do not
crash. Add tests for the graph completing end-to-end on a simulated
incident, and a test confirming the retry limit actually bounds the loop.
Run pytest and show me a full trace of one run.
```

## Phase 6 — MCP Layer
```
Implement Phase 6 per Section 12: build an MCP server in app/mcp/server.py
exposing the tools listed in Section 12, split clearly into READ tools
(app/mcp/metrics_tools.py, logs_tools.py — get_system_metrics,
get_recent_logs, get_incident_history, get_deployment_history,
get_service_health, search_runbooks) and ACTION tools
(app/mcp/deployment_tools.py, incident_tools.py — simulate_rollback,
execute_rollback, restart_service, switch_model, reindex_vector_store,
create_incident, update_incident). Every ACTION tool must: check an
allowlist, validate its inputs, classify its own risk level (low/medium/
high), and write an AuditLog row (Phase 1 model) before and after
execution. execute_rollback and restart_service must refuse to run if not
called with an approved=True flag when risk is high — enforce this in the
tool itself, not just in the calling agent. Update recovery_agent.py
(Phase 5) to call these MCP tools instead of any placeholder logic. Add
tests: one confirming a high-risk tool is blocked without approval, one
confirming audit logs are written for every action tool call. Run pytest
and show me the audit log output for one blocked and one approved action.
```

## Phase 7 — Human Approval + Recovery
```
Implement Phase 7 per Section 13: add POST /api/incidents/{id}/approve and
/reject endpoints that update the RecoveryAction's approval_status (Phase
1 model) and resume the LangGraph flow via a proper interrupt/resume
pattern (LangGraph's `interrupt()` — not re-running the whole graph from
scratch). Implement app/rag or app/graph verification logic per Section
16: after execution, compare before/after metrics and set
verification_result explicitly true/false; false routes back to diagnosis
(respecting the Phase 5 retry bound). Add GET
/api/incidents/{id}/recovery-options showing the counterfactual simulator
output from Section 15 (each strategy's recovery probability, risk,
reversibility) before any approval decision is made. Add tests for: the
full approve→execute→verify-success path, the approve→execute→
verify-failure→re-diagnose path, and the reject path. Run pytest and show
results.
```

## Phase 8 — LangSmith
```
Implement Phase 8 per Sections 17-19. Wire LANGCHAIN_TRACING_V2,
LANGCHAIN_API_KEY, LANGCHAIN_PROJECT from app/config.py's
langsmith_configured property — when false, confirm tracing is skipped
silently and local structured logging (Phase 1) continues, per Section 32.
When true, attach the metadata fields from Section 17
(incident_id, failure_type, severity, environment, agent_name,
recovery_strategy) to every graph run. Implement local evaluation (works
WITHOUT LangSmith) in app/evaluation/evaluators.py and metrics.py per
Section 19 — compute real Detection F1, Diagnosis Accuracy, RAG Retrieval
Score, Recovery Success Rate, Unsafe Action Rate, Mean Recovery Time from
actual incidents in the database, never fabricated numbers. Build
app/evaluation/benchmark.py implementing the version-comparison pipeline
from Section 18. Add scripts/run_benchmark.py as the CLI entrypoint. Run
it against at least 15 simulated incidents and show me the real
computed report (format matches Section 19's example). Per Section 37.5,
also implement scripts/generate_finetune_dataset.py: query the database
for all resolved incidents (joining Incident + Diagnosis + RecoveryAction
+ verification result) and export them into the Section 28 JSON format
into data/fine_tuning/dataset.jsonl. Make it safe to re-run repeatedly
(append/refresh, no duplicate entries, no manual curation step). Run it
against your 15 simulated incidents and show me a few real generated
dataset rows.
```

## Phase 9 — Frontend Dashboard
```
Implement Phase 9 per Section 24. Inspect the empty frontend/ folder and
scaffold a React + TypeScript + Vite app. Build: Dashboard page (system
health per Section 24's example, driven by real GET /api/metrics data —
never hardcoded), Incidents list/filter page, Incident Detail page
(timeline, metrics, logs, root cause, evidence, agent trace, recovery
options with the counterfactual probabilities, approval buttons, execution
result, verification result, evaluation scores), Agent Trace page
(visualize the Section 3 pipeline for a specific incident), Evaluation
page (charts from Phase 8's benchmark data), Simulation page (buttons
wired to POST /api/simulation/inject from Phase 2), Settings page (shows
LLM/LangSmith/DB/vector-DB/MCP status from /health — never render secret
values). Make it look like a real engineering tool, not a default
Bootstrap template — dense information, dark-mode friendly, clear status
colors. Run the frontend build and confirm no errors.
```

## Phase 10 — MLOps + Production Hardening
```
Implement Phase 10 per Section 33: confirm structured logging (Phase 1)
covers every agent/tool call end-to-end. Finalize docker-compose.yml to
include the frontend build, add healthchecks for every service. Write a
GitHub Actions CI workflow (.github/workflows/ci.yml) running backend
pytest and frontend build/lint on every push. Write docs/deployment.md
with real instructions matching what you actually built (no invented
steps). Do a full security review against Section 21's checklist and fix
any gaps you find (e.g., confirm no API keys ever reach frontend code,
confirm rate-limiting architecture exists even if just a placeholder
middleware for now).
```

## Phase 11 — Final Benchmark + Demo
```
Implement the one-click demo from Section 29: a single endpoint or
frontend button that runs the full 14-step demo scenario end-to-end
against the simulation engine, visible live on the dashboard. Run the full
eval/benchmark suite from Phase 8 one final time and record the real
results. Then produce, using only what was actually built and actually
measured: (1) an updated README.md following Section 30's structure with
real Mermaid diagrams of the architecture you built, (2) a resume-ready
project description paragraph, (3) a list of genuine future improvements,
(4) docs/demo_script.md for recording a 2-3 minute walkthrough video. Do
not include any screenshot, metric, or claim that doesn't correspond to
something that actually runs in this repo.
```

---

## Antigravity-specific tips

- **Feed docs/ARGUS_SPEC.md as context on every single phase**, not just
  Phase 0 — reference it explicitly in each prompt (already done above) so
  the agent doesn't drift from the spec's exact schemas/endpoints/rules.
- **Rule 2 and 3 from Section 34 are the ones to watch most closely**: read
  every eval/benchmark number the agent reports before trusting it. Ask it
  to show you the raw computation, not just the summary, at least once per
  phase.
- **Use Manager View to parallelize** Phase 3 (ML) and Phase 4 (RAG) — they
  don't depend on each other and can run as separate agents once Phase 2 is
  merged.
- **Commit after every phase.** Several phases (5, 6, 7) touch the same
  graph/agent files repeatedly — you want clean rollback points.
