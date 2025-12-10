"""Utilization map API endpoints."""

import math
from datetime import UTC, datetime, timedelta
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.database import get_db
from app.models import Node, SystemSetting, Telemetry, UtilizationCell

router = APIRouter(prefix="/api/utilization", tags=["utilization"])

# Constants for coordinate conversion
KM_PER_DEGREE_LAT = 111.0
MILES_TO_KM = 1.60934

UTILIZATION_CONFIG_KEY = "utilization_config"


class AggregationType(str, Enum):
    """Aggregation method for utilization values."""

    MIN = "min"
    MAX = "max"
    AVG = "avg"


# Color scale for utilization heatmap (0-100%)
# Green (low) -> Yellow (medium) -> Red (high)
def get_color_for_utilization(value: float) -> str:
    """Get heatmap color for utilization value (0-100%)."""
    if value < 0:
        return "transparent"
    if value <= 10:
        return "rgba(0, 128, 0, 0.5)"  # Green
    if value <= 25:
        return "rgba(50, 205, 50, 0.5)"  # Lime Green
    if value <= 40:
        return "rgba(154, 205, 50, 0.5)"  # Yellow-Green
    if value <= 55:
        return "rgba(255, 255, 0, 0.5)"  # Yellow
    if value <= 70:
        return "rgba(255, 165, 0, 0.6)"  # Orange
    if value <= 85:
        return "rgba(255, 69, 0, 0.6)"  # Red-Orange
    return "rgba(255, 0, 0, 0.7)"  # Red


class UtilizationConfigRequest(BaseModel):
    """Request schema for utilization configuration."""

    enabled: bool = False
    resolution: float = 1.0  # in miles or km
    unit: str = "miles"  # "miles" or "kilometers"
    lookback_days: int = 7
    aggregation: AggregationType = AggregationType.AVG
    # Map bounds (set by panning/zooming)
    bounds_south: float | None = None
    bounds_west: float | None = None
    bounds_north: float | None = None
    bounds_east: float | None = None


class UtilizationConfigResponse(BaseModel):
    """Response schema for utilization configuration."""

    enabled: bool
    resolution: float
    unit: str
    lookback_days: int
    aggregation: str
    bounds_south: float | None
    bounds_west: float | None
    bounds_north: float | None
    bounds_east: float | None
    last_generated: str | None
    cell_count: int


class UtilizationCellResponse(BaseModel):
    """Response schema for a utilization cell."""

    south: float
    west: float
    north: float
    east: float
    value: float
    color: str


class GenerateResponse(BaseModel):
    """Response schema for generate action."""

    success: bool
    cell_count: int
    message: str


@router.get("/config", response_model=UtilizationConfigResponse)
async def get_utilization_config(
    db: AsyncSession = Depends(get_db),
) -> UtilizationConfigResponse:
    """Get current utilization map configuration."""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == UTILIZATION_CONFIG_KEY)
    )
    setting = result.scalar()

    # Count existing cells
    count_result = await db.execute(select(UtilizationCell.id))
    cell_count = len(count_result.all())

    if not setting:
        return UtilizationConfigResponse(
            enabled=False,
            resolution=1.0,
            unit="miles",
            lookback_days=7,
            aggregation="avg",
            bounds_south=None,
            bounds_west=None,
            bounds_north=None,
            bounds_east=None,
            last_generated=None,
            cell_count=cell_count,
        )

    value = setting.value
    return UtilizationConfigResponse(
        enabled=value.get("enabled", False),
        resolution=value.get("resolution", 1.0),
        unit=value.get("unit", "miles"),
        lookback_days=value.get("lookback_days", 7),
        aggregation=value.get("aggregation", "avg"),
        bounds_south=value.get("bounds_south"),
        bounds_west=value.get("bounds_west"),
        bounds_north=value.get("bounds_north"),
        bounds_east=value.get("bounds_east"),
        last_generated=value.get("last_generated"),
        cell_count=cell_count,
    )


@router.put("/config", response_model=UtilizationConfigResponse)
async def update_utilization_config(
    config: UtilizationConfigRequest,
    db: AsyncSession = Depends(get_db),
) -> UtilizationConfigResponse:
    """Update utilization map configuration."""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == UTILIZATION_CONFIG_KEY)
    )
    setting = result.scalar()

    value = {
        "enabled": config.enabled,
        "resolution": config.resolution,
        "unit": config.unit,
        "lookback_days": config.lookback_days,
        "aggregation": config.aggregation.value,
        "bounds_south": config.bounds_south,
        "bounds_west": config.bounds_west,
        "bounds_north": config.bounds_north,
        "bounds_east": config.bounds_east,
    }

    if setting:
        # Preserve last_generated
        value["last_generated"] = setting.value.get("last_generated")
        setting.value = value
    else:
        setting = SystemSetting(key=UTILIZATION_CONFIG_KEY, value=value)
        db.add(setting)

    await db.commit()

    # Count cells
    count_result = await db.execute(select(UtilizationCell.id))
    cell_count = len(count_result.all())

    return UtilizationConfigResponse(
        enabled=value.get("enabled", False),
        resolution=value.get("resolution", 1.0),
        unit=value.get("unit", "miles"),
        lookback_days=value.get("lookback_days", 7),
        aggregation=value.get("aggregation", "avg"),
        bounds_south=value.get("bounds_south"),
        bounds_west=value.get("bounds_west"),
        bounds_north=value.get("bounds_north"),
        bounds_east=value.get("bounds_east"),
        last_generated=value.get("last_generated"),
        cell_count=cell_count,
    )


@router.post("/generate", response_model=GenerateResponse)
async def generate_utilization(db: AsyncSession = Depends(get_db)) -> GenerateResponse:
    """Generate utilization grid from channel utilization telemetry."""
    # Get config
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == UTILIZATION_CONFIG_KEY)
    )
    setting = result.scalar()

    if not setting:
        raise HTTPException(status_code=400, detail="Utilization not configured")

    config = setting.value
    lookback_days = config.get("lookback_days", 7)
    resolution = config.get("resolution", 1.0)
    unit = config.get("unit", "miles")
    aggregation = config.get("aggregation", "avg")
    bounds_south = config.get("bounds_south")
    bounds_west = config.get("bounds_west")
    bounds_north = config.get("bounds_north")
    bounds_east = config.get("bounds_east")

    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)

    # Get all nodes with positions
    nodes_result = await db.execute(
        select(Node).where(
            Node.latitude.isnot(None),
            Node.longitude.isnot(None),
        )
    )
    nodes = nodes_result.scalars().all()

    if not nodes:
        return GenerateResponse(
            success=False,
            cell_count=0,
            message="No nodes with positions found",
        )

    # Build node_num to position lookup
    node_positions = {}
    for node in nodes:
        if node.latitude and node.longitude:
            node_positions[node.node_num] = {
                "latitude": node.latitude,
                "longitude": node.longitude,
            }

    # Get channel utilization telemetry
    util_query = (
        select(Telemetry)
        .where(Telemetry.received_at >= cutoff)
        .where(Telemetry.metric_name == "channelUtilization")
        .where(Telemetry.channel_utilization.isnot(None))
    )
    util_result = await db.execute(util_query)
    util_records = util_result.scalars().all()

    if not util_records:
        return GenerateResponse(
            success=False,
            cell_count=0,
            message="No channel utilization data found",
        )

    # Match telemetry to node positions
    data_points = []
    for record in util_records:
        pos = node_positions.get(record.node_num)
        if pos:
            data_points.append({
                "latitude": pos["latitude"],
                "longitude": pos["longitude"],
                "value": record.channel_utilization,
            })

    if not data_points:
        return GenerateResponse(
            success=False,
            cell_count=0,
            message="No utilization data with node positions found",
        )

    # Filter by bounds if specified
    if all([bounds_south, bounds_west, bounds_north, bounds_east]):
        data_points = [
            p for p in data_points
            if bounds_south <= p["latitude"] <= bounds_north
            and bounds_west <= p["longitude"] <= bounds_east
        ]

    if not data_points:
        return GenerateResponse(
            success=False,
            cell_count=0,
            message="No utilization data within specified bounds",
        )

    # Calculate grid
    cell_size_km = resolution * MILES_TO_KM if unit == "miles" else resolution
    cell_size_lat = cell_size_km / KM_PER_DEGREE_LAT

    lats = [p["latitude"] for p in data_points]
    lngs = [p["longitude"] for p in data_points]
    min_lat, max_lat = min(lats), max(lats)
    min_lng, max_lng = min(lngs), max(lngs)

    # Use bounds if specified, otherwise use data bounds
    if all([bounds_south, bounds_west, bounds_north, bounds_east]):
        min_lat = max(min_lat, bounds_south)
        max_lat = min(max_lat, bounds_north)
        min_lng = max(min_lng, bounds_west)
        max_lng = min(max_lng, bounds_east)

    center_lat = (min_lat + max_lat) / 2
    km_per_degree_lng = KM_PER_DEGREE_LAT * math.cos(center_lat * math.pi / 180)
    cell_size_lng = cell_size_km / km_per_degree_lng

    # Align to grid
    grid_min_lat = math.floor(min_lat / cell_size_lat) * cell_size_lat
    grid_max_lat = math.ceil(max_lat / cell_size_lat) * cell_size_lat
    grid_min_lng = math.floor(min_lng / cell_size_lng) * cell_size_lng
    grid_max_lng = math.ceil(max_lng / cell_size_lng) * cell_size_lng

    # Collect values in each cell
    cell_values: dict[str, list[float]] = {}
    for point in data_points:
        cell_row = int((point["latitude"] - grid_min_lat) / cell_size_lat)
        cell_col = int((point["longitude"] - grid_min_lng) / cell_size_lng)
        key = f"{cell_row},{cell_col}"
        if key not in cell_values:
            cell_values[key] = []
        cell_values[key].append(point["value"])

    # Check grid size
    num_rows = math.ceil((grid_max_lat - grid_min_lat) / cell_size_lat)
    num_cols = math.ceil((grid_max_lng - grid_min_lng) / cell_size_lng)
    if num_rows * num_cols > 50000:
        return GenerateResponse(
            success=False,
            cell_count=0,
            message=f"Grid too large ({num_rows}x{num_cols}). Increase resolution or reduce bounds.",
        )

    # Clear existing cells
    await db.execute(delete(UtilizationCell))

    # Create new cells with aggregated values
    now = datetime.now(UTC)
    cells_created = 0
    for key, values in cell_values.items():
        row, col = map(int, key.split(","))
        south = grid_min_lat + row * cell_size_lat
        north = south + cell_size_lat
        west = grid_min_lng + col * cell_size_lng
        east = west + cell_size_lng

        # Apply aggregation
        if aggregation == "min":
            agg_value = min(values)
        elif aggregation == "max":
            agg_value = max(values)
        else:  # avg
            agg_value = sum(values) / len(values)

        cell = UtilizationCell(
            south=south,
            west=west,
            north=north,
            east=east,
            value=round(agg_value, 2),
            color=get_color_for_utilization(agg_value),
            generated_at=now,
        )
        db.add(cell)
        cells_created += 1

    # Update last_generated in config
    config["last_generated"] = now.isoformat()
    setting.value = config
    flag_modified(setting, "value")

    await db.commit()

    return GenerateResponse(
        success=True,
        cell_count=cells_created,
        message=f"Generated {cells_created} cells from {len(data_points)} data points using {aggregation}",
    )


@router.get("/cells", response_model=list[UtilizationCellResponse])
async def get_utilization_cells(
    db: AsyncSession = Depends(get_db),
) -> list[UtilizationCellResponse]:
    """Get all utilization grid cells for map overlay."""
    result = await db.execute(select(UtilizationCell))
    cells = result.scalars().all()

    return [
        UtilizationCellResponse(
            south=cell.south,
            west=cell.west,
            north=cell.north,
            east=cell.east,
            value=cell.value,
            color=cell.color,
        )
        for cell in cells
    ]
