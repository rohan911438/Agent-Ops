"""Cross-cutting ASGI middleware: a global request-size cap and a basic
per-client rate limit. Neither existed before — see
docs/ASP-6262-Production-Readiness-Audit.md findings H-2 and M-5.

Both are deliberately simple, dependency-free, in-process implementations
that match the rest of the MVP's "no Redis/broker yet" posture (see
docs/TechnicalDecisions.md) rather than pulling in a library or an external
store. That means neither coordinates across multiple worker processes or
replicas and both reset on restart — acceptable for a single-process
deployment, and a named limitation to revisit once Phase 3's real
scheduler/broker lands, not an oversight.
"""

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """A hard cap on request body size across every route — previously only
    POST /scans/upload enforced its own limit (2MB, see api/v1/scans.py);
    every other route had none. Checked via the Content-Length header
    up front, which every JSON/form client sends; this is a fast-fail for
    the common case, not a substitute for a reverse proxy's own limits in
    front of a real deployment.
    """

    def __init__(self, app, max_bytes: int = 5 * 1024 * 1024):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                too_large = int(content_length) > self.max_bytes
            except ValueError:
                too_large = False
            if too_large:
                return JSONResponse(
                    {"detail": f"Request body exceeds the {self.max_bytes // (1024 * 1024)}MB limit."},
                    status_code=413,
                )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window rate limit per client (X-Forwarded-For if present,
    otherwise the connecting IP). Applies ahead of authentication, so it
    protects unauthenticated routes (e.g. /auth/wallet/nonce) too, not just
    org-scoped ones.
    """

    def __init__(self, app, max_requests: int = 120, window_seconds: float = 60.0):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    @staticmethod
    def _client_key(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/healthz", "/health"):
            return await call_next(request)

        key = self._client_key(request)
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()

        if len(hits) >= self.max_requests:
            return JSONResponse(
                {"detail": "Too many requests. Please slow down and try again shortly."},
                status_code=429,
            )

        hits.append(now)
        return await call_next(request)
