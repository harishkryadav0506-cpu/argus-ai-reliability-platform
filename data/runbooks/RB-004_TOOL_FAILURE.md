# Runbook: External MCP Tool Execution and Schema Failure

- **Failure Type**: `TOOL_FAILURE`
- **Severity**: High
- **Reference Incident / Source**: LangChain Issue #9812 "Tool Execution ValidationError on Type Coercion"; MCP Protocol Case Study "Tool Execution Failures from Upstream Schema Drift"

## Incident Description
Specialized agent tool executions (metrics fetching, log analysis, deployment inspection) fail consistently. Tools return error payloads, throw validation exceptions, or time out when communicating with integrated microservices.

## Symptoms
- `tool_failure_rate` surges above 0.20 (20% to 65% failure rate).
- Application logs report `ToolException`, `ValidationError`, `ConnectionTimeout`, or `ToolExecutionError`.
- Agent attempts repeated retries of the same tool call with slight parameter variations.
- `error_rate` climbs above 0.15 as downstream agent nodes fail to receive required tool outputs.

## Root Cause
1. Schema mismatch between tool declaration and LLM arguments (e.g. LLM passing string `"60"` instead of integer `60`).
2. Target microservice endpoint down or unreachable due to network partition or invalid auth credentials.
3. Unhandled exceptions inside tool implementation when processing null or malformed upstream payloads.

## Recommended Recovery
1. **Input Type Coercion & Validation**: Apply strict Pydantic parsing and automatic type casting in tool wrappers prior to tool execution.
2. **Circuit Breaker**: Trip the circuit breaker for failing action tools; return structured fallback diagnostics to the calling agent to prevent cascading retry loops.
3. **Restart Tool Integration**: Call `restart_service(service_name="mcp_server")` or reload tool client connection pools.
