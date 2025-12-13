"""Scheduler service for scheduled solar analysis notifications."""

import asyncio
import logging
from datetime import datetime

import httpx
from sqlalchemy import select

from app.database import async_session_maker
from app.models import SystemSetting
from app.services.notifications import notification_service

logger = logging.getLogger(__name__)

SETTINGS_KEY = "solar_analysis.schedule"


class SchedulerService:
    """Background service for scheduled solar analysis notifications."""

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_run_minute: str | None = None  # Track last run to avoid duplicates

    async def start(self) -> None:
        """Start the scheduler service."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._schedule_loop())
        logger.info("Started solar analysis scheduler service")

    async def stop(self) -> None:
        """Stop the scheduler service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped solar analysis scheduler service")

    async def get_settings(self) -> dict | None:
        """Get scheduler settings from database."""
        async with async_session_maker() as db:
            result = await db.execute(
                select(SystemSetting).where(SystemSetting.key == SETTINGS_KEY)
            )
            setting = result.scalar_one_or_none()
            return setting.value if setting else None

    async def _schedule_loop(self) -> None:
        """Main loop - check every minute if analysis should run."""
        while self._running:
            try:
                settings = await self.get_settings()
                if settings and settings.get("enabled"):
                    current_time = datetime.now().strftime("%H:%M")
                    schedules = settings.get("schedules", [])

                    # Check if current time matches any schedule and we haven't run this minute
                    if current_time in schedules and self._last_run_minute != current_time:
                        self._last_run_minute = current_time
                        logger.info(f"Scheduled solar analysis triggered at {current_time}")
                        await self._run_analysis(settings)
                    elif current_time not in schedules:
                        # Reset last run when we're not on a scheduled minute
                        self._last_run_minute = None
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")

            await asyncio.sleep(30)  # Check every 30 seconds for better accuracy

    async def _run_analysis(self, settings: dict) -> None:
        """Run solar analysis and send notifications."""
        lookback_days = settings.get("lookback_days", 7)
        urls = settings.get("apprise_urls", [])

        if not urls:
            logger.warning("No Apprise URLs configured, skipping notification")
            return

        try:
            # Fetch analysis from internal API endpoints
            # Use localhost:8000 since we're inside the same container as uvicorn
            base_url = "http://localhost:8000"
            async with httpx.AsyncClient() as client:
                # Get solar nodes analysis
                analysis_resp = await client.get(
                    f"{base_url}/api/analysis/solar-nodes",
                    params={"lookback_days": lookback_days},
                    timeout=60.0,
                )
                analysis_resp.raise_for_status()
                analysis = analysis_resp.json()

                # Get forecast analysis
                forecast_resp = await client.get(
                    f"{base_url}/api/analysis/solar-forecast",
                    params={"lookback_days": lookback_days},
                    timeout=60.0,
                )
                forecast_resp.raise_for_status()
                forecast = forecast_resp.json()

            # Format and send notification
            title, body = notification_service.format_solar_summary(analysis, forecast)
            result = await notification_service.send(urls, title, body)

            if result["success"]:
                logger.info(f"Scheduled solar analysis notification sent to {len(urls)} URLs")
            else:
                logger.error(f"Failed to send notification: {result.get('error')}")

        except httpx.RequestError as e:
            logger.error(f"Failed to fetch analysis data: {e}")
        except Exception as e:
            logger.error(f"Failed to run scheduled analysis: {e}")

    async def run_test_notification(self, settings: dict) -> dict:
        """Run a test notification with current settings.

        Returns dict with success status and any error message.
        """
        lookback_days = settings.get("lookback_days", 7)
        urls = settings.get("apprise_urls", [])

        if not urls:
            return {"success": False, "error": "No Apprise URLs configured"}

        try:
            # Use localhost:8000 since we're inside the same container as uvicorn
            base_url = "http://localhost:8000"
            async with httpx.AsyncClient() as client:
                # Get solar nodes analysis
                analysis_resp = await client.get(
                    f"{base_url}/api/analysis/solar-nodes",
                    params={"lookback_days": lookback_days},
                    timeout=60.0,
                )
                analysis_resp.raise_for_status()
                analysis = analysis_resp.json()

                # Get forecast analysis
                forecast_resp = await client.get(
                    f"{base_url}/api/analysis/solar-forecast",
                    params={"lookback_days": lookback_days},
                    timeout=60.0,
                )
                forecast_resp.raise_for_status()
                forecast = forecast_resp.json()

            # Format and send notification
            title, body = notification_service.format_solar_summary(analysis, forecast)
            result = await notification_service.send(urls, title, body)

            return result

        except httpx.RequestError as e:
            return {"success": False, "error": f"Failed to fetch analysis: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global scheduler service instance
scheduler_service = SchedulerService()
