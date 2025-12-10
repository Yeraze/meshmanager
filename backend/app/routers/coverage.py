"""Coverage map API endpoints."""

import math
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.database import get_db
from app.models import CoverageCell, SystemSetting, Telemetry

router = APIRouter(prefix="/api/coverage", tags=["coverage"])

# Constants for coordinate conversion
KM_PER_DEGREE_LAT = 111.0
MILES_TO_KM = 1.60934

# Color scale for heatmap
COLORS = [
    "rgba(65, 105, 225, 0.4)",   # 1 - Royal Blue
    "rgba(50, 205, 50, 0.5)",    # 2 - Lime Green
    "rgba(255, 255, 0, 0.5)",    # 3 - Yellow
    "rgba(255, 165, 0, 0.6)",    # 4-5 - Orange
    "rgba(255, 69, 0, 0.6)",     # 6-7 - Red-Orange
    "rgba(255, 0, 0, 0.7)",      # 8-9 - Red
    "rgba(139, 0, 0, 0.8)",      # 10+ - Dark Red
]

COVERAGE_CONFIG_KEY = "coverage_config"


def get_color_for_count(count: int) -> str:
    """Get heatmap color for position count."""
    if count <= 0:
        return "transparent"
    if count == 1:
        return COLORS[0]
    if count == 2:
        return COLORS[1]
    if count == 3:
        return COLORS[2]
    if count <= 5:
        return COLORS[3]
    if count <= 7:
        return COLORS[4]
    if count <= 9:
        return COLORS[5]
    return COLORS[6]


class CoverageConfigRequest(BaseModel):
    """Request schema for coverage configuration."""

    enabled: bool = False
    resolution: float = 1.0  # in miles or km
    unit: str = "miles"  # "miles" or "kilometers"
    lookback_days: int = 7
    # Map bounds (set by panning/zooming)
    bounds_south: float | None = None
    bounds_west: float | None = None
    bounds_north: float | None = None
    bounds_east: float | None = None


class CoverageConfigResponse(BaseModel):
    """Response schema for coverage configuration."""

    enabled: bool
    resolution: float
    unit: str
    lookback_days: int
    bounds_south: float | None
    bounds_west: float | None
    bounds_north: float | None
    bounds_east: float | None
    last_generated: str | None
    cell_count: int


class CoverageCellResponse(BaseModel):
    """Response schema for a coverage cell."""

    south: float
    west: float
    north: float
    east: float
    count: int
    color: str


class GenerateResponse(BaseModel):
    """Response schema for generate action."""

    success: bool
    cell_count: int
    message: str


@router.get("/config", response_model=CoverageConfigResponse)
async def get_coverage_config(db: AsyncSession = Depends(get_db)) -> CoverageConfigResponse:
    """Get current coverage map configuration."""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == COVERAGE_CONFIG_KEY)
    )
    setting = result.scalar()

    # Count existing cells
    count_result = await db.execute(select(CoverageCell.id))
    cell_count = len(count_result.all())

    if not setting:
        return CoverageConfigResponse(
            enabled=False,
            resolution=1.0,
            unit="miles",
            lookback_days=7,
            bounds_south=None,
            bounds_west=None,
            bounds_north=None,
            bounds_east=None,
            last_generated=None,
            cell_count=cell_count,
        )

    value = setting.value
    return CoverageConfigResponse(
        enabled=value.get("enabled", False),
        resolution=value.get("resolution", 1.0),
        unit=value.get("unit", "miles"),
        lookback_days=value.get("lookback_days", 7),
        bounds_south=value.get("bounds_south"),
        bounds_west=value.get("bounds_west"),
        bounds_north=value.get("bounds_north"),
        bounds_east=value.get("bounds_east"),
        last_generated=value.get("last_generated"),
        cell_count=cell_count,
    )


@router.put("/config", response_model=CoverageConfigResponse)
async def update_coverage_config(
    config: CoverageConfigRequest,
    db: AsyncSession = Depends(get_db),
) -> CoverageConfigResponse:
    """Update coverage map configuration."""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == COVERAGE_CONFIG_KEY)
    )
    setting = result.scalar()

    value = {
        "enabled": config.enabled,
        "resolution": config.resolution,
        "unit": config.unit,
        "lookback_days": config.lookback_days,
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
        setting = SystemSetting(key=COVERAGE_CONFIG_KEY, value=value)
        db.add(setting)

    await db.commit()

    # Count cells
    count_result = await db.execute(select(CoverageCell.id))
    cell_count = len(count_result.all())

    return CoverageConfigResponse(
        enabled=value.get("enabled", False),
        resolution=value.get("resolution", 1.0),
        unit=value.get("unit", "miles"),
        lookback_days=value.get("lookback_days", 7),
        bounds_south=value.get("bounds_south"),
        bounds_west=value.get("bounds_west"),
        bounds_north=value.get("bounds_north"),
        bounds_east=value.get("bounds_east"),
        last_generated=value.get("last_generated"),
        cell_count=cell_count,
    )


@router.post("/generate", response_model=GenerateResponse)
async def generate_coverage(db: AsyncSession = Depends(get_db)) -> GenerateResponse:
    """Generate coverage grid from position history."""
    # Get config
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == COVERAGE_CONFIG_KEY)
    )
    setting = result.scalar()

    if not setting:
        raise HTTPException(status_code=400, detail="Coverage not configured")

    config = setting.value
    lookback_days = config.get("lookback_days", 7)
    resolution = config.get("resolution", 1.0)
    unit = config.get("unit", "miles")
    bounds_south = config.get("bounds_south")
    bounds_west = config.get("bounds_west")
    bounds_north = config.get("bounds_north")
    bounds_east = config.get("bounds_east")

    # Fetch position data
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    # Get latitude records
    lat_query = (
        select(Telemetry)
        .where(Telemetry.received_at >= cutoff)
        .where(Telemetry.metric_name.in_(["latitude", "estimated_latitude"]))
        .where(Telemetry.latitude.isnot(None))
    )
    lat_result = await db.execute(lat_query)
    lat_records = lat_result.scalars().all()

    # Get longitude records
    lng_query = (
        select(Telemetry)
        .where(Telemetry.received_at >= cutoff)
        .where(Telemetry.metric_name.in_(["longitude", "estimated_longitude"]))
        .where(Telemetry.longitude.isnot(None))
    )
    lng_result = await db.execute(lng_query)
    lng_records = lng_result.scalars().all()

    # Match lat/lng by timestamp
    lng_lookup = {}
    for lng in lng_records:
        ts_key = lng.received_at.replace(second=0, microsecond=0)
        key = (str(lng.source_id), lng.node_num, ts_key)
        if key not in lng_lookup:
            lng_lookup[key] = lng.longitude

    positions = []
    for lat in lat_records:
        ts_key = lat.received_at.replace(second=0, microsecond=0)
        key = (str(lat.source_id), lat.node_num, ts_key)
        lng_value = lng_lookup.get(key)
        if lng_value is not None:
            positions.append({"latitude": lat.latitude, "longitude": lng_value})

    if not positions:
        return GenerateResponse(
            success=False,
            cell_count=0,
            message="No position data found",
        )

    # Filter by bounds if specified
    if all([bounds_south, bounds_west, bounds_north, bounds_east]):
        positions = [
            p for p in positions
            if bounds_south <= p["latitude"] <= bounds_north
            and bounds_west <= p["longitude"] <= bounds_east
        ]

    if not positions:
        return GenerateResponse(
            success=False,
            cell_count=0,
            message="No positions within specified bounds",
        )

    # Calculate grid
    cell_size_km = resolution * MILES_TO_KM if unit == "miles" else resolution
    cell_size_lat = cell_size_km / KM_PER_DEGREE_LAT

    lats = [p["latitude"] for p in positions]
    lngs = [p["longitude"] for p in positions]
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

    # Count positions in each cell
    cell_counts: dict[str, int] = {}
    for pos in positions:
        cell_row = int((pos["latitude"] - grid_min_lat) / cell_size_lat)
        cell_col = int((pos["longitude"] - grid_min_lng) / cell_size_lng)
        key = f"{cell_row},{cell_col}"
        cell_counts[key] = cell_counts.get(key, 0) + 1

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
    await db.execute(delete(CoverageCell))

    # Create new cells
    now = datetime.now(timezone.utc)
    cells_created = 0
    for key, count in cell_counts.items():
        row, col = map(int, key.split(","))
        south = grid_min_lat + row * cell_size_lat
        north = south + cell_size_lat
        west = grid_min_lng + col * cell_size_lng
        east = west + cell_size_lng

        cell = CoverageCell(
            south=south,
            west=west,
            north=north,
            east=east,
            count=min(count, 100),  # Cap display count
            color=get_color_for_count(count),
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
        message=f"Generated {cells_created} cells from {len(positions)} positions",
    )


@router.get("/cells", response_model=list[CoverageCellResponse])
async def get_coverage_cells(db: AsyncSession = Depends(get_db)) -> list[CoverageCellResponse]:
    """Get all coverage grid cells for map overlay."""
    result = await db.execute(select(CoverageCell))
    cells = result.scalars().all()

    return [
        CoverageCellResponse(
            south=cell.south,
            west=cell.west,
            north=cell.north,
            east=cell.east,
            count=cell.count,
            color=cell.color,
        )
        for cell in cells
    ]
