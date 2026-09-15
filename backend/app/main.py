"""
ARGUS Backend Entrypoint — Phase 1

Scope for this phase (per docs/ARGUS_SPEC.md Section 33):
  - app boots
  - configuration loads with graceful defaults
  - database session + models exist
  - /health reports per-integration status without crashing

Later phases add: simulation engine, ML detection, RAG, LangGraph agents,
MCP tools, human approval, LangSmith, frontend integration, and hardening.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging_config import configure_logging
from app.api.routes import health, simulation, metrics, incidents, evaluation
from app.services.simulation_service import simulation_engine
from app.middleware.rate_limit import RateLimitMiddleware

settings = get_settings()
configure_logging(settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create database tables on boot if reachable
    try:
        from app.database.models import Base
        from app.database.session import engine
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Could not auto-create database tables on startup: %s", e)

    # Start background metric simulation
    simulation_engine.start_background_task(interval=2.0)
    yield
    # Gracefully stop background task on shutdown
    simulation_engine.stop_background_task()


app = FastAPI(
    title=settings.APP_NAME,
    description="Autonomous AI Reliability & Recovery Platform",
    version="0.1.0",
    lifespan=lifespan,
)

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware, requests_per_minute=240)

app.include_router(health.router, tags=["health"])
app.include_router(simulation.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(incidents.router, prefix="/api")
app.include_router(evaluation.router, prefix="/api")


@app.get("/")
def root():
    return {"app": settings.APP_NAME, "status": "running", "environment": settings.ARGUS_ENV}

