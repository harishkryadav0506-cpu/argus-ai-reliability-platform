# Runbook: End-to-End Latency Spike and Queue Backlog

- **Failure Type**: `LATENCY_SPIKE`
- **Severity**: High
- **Reference Incident / Source**: Engineering Blog Post "FastAPI Async Event Loop Starvation from Synchronous LLM Calls"; Production Post-Mortem "P99 Latency Surge from Unbounded Concurrency"

## Incident Description
End-to-end request latency surges far beyond SLA thresholds. User requests stall, thread pools become saturated, and request queue depth grows monotonically, threatening systemic deadlock.

## Symptoms
- `latency` surges past 5.0s–12.0s (healthy SLA threshold: <= 2.0s).
- `cpu_usage` rises above 75% due to task queue context switching and backlog polling.
- Client requests begin encountering client-side read timeouts.
- Error rate remains initially low until queues overflow and 504 timeouts cascade.

## Root Cause
1. Synchronous I/O or blocking operations executed on the main asynchronous event loop, stalling all concurrent coroutines.
2. Sudden surge in time-to-first-token (TTFT) from LLM provider under high infrastructure load.
3. Unindexed relational database queries blocking connection pools during incident audit logging.

## Recommended Recovery
1. **Concurrency Throttling**: Apply rate limiting and request queue caps to reject excess traffic cleanly before latency degrades global availability.
2. **Offload Blocking Work**: Ensure all CPU-intensive and synchronous I/O operations are run within `asyncio.to_thread()` or dedicated worker pools.
3. **Switch to Streaming Responses**: Stream tokens to clients to minimize perceived latency and prevent memory buffering.
