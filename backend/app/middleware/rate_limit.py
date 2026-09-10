"""
ARGUS Rate-Limiting Middleware (Section 21)

Implements an in-memory sliding-window rate limiter per client IP address.
Protects AI inference and simulation endpoints from runaway query traffic and DoS.
"""
import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        requests_per_minute: int = 180,
        burst_limit: int = 240,
    ):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.burst_limit = burst_limit
        # Client IP -> list of timestamps
        self.request_history: Dict[str, List[float]] = defaultdict(list)
        # Paths exempt from rate limits (liveness probes, health checks)
        self.exempt_paths = {"/", "/health", "/docs", "/openapi.json"}

    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Exempt health checks & root probes
        path = request.url.path
        if path in self.exempt_paths:
            return await call_next(request)

        # 2. Extract client IP (respecting X-Forwarded-For if behind a reverse proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "127.0.0.1"

        now = time.time()
        window_start = now - 60.0

        # 3. Clean up timestamps older than 60s
        history = [t for t in self.request_history[client_ip] if t > window_start]
        self.request_history[client_ip] = history

        # 4. Check if request count exceeds limit
        if len(history) >= self.rpm:
            retry_after = int(60.0 - (now - history[0])) if history else 60
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": "Too Many Requests. Rate limit exceeded.",
                    "limit": self.rpm,
                    "window": "60s",
                    "retry_after_seconds": max(retry_after, 1),
                },
                headers={
                    "X-RateLimit-Limit": str(self.rpm),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + max(retry_after, 1))),
                    "Retry-After": str(max(retry_after, 1)),
                },
            )
            return response

        # 5. Record request timestamp
        self.request_history[client_ip].append(now)
        remaining = max(0, self.rpm - len(self.request_history[client_ip]))

        # 6. Execute request
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.rpm)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + 60))

        return response
