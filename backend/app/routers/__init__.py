"""API routers."""

from app.routers.auth import router as auth_router
from app.routers.config import router as config_router
from app.routers.coverage import router as coverage_router
from app.routers.health import router as health_router
from app.routers.messages import router as messages_router
from app.routers.metrics import router as metrics_router
from app.routers.sources import router as sources_router
from app.routers.ui import router as ui_router
from app.routers.users import router as users_router
from app.routers.utilization import router as utilization_router

__all__ = [
    "auth_router",
    "config_router",
    "coverage_router",
    "health_router",
    "messages_router",
    "metrics_router",
    "sources_router",
    "ui_router",
    "users_router",
    "utilization_router",
]
