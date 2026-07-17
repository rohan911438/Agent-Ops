from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import get_settings
from app.jobs.tasks import run_stale_scan_sweep
from app.middleware import MaxBodySizeMiddleware, RateLimitMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # A scan's BackgroundTasks state lives only in the serving process's
    # memory, so a restart mid-scan leaves it stuck forever with no other
    # recovery path — see app/services/scan_service.py sweep_stale_scans and
    # docs/ASP-6262-Production-Readiness-Audit.md finding M-3.
    await run_stale_scan_sweep()
    yield


app = FastAPI(
    title="AgentOps Cloud API",
    description="The enterprise control plane for AI agents.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Order matters: the last-added middleware runs first. Body-size rejection
# should happen before a doomed-anyway request also consumes a rate-limit
# slot, so RateLimit is added first (runs second) and MaxBodySize last
# (runs first).
app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.rate_limit_max_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
app.add_middleware(MaxBodySizeMiddleware)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
