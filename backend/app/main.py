"""
DevInsight AI — FastAPI application entry point.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.base import create_tables
from app.ml.anomaly_detector import get_detector, build_demo_training_data

setup_logging()
logger = logging.getLogger("devinsight")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("DevInsight AI starting up...")
    logger.info("Monitoring mode: %s", settings.MONITORING_MODE)
    logger.info("GitHub configured: %s", settings.github_configured)
    logger.info("Gemini available: %s", settings.gemini_available)
    logger.info("ShopSphere metrics URL: %s", settings.SHOPSPHERE_METRICS_URL)

    try:
        await create_tables()
        logger.info("Database tables ready")
    except Exception as e:
        logger.error("Failed to create database tables: %s", e)

    try:
        from app.db.base import AsyncSessionLocal
        from app.services.demo_seeder import seed_demo_data
        async with AsyncSessionLocal() as db:
            await seed_demo_data(db)
        logger.info("Demo data seeded")
    except Exception as e:
        logger.error("Failed to seed demo data: %s", e)

    try:
        detector = get_detector()
        if not detector.is_trained:
            samples = build_demo_training_data(500)
            result = detector.train(samples)
            logger.info("Anomaly detector trained: %s", result)
    except Exception as e:
        logger.error("Failed to train anomaly detector: %s", e)

    # Start ShopSphere metrics poller
    poller_task = None
    try:
        from app.services.shopsphere_poller import run_poller
        poller_task = asyncio.create_task(run_poller())
        logger.info("ShopSphere poller started — target: %s", settings.SHOPSPHERE_METRICS_URL)
    except Exception as e:
        logger.error("Failed to start ShopSphere poller: %s", e)

    logger.info("DevInsight AI ready — visit http://localhost:8000/docs")
    yield

    # Shutdown: cancel poller
    if poller_task and not poller_task.done():
        poller_task.cancel()
        try:
            await poller_task
        except asyncio.CancelledError:
            pass
    logger.info("DevInsight AI shutting down")


app = FastAPI(
    title="DevInsight AI",
    description="AI-powered AIOps and Self-Healing DevOps Platform",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Existing routers ──────────────────────────────────────────────────────────
from app.api.health import router as health_router
from app.api.dashboard import router as dashboard_router
from app.api.incidents import router as incidents_router
from app.api.metrics import router as metrics_router
from app.api.logs import router as logs_router
from app.api.traces import router as traces_router
from app.api.services_api import router as services_router
from app.api.anomaly import router as anomaly_router
from app.api.rca import router as rca_router
from app.api.demo import router as demo_router
from app.api.ai_assistant import router as ai_router

# ── New routers ───────────────────────────────────────────────────────────────
from app.api.github_api import router as github_router
from app.api.remediation import router as remediation_router
from app.api.webhook import router as webhook_router
from app.api.deployments import router as deployments_router
from app.api.integrations import router as integrations_router
from app.api.ingest import router as ingest_router

app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(incidents_router)
app.include_router(metrics_router)
app.include_router(logs_router)
app.include_router(traces_router)
app.include_router(services_router)
app.include_router(anomaly_router)
app.include_router(rca_router)
app.include_router(demo_router)
app.include_router(ai_router)
app.include_router(github_router)
app.include_router(remediation_router)
app.include_router(webhook_router)
app.include_router(deployments_router)
app.include_router(integrations_router)
app.include_router(ingest_router)


@app.get("/")
async def root():
    return {
        "name": "DevInsight AI",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
        "monitoring_mode": settings.MONITORING_MODE,
        "github_configured": settings.github_configured,
        "gemini_available": settings.gemini_available,
        "shopsphere_metrics_url": settings.SHOPSPHERE_METRICS_URL,
    }
