"""Source management endpoints (admin only)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import require_admin
from app.database import get_db
from app.models import Source
from app.models.source import SourceType
from app.schemas.source import (
    MeshMonitorSourceCreate,
    MeshMonitorSourceUpdate,
    MqttSourceCreate,
    MqttSourceUpdate,
    SourceResponse,
    SourceTestResult,
)
from app.services.collector_manager import collector_manager

router = APIRouter(prefix="/api/admin/sources", tags=["sources"])


@router.get("", response_model=list[SourceResponse])
async def list_sources(
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
) -> list[SourceResponse]:
    """List all configured sources."""
    result = await db.execute(select(Source).order_by(Source.name))
    sources = result.scalars().all()
    return [SourceResponse.model_validate(s) for s in sources]


@router.post("/meshmonitor", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_meshmonitor_source(
    source_data: MeshMonitorSourceCreate,
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
) -> SourceResponse:
    """Create a new MeshMonitor source."""
    source = Source(
        name=source_data.name,
        type=SourceType.MESHMONITOR,
        url=source_data.url,
        api_token=source_data.api_token,
        poll_interval_seconds=source_data.poll_interval_seconds,
        historical_days_back=source_data.historical_days_back,
        enabled=source_data.enabled,
    )
    db.add(source)
    await db.flush()
    await db.refresh(source)

    # Start collector for the new source
    await collector_manager.add_source(source)

    return SourceResponse.model_validate(source)


@router.post("/mqtt", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_mqtt_source(
    source_data: MqttSourceCreate,
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
) -> SourceResponse:
    """Create a new MQTT source."""
    source = Source(
        name=source_data.name,
        type=SourceType.MQTT,
        mqtt_host=source_data.mqtt_host,
        mqtt_port=source_data.mqtt_port,
        mqtt_username=source_data.mqtt_username,
        mqtt_password=source_data.mqtt_password,
        mqtt_topic_pattern=source_data.mqtt_topic_pattern,
        mqtt_use_tls=source_data.mqtt_use_tls,
        enabled=source_data.enabled,
    )
    db.add(source)
    await db.flush()
    await db.refresh(source)

    # Start collector for the new source
    await collector_manager.add_source(source)

    return SourceResponse.model_validate(source)


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
) -> SourceResponse:
    """Get a specific source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return SourceResponse.model_validate(source)


@router.put("/meshmonitor/{source_id}", response_model=SourceResponse)
async def update_meshmonitor_source(
    source_id: str,
    source_data: MeshMonitorSourceUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
) -> SourceResponse:
    """Update a MeshMonitor source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.type != SourceType.MESHMONITOR:
        raise HTTPException(status_code=400, detail="Source is not a MeshMonitor source")

    update_data = source_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)

    await db.flush()
    await db.refresh(source)

    # Update collector with new config
    await collector_manager.update_source(source)

    return SourceResponse.model_validate(source)


@router.put("/mqtt/{source_id}", response_model=SourceResponse)
async def update_mqtt_source(
    source_id: str,
    source_data: MqttSourceUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
) -> SourceResponse:
    """Update an MQTT source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.type != SourceType.MQTT:
        raise HTTPException(status_code=400, detail="Source is not an MQTT source")

    update_data = source_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)

    await db.flush()
    await db.refresh(source)

    # Update collector with new config
    await collector_manager.update_source(source)

    return SourceResponse.model_validate(source)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
) -> None:
    """Delete a source and all its data."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Stop the collector first
    await collector_manager.remove_source(source_id)

    await db.delete(source)


@router.post("/{source_id}/test", response_model=SourceTestResult)
async def test_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
) -> SourceTestResult:
    """Test a source connection."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    if source.type == SourceType.MESHMONITOR:
        from app.collectors.meshmonitor import MeshMonitorCollector

        collector = MeshMonitorCollector(source)
        return await collector.test_connection()
    else:
        from app.collectors.mqtt import MqttCollector

        collector = MqttCollector(source)
        return await collector.test_connection()


@router.post("/{source_id}/sync")
async def sync_source_data(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
) -> dict:
    """Trigger full data sync for a source, skipping duplicates."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    if source.type != SourceType.MESHMONITOR:
        raise HTTPException(status_code=400, detail="Sync only supported for MeshMonitor sources")

    success = await collector_manager.trigger_sync(source_id)
    if success:
        return {"message": "Sync started", "source_id": source_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to start sync")


@router.post("/{source_id}/collect-history")
async def collect_historical_data(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
) -> dict:
    """Trigger historical data collection for a source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    if source.type != SourceType.MESHMONITOR:
        raise HTTPException(status_code=400, detail="Historical collection only supported for MeshMonitor sources")

    success = await collector_manager.trigger_historical_collection(source_id)
    if success:
        return {"message": "Historical collection started", "source_id": source_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to start historical collection")


@router.post("/collect-history-all")
async def collect_historical_data_all(
    _admin: None = Depends(require_admin),
) -> dict:
    """Trigger historical data collection for all MeshMonitor sources."""
    count = await collector_manager.trigger_historical_collection_all()
    return {"message": f"Historical collection started for {count} sources"}


@router.post("/{source_id}/collect-node-history")
async def collect_per_node_historical_data(
    source_id: str,
    days_back: int = 7,
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
) -> dict:
    """Trigger per-node historical telemetry collection for a source.

    Uses the new MeshMonitor per-node API (if available) to fetch historical
    telemetry for all nodes from this source.

    Args:
        source_id: The source ID
        days_back: Number of days of history to fetch (default 7)
    """
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    if source.type != SourceType.MESHMONITOR:
        raise HTTPException(
            status_code=400,
            detail="Per-node historical collection only supported for MeshMonitor sources",
        )

    success = await collector_manager.trigger_per_node_historical_collection(
        source_id, days_back=days_back
    )
    if success:
        return {
            "message": f"Per-node historical collection started ({days_back} days)",
            "source_id": source_id,
        }
    else:
        raise HTTPException(
            status_code=500, detail="Failed to start per-node historical collection"
        )


@router.post("/collect-node-history-all")
async def collect_per_node_historical_data_all(
    days_back: int = 7,
    _admin: None = Depends(require_admin),
) -> dict:
    """Trigger per-node historical telemetry collection for all MeshMonitor sources.

    Uses the new MeshMonitor per-node API to fetch historical telemetry.
    """
    count = await collector_manager.trigger_per_node_historical_collection_all(
        days_back=days_back
    )
    return {
        "message": f"Per-node historical collection started for {count} sources ({days_back} days)",
    }
