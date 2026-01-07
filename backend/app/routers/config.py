"""Configuration export/import router."""

import json
import logging
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.auth.middleware import require_admin
from app.database import get_db
from app.models import Source
from app.models.source import SourceType
from app.models.settings import SystemSetting
from app.schemas.config import (
    AnalysisConfig,
    BoundsConfig,
    ConfigExport,
    ConfigImport,
    CoverageAnalysisConfig,
    DisplaySettingsConfig,
    ExportSourceConfig,
    ImportResult,
    SolarScheduleConfig,
    UtilizationAnalysisConfig,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/config", tags=["config"])

# Get app version
try:
    APP_VERSION = version("meshmanager")
except PackageNotFoundError:
    APP_VERSION = "0.0.0-dev"

# Settings keys
COVERAGE_CONFIG_KEY = "coverage_config"
UTILIZATION_CONFIG_KEY = "utilization_config"
SOLAR_SCHEDULE_KEY = "solar_analysis.schedule"


@router.get("/export")
async def export_config(
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
) -> Response:
    """Export all configuration to a downloadable JSON file."""
    # Query all sources
    result = await db.execute(select(Source))
    sources = result.scalars().all()

    # Convert sources to export format (exclude sensitive data)
    export_sources = []
    for source in sources:
        source_config = ExportSourceConfig(
            name=source.name,
            type=source.type.value,
            enabled=source.enabled,
            url=source.url,
            poll_interval_seconds=source.poll_interval_seconds,
            historical_days_back=source.historical_days_back,
            mqtt_host=source.mqtt_host,
            mqtt_port=source.mqtt_port,
            mqtt_topic_pattern=source.mqtt_topic_pattern,
            mqtt_use_tls=source.mqtt_use_tls,
        )
        export_sources.append(source_config)

    # Query analysis settings
    analysis = AnalysisConfig()

    # Coverage config
    coverage_result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == COVERAGE_CONFIG_KEY)
    )
    coverage_setting = coverage_result.scalar_one_or_none()
    if coverage_setting and coverage_setting.value:
        cv = coverage_setting.value
        bounds = None
        if any(cv.get(k) is not None for k in ["bounds_south", "bounds_west", "bounds_north", "bounds_east"]):
            bounds = BoundsConfig(
                south=cv.get("bounds_south"),
                west=cv.get("bounds_west"),
                north=cv.get("bounds_north"),
                east=cv.get("bounds_east"),
            )
        analysis.coverage_config = CoverageAnalysisConfig(
            enabled=cv.get("enabled", False),
            resolution=cv.get("resolution", 1.0),
            unit=cv.get("unit", "miles"),
            lookback_days=cv.get("lookback_days", 7),
            bounds=bounds,
        )

    # Utilization config
    util_result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == UTILIZATION_CONFIG_KEY)
    )
    util_setting = util_result.scalar_one_or_none()
    if util_setting and util_setting.value:
        uv = util_setting.value
        bounds = None
        if any(uv.get(k) is not None for k in ["bounds_south", "bounds_west", "bounds_north", "bounds_east"]):
            bounds = BoundsConfig(
                south=uv.get("bounds_south"),
                west=uv.get("bounds_west"),
                north=uv.get("bounds_north"),
                east=uv.get("bounds_east"),
            )
        analysis.utilization_config = UtilizationAnalysisConfig(
            enabled=uv.get("enabled", False),
            resolution=uv.get("resolution", 1.0),
            unit=uv.get("unit", "miles"),
            lookback_days=uv.get("lookback_days", 7),
            aggregation=uv.get("aggregation", "avg"),
            bounds=bounds,
        )

    # Solar schedule config
    solar_result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == SOLAR_SCHEDULE_KEY)
    )
    solar_setting = solar_result.scalar_one_or_none()
    if solar_setting and solar_setting.value:
        sv = solar_setting.value
        analysis.solar_schedule = SolarScheduleConfig(
            enabled=sv.get("enabled", False),
            schedules=sv.get("schedules", []),
            apprise_urls=sv.get("apprise_urls", []),
            lookback_days=sv.get("lookback_days", 7),
        )

    # Build export
    export_data = ConfigExport(
        version="1.0",
        exported_at=datetime.now(timezone.utc).isoformat(),
        meshmanager_version=APP_VERSION,
        sources=export_sources,
        display_settings=DisplaySettingsConfig(),  # Default values, frontend manages these
        analysis=analysis,
    )

    # Generate filename
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"meshmanager-config-{date_str}.json"

    # Return as downloadable JSON
    return Response(
        content=json.dumps(export_data.model_dump(), indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


@router.post("/import", response_model=ImportResult)
async def import_config(
    config: ConfigImport,
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
    merge_sources: bool = False,
) -> ImportResult:
    """Import configuration from JSON.

    Args:
        config: Configuration to import
        merge_sources: If True, keep existing sources and add new ones.
                      If False (default), delete all existing sources first.
    """
    warnings: list[str] = []
    sources_imported = 0
    sources_skipped = 0
    analysis_configs_imported: list[str] = []

    # Validate version
    if config.version != "1.0":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported config version: {config.version}. Expected: 1.0",
        )

    # Import sources
    if config.sources:
        if not merge_sources:
            # Delete all existing sources
            existing_result = await db.execute(select(Source))
            existing_sources = existing_result.scalars().all()
            for source in existing_sources:
                await db.delete(source)
            await db.flush()
            logger.info(f"Deleted {len(existing_sources)} existing sources")

        # Get existing source names for duplicate checking
        existing_names_result = await db.execute(select(Source.name))
        existing_names = {name for (name,) in existing_names_result.all()}

        for source_config in config.sources:
            # Skip duplicates in merge mode
            if merge_sources and source_config.name in existing_names:
                sources_skipped += 1
                warnings.append(f"Skipped duplicate source: {source_config.name}")
                continue

            # Create new source (without credentials)
            try:
                source_type = SourceType(source_config.type)
            except ValueError:
                sources_skipped += 1
                warnings.append(f"Invalid source type '{source_config.type}' for source: {source_config.name}")
                continue

            new_source = Source(
                id=str(uuid4()),
                name=source_config.name,
                type=source_type,
                enabled=False,  # Disabled by default since credentials are missing
                url=source_config.url,
                poll_interval_seconds=source_config.poll_interval_seconds or 300,
                historical_days_back=source_config.historical_days_back or 1,
                mqtt_host=source_config.mqtt_host,
                mqtt_port=source_config.mqtt_port or 1883,
                mqtt_topic_pattern=source_config.mqtt_topic_pattern,
                mqtt_use_tls=source_config.mqtt_use_tls or False,
                # Credentials left blank - user must re-enter
                api_token=None,
                mqtt_username=None,
                mqtt_password=None,
            )
            db.add(new_source)
            sources_imported += 1
            existing_names.add(source_config.name)

        if sources_imported > 0:
            warnings.append(
                f"Imported {sources_imported} source(s) in DISABLED state. "
                "Please edit each source to add credentials and enable."
            )

    # Import analysis configs
    if config.analysis:
        # Coverage config
        if config.analysis.coverage_config:
            cc = config.analysis.coverage_config
            coverage_value = {
                "enabled": cc.enabled,
                "resolution": cc.resolution,
                "unit": cc.unit,
                "lookback_days": cc.lookback_days,
            }
            if cc.bounds:
                coverage_value.update({
                    "bounds_south": cc.bounds.south,
                    "bounds_west": cc.bounds.west,
                    "bounds_north": cc.bounds.north,
                    "bounds_east": cc.bounds.east,
                })

            coverage_setting = await db.execute(
                select(SystemSetting).where(SystemSetting.key == COVERAGE_CONFIG_KEY)
            )
            existing = coverage_setting.scalar_one_or_none()
            if existing:
                existing.value = coverage_value
            else:
                db.add(SystemSetting(key=COVERAGE_CONFIG_KEY, value=coverage_value))
            analysis_configs_imported.append("coverage_config")

        # Utilization config
        if config.analysis.utilization_config:
            uc = config.analysis.utilization_config
            util_value = {
                "enabled": uc.enabled,
                "resolution": uc.resolution,
                "unit": uc.unit,
                "lookback_days": uc.lookback_days,
                "aggregation": uc.aggregation,
            }
            if uc.bounds:
                util_value.update({
                    "bounds_south": uc.bounds.south,
                    "bounds_west": uc.bounds.west,
                    "bounds_north": uc.bounds.north,
                    "bounds_east": uc.bounds.east,
                })

            util_setting = await db.execute(
                select(SystemSetting).where(SystemSetting.key == UTILIZATION_CONFIG_KEY)
            )
            existing = util_setting.scalar_one_or_none()
            if existing:
                existing.value = util_value
            else:
                db.add(SystemSetting(key=UTILIZATION_CONFIG_KEY, value=util_value))
            analysis_configs_imported.append("utilization_config")

        # Solar schedule config
        if config.analysis.solar_schedule:
            sc = config.analysis.solar_schedule
            solar_value = {
                "enabled": sc.enabled,
                "schedules": sc.schedules,
                "apprise_urls": sc.apprise_urls,
                "lookback_days": sc.lookback_days,
            }

            solar_setting = await db.execute(
                select(SystemSetting).where(SystemSetting.key == SOLAR_SCHEDULE_KEY)
            )
            existing = solar_setting.scalar_one_or_none()
            if existing:
                existing.value = solar_value
            else:
                db.add(SystemSetting(key=SOLAR_SCHEDULE_KEY, value=solar_value))
            analysis_configs_imported.append("solar_schedule")

    await db.commit()

    return ImportResult(
        success=True,
        sources_imported=sources_imported,
        sources_skipped=sources_skipped,
        display_settings_imported=config.display_settings is not None,
        analysis_configs_imported=analysis_configs_imported,
        warnings=warnings,
        display_settings=config.display_settings,
    )
