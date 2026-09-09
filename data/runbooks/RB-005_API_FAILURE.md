# Runbook: Upstream HTTP/API Gateway Outage and 5xx Cascades

- **Failure Type**: `API_FAILURE`
- **Severity**: Critical
- **Reference Incident / Source**: Google Cloud Vertex AI Incident "503 Service Unavailable Under Peak Load" (Dec 2024); Cloudflare Status Incident "Edge Gateway 502/504 Bad Gateway Propagation"

## Incident Description
External network, proxy, or edge API gateways return 502 Bad Gateway, 503 Service Unavailable, or 504 Gateway Timeout. Unlike `LLM_FAILURE` (which involves model inference or schema parsing bugs), `API_FAILURE` stems from transport-level network partition or upstream gateway unavailability.

## Symptoms
- `api_success_rate` drops sharply below 0.75 (healthy: >= 0.995).
- HTTP client logs show `HTTPStatusError: 502 Bad Gateway`, `503 Service Unavailable`, or `ConnectTimeout`.
- Internal application and database metrics remain completely healthy (low memory, normal CPU).
- All requests attempting external network communication fail at the network boundary.

## Root Cause
1. Upstream cloud provider regional network outage or DNS resolution failure.
2. HTTP client connection pool exhaustion caused by unclosed keep-alive connections.
3. Edge rate limiting or IP throttling returning 429/503 HTML challenge pages instead of JSON payloads.

## Recommended Recovery
1. **Exponential Backoff & Jitter**: Ensure client requests utilize randomized exponential backoff with jitter to avoid thundering herd problem on gateway recovery.
2. **Switch Gateway / Region**: Route requests to an alternate cloud region or secondary backup API endpoint (e.g. switch API endpoint from us-central1 to us-east4).
3. **Graceful Degradation**: Activate local rule-based diagnostic mode per Section 32, bypassing external API calls while logging status.
