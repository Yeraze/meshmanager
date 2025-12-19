"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.database import close_db, init_db
from app.routers import (
    auth_router,
    coverage_router,
    health_router,
    messages_router,
    metrics_router,
    sources_router,
    ui_router,
    utilization_router,
)
from app.services.collector_manager import collector_manager
from app.services.retention import retention_service
from app.services.scheduler import scheduler_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting MeshManager...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Start collectors
    await collector_manager.start()
    logger.info("Collectors started")

    # Start retention service
    await retention_service.start()
    logger.info("Retention service started")

    # Start solar analysis scheduler
    await scheduler_service.start()
    logger.info("Solar analysis scheduler started")

    yield

    # Shutdown
    logger.info("Shutting down MeshManager...")

    # Stop services
    await scheduler_service.stop()
    await retention_service.stop()
    await collector_manager.stop()
    await close_db()

    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="MeshManager",
    description="Management and oversight application for MeshMonitor and Meshtastic MQTT",
    version="0.1.0",
    lifespan=lifespan,
)

# Add session middleware (required for OIDC)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    max_age=86400,  # 24 hours
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(auth_router)
app.include_router(sources_router)
app.include_router(ui_router)
app.include_router(coverage_router)
app.include_router(utilization_router)
app.include_router(messages_router)


@app.get("/")
async def root():
    """Root endpoint - redirects to frontend or shows API info."""
    return {
        "name": "MeshManager",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }
