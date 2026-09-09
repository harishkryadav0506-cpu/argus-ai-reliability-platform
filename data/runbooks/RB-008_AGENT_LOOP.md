# Runbook: Agent Circular Execution Loop and State Stagnation

- **Failure Type**: `AGENT_LOOP`
- **Severity**: High
- **Reference Incident / Source**: LangChain Issue #4518 "AgentExecutor RecursionLimitExceeded on Ambiguous Observation"; AutoGPT Incident Post-Mortem "Infinite Tool Re-Invocation on Uninformative Tool Response"

## Incident Description
An autonomous ReAct or LangGraph agent enters a repeating circular trajectory, re-executing the same tool calls or oscillating between two states without making measurable forward progress toward incident resolution.

## Symptoms
- `token_usage` reaches extreme levels (3000–5500+ tokens).
- `latency` surges past 10.0s–18.0s per workflow execution.
- `cpu_usage` rises above 85% due to continuous serialization and graph state transitions.
- Graph state history contains repeating sequences of identical tool actions (e.g. repeated `get_recent_logs` calls with identical timestamps).
- Execution eventually crashes with `RecursionError`, `GraphRecursionError`, or timeout.

## Root Cause
1. Tool returns uninformative output (e.g. empty string or generic error) without clear guidance on how the agent should adjust its strategy.
2. Missing stop condition or ambiguous state transition logic in LangGraph conditional edges.
3. Lack of execution step bounds allowing agents to loop indefinitely.

## Recommended Recovery
1. **Enforce Max Retries Bound**: Apply hard iteration limits (`MAX_RETRIES = 3`) on all cyclic agent graph edges (per Section 10).
2. **Interrupt for Human Review**: Route agent to human intervention state when circular tool patterns are detected (per Section 13).
3. **State History Deduction**: Inject a trajectory summarizer into the agent prompt warning the agent of repeated failures and forcing an alternative strategy.
