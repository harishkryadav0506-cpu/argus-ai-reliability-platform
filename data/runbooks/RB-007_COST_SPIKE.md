# Runbook: Runaway Token Consumption and Cost Surge

- **Failure Type**: `COST_SPIKE`
- **Severity**: Medium
- **Reference Incident / Source**: Anthropic Developer Forum "Runaway Token Consumption in Recursive Chain Prompts"; AI FinOps Report "Uncapped Context Growth and Multi-Turn Cost Explosions"

## Incident Description
Token consumption per request or per minute escalates dramatically (+200% to +400% above baseline). Cost burn rate exceeds operational budgets, risking rapid API quota exhaustion and sudden account suspension.

## Symptoms
- `token_usage` surges above 2200–4000 tokens per request (baseline: ~520 tokens).
- `request_volume` or cumulative token metrics climb continuously without proportional increase in user traffic.
- API cost telemetry shows an exponential cost trajectory.
- Output text from models becomes excessively verbose, repetitive, or includes full raw document dumps.

## Root Cause
1. Multi-turn chat context accumulating prior turns indefinitely without sliding window trimming or token budgeting.
2. Prompts requesting full document regurgitation or excessive reasoning chains without `max_tokens` boundaries.
3. System prompt duplication inside nested agent tool calls.

## Recommended Recovery
1. **Enforce Hard Token Caps**: Set strict `max_output_tokens` limits (e.g. 1024 tokens) on all agent inference requests.
2. **Context Compression**: Implement semantic sliding window compression, retaining only the system prompt, retrieved runbook snippets, and last 2 conversational turns.
3. **Enable Prompt Caching**: Utilize Gemini/Anthropic prompt caching for invariant system prompts and static tool declarations.
