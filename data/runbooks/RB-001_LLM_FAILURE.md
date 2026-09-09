# Runbook: LLM Provider Failure and Schema Decoding Error

- **Failure Type**: `LLM_FAILURE`
- **Severity**: Critical
- **Reference Incident / Source**: OpenAI Incident Report "Elevated API Error Rates and Context Window Truncation" (March 2024); LangChain Issue #11234 "Structured Output JSONDecodeError on Model Timeout"

## Incident Description
The primary language model API endpoint fails to return valid responses, returns 5xx status codes, exceeds inference timeouts, or yields malformed/truncated output tokens that fail structured Pydantic schema validation.

## Symptoms
- `error_rate` spikes above 0.15 (15% to 45% failure rate).
- `api_success_rate` drops sharply below 0.80.
- Application raises `JSONDecodeError` or `OutputParserException` during agent decision steps.
- Latency percentiles (P95/P99) rise to 5.0s–8.0s due to HTTP retry timeouts.

## Root Cause
1. Upstream LLM provider infrastructure outage or regional capacity degradation.
2. Context window saturation causing the model to abruptly truncate structured JSON output mid-bracket.
3. Model deprecation or sudden internal safety filtering suppressing generated tokens without structured response.

## Recommended Recovery
1. **Model Fallback**: Switch active LLM provider from primary to secondary fallback (e.g. switch `gemini-2.0-flash` to backup provider/deployment via `switch_model` action tool).
2. **Context Window Pruning**: Enable aggressive context window summarization to keep input tokens comfortably below maximum context limits.
3. **Structured Parser Recovery**: Catch `OutputParserException` and apply fallback regex extractor or rule-based default diagnostic schema before failing downstream agents.
