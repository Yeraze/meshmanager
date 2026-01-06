"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import FileResponse

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


# Static files directory (for unified Docker image)
STATIC_DIR = Path(__file__).parent.parent / "static"


# Mount static files if the directory exists (unified Docker image)
if STATIC_DIR.exists():
    # Serve static assets (JS, CSS, images, etc.)
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    # IMPORTANT: This catch-all route must be registered AFTER all API routers
    # to ensure API routes (e.g., /health, /api/*) take priority over SPA routing
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SPA frontend - returns index.html for all non-API routes."""
        # Try to serve the exact file first (for files like favicon.ico)
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        # Otherwise return index.html for SPA routing
        return FileResponse(STATIC_DIR / "index.html")
else:
    # Fallback when running without frontend (development/API-only mode)
    @app.get("/")
    async def root():
        """Root endpoint - shows API info when no frontend is bundled."""
        return {
            "name": "MeshManager",
            "version": "0.4.0",
            "docs": "/docs",
            "health": "/health",
            "metrics": "/metrics",
        }
