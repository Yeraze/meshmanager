"""Coverage map API endpoints."""

import math
import tempfile
from datetime import UTC, datetime, timedelta
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import Numeric, cast, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.database import get_db
from app.models import CoverageCell, Node, SystemSetting, Telemetry

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
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)

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
    now = datetime.now(UTC)
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


class PositionPoint(BaseModel):
    """A single position point for heatmap rendering."""

    lat: float
    lng: float


@router.get("/positions", response_model=list[PositionPoint])
async def get_position_history(
    lookback_days: int = 7,
    bounds_south: float | None = None,
    bounds_west: float | None = None,
    bounds_north: float | None = None,
    bounds_east: float | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[PositionPoint]:
    """Get raw position points for heatmap rendering."""
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)

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
            positions.append(PositionPoint(lat=lat.latitude, lng=lng_value))

    # Filter by bounds if specified
    if all([bounds_south, bounds_west, bounds_north, bounds_east]):
        positions = [
            p for p in positions
            if bounds_south <= p.lat <= bounds_north
            and bounds_west <= p.lng <= bounds_east
        ]

    return positions


@router.get("/export/kml")
async def export_kml(db: AsyncSession = Depends(get_db)) -> Response:
    """Export coverage grid as KML file."""
    result = await db.execute(select(CoverageCell))
    cells = result.scalars().all()

    if not cells:
        raise HTTPException(status_code=404, detail="No coverage data to export")

    # Create KML document
    kml = ET.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    doc = ET.SubElement(kml, "Document")
    ET.SubElement(doc, "name").text = "MeshManager Coverage Map"
    ET.SubElement(doc, "description").text = (
        f"Coverage map with {len(cells)} cells, "
        f"generated {datetime.now(UTC).isoformat()}"
    )

    # Define styles for each count range
    style_colors = [
        ("style1", "99E36941"),      # Blue (AABBGGRR format)
        ("style2", "9932CD32"),      # Green
        ("style3", "9900FFFF"),      # Yellow
        ("style4", "9900A5FF"),      # Orange
        ("style5", "990045FF"),      # Red-Orange
        ("style6", "990000FF"),      # Red
        ("style7", "99000088"),      # Dark Red
    ]

    for style_id, color in style_colors:
        style = ET.SubElement(doc, "Style", id=style_id)
        poly_style = ET.SubElement(style, "PolyStyle")
        ET.SubElement(poly_style, "color").text = color
        ET.SubElement(poly_style, "outline").text = "0"

    def get_style_id(count: int) -> str:
        if count <= 1:
            return "#style1"
        if count <= 2:
            return "#style2"
        if count <= 3:
            return "#style3"
        if count <= 5:
            return "#style4"
        if count <= 7:
            return "#style5"
        if count <= 9:
            return "#style6"
        return "#style7"

    # Create placemarks for each cell
    for cell in cells:
        placemark = ET.SubElement(doc, "Placemark")
        ET.SubElement(placemark, "name").text = f"Count: {cell.count}"
        ET.SubElement(placemark, "description").text = (
            f"Position reports: {cell.count}\n"
            f"Bounds: {cell.south:.6f}, {cell.west:.6f} to {cell.north:.6f}, {cell.east:.6f}"
        )
        ET.SubElement(placemark, "styleUrl").text = get_style_id(cell.count)

        polygon = ET.SubElement(placemark, "Polygon")
        ET.SubElement(polygon, "altitudeMode").text = "clampToGround"
        outer = ET.SubElement(polygon, "outerBoundaryIs")
        ring = ET.SubElement(outer, "LinearRing")
        # KML coordinates: lon,lat,altitude (altitude optional)
        coords = (
            f"{cell.west},{cell.south},0 "
            f"{cell.east},{cell.south},0 "
            f"{cell.east},{cell.north},0 "
            f"{cell.west},{cell.north},0 "
            f"{cell.west},{cell.south},0"
        )
        ET.SubElement(ring, "coordinates").text = coords

    # Generate XML
    kml_content = ET.tostring(kml, encoding="unicode", xml_declaration=True)

    return Response(
        content=kml_content,
        media_type="application/vnd.google-earth.kml+xml",
        headers={"Content-Disposition": "attachment; filename=coverage.kml"},
    )


async def _get_position_points(
    db: AsyncSession,
    lookback_days: int = 7,
    bounds_south: float | None = None,
    bounds_west: float | None = None,
    bounds_north: float | None = None,
    bounds_east: float | None = None,
) -> list[dict]:
    """Get position points for export (internal helper)."""
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)

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
            lng_lookup[key] = (lng.longitude, lng.received_at)

    positions = []
    for lat in lat_records:
        ts_key = lat.received_at.replace(second=0, microsecond=0)
        key = (str(lat.source_id), lat.node_num, ts_key)
        lng_data = lng_lookup.get(key)
        if lng_data is not None:
            positions.append({
                "lat": lat.latitude,
                "lng": lng_data[0],
                "node_num": lat.node_num,
                "timestamp": lat.received_at.isoformat(),
            })

    # Filter by bounds if specified
    if all([bounds_south, bounds_west, bounds_north, bounds_east]):
        positions = [
            p for p in positions
            if bounds_south <= p["lat"] <= bounds_north
            and bounds_west <= p["lng"] <= bounds_east
        ]

    return positions


@router.get("/export/csv")
async def export_csv(
    lookback_days: int = 7,
    bounds_south: float | None = None,
    bounds_west: float | None = None,
    bounds_north: float | None = None,
    bounds_east: float | None = None,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export position points as CSV file with headers."""
    import csv
    import io

    positions = await _get_position_points(
        db, lookback_days, bounds_south, bounds_west, bounds_north, bounds_east
    )

    if not positions:
        raise HTTPException(status_code=404, detail="No position data to export")

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header row
    writer.writerow(["latitude", "longitude", "node_num", "timestamp"])

    # Write data rows
    for pos in positions:
        writer.writerow([pos["lat"], pos["lng"], pos["node_num"], pos["timestamp"]])

    csv_content = output.getvalue()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=positions.csv"},
    )


@router.get("/export/shapefile")
async def export_shapefile(
    lookback_days: int = 7,
    bounds_south: float | None = None,
    bounds_west: float | None = None,
    bounds_north: float | None = None,
    bounds_east: float | None = None,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export position points as Shapefile (.shp in a ZIP archive)."""
    try:
        import os
        import zipfile

        import fiona
        from fiona.crs import CRS
    except ImportError as e:
        raise HTTPException(
            status_code=501,
            detail=f"Shapefile export requires fiona: {e}",
        )

    positions = await _get_position_points(
        db, lookback_days, bounds_south, bounds_west, bounds_north, bounds_east
    )

    if not positions:
        raise HTTPException(status_code=404, detail="No position data to export")

    # Create shapefile in temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        shp_path = os.path.join(tmpdir, "positions.shp")

        # Define schema for point features
        schema = {
            "geometry": "Point",
            "properties": {
                "node_num": "int",
                "timestamp": "str",
            },
        }

        # Write shapefile
        with fiona.open(
            shp_path,
            "w",
            driver="ESRI Shapefile",
            crs=CRS.from_epsg(4326),
            schema=schema,
        ) as shp:
            for pos in positions:
                shp.write({
                    "geometry": {
                        "type": "Point",
                        "coordinates": (pos["lng"], pos["lat"]),
                    },
                    "properties": {
                        "node_num": pos["node_num"],
                        "timestamp": pos["timestamp"],
                    },
                })

        # Create ZIP archive with all shapefile components
        zip_path = os.path.join(tmpdir, "positions.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
                file_path = os.path.join(tmpdir, f"positions{ext}")
                if os.path.exists(file_path):
                    zf.write(file_path, f"positions{ext}")

        # Read ZIP content
        with open(zip_path, "rb") as f:
            zip_content = f.read()

    return Response(
        content=zip_content,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=positions.zip"},
    )


@router.get("/export/geopackage")
async def export_geopackage(
    lookback_days: int = 7,
    bounds_south: float | None = None,
    bounds_west: float | None = None,
    bounds_north: float | None = None,
    bounds_east: float | None = None,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export position points as GeoPackage (.gpkg) - OGC standard geodatabase format."""
    try:
        import os

        import fiona
        from fiona.crs import CRS
    except ImportError as e:
        raise HTTPException(
            status_code=501,
            detail=f"GeoPackage export requires fiona: {e}",
        )

    positions = await _get_position_points(
        db, lookback_days, bounds_south, bounds_west, bounds_north, bounds_east
    )

    if not positions:
        raise HTTPException(status_code=404, detail="No position data to export")

    # Create GeoPackage in temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        gpkg_path = os.path.join(tmpdir, "positions.gpkg")

        # Define schema for point features
        schema = {
            "geometry": "Point",
            "properties": {
                "node_num": "int",
                "timestamp": "str",
            },
        }

        # Write GeoPackage
        with fiona.open(
            gpkg_path,
            "w",
            driver="GPKG",
            crs=CRS.from_epsg(4326),
            schema=schema,
            layer="positions",
        ) as gpkg:
            for pos in positions:
                gpkg.write({
                    "geometry": {
                        "type": "Point",
                        "coordinates": (pos["lng"], pos["lat"]),
                    },
                    "properties": {
                        "node_num": pos["node_num"],
                        "timestamp": pos["timestamp"],
                    },
                })

        # Read file content
        with open(gpkg_path, "rb") as f:
            gpkg_content = f.read()

    return Response(
        content=gpkg_content,
        media_type="application/geopackage+sqlite3",
        headers={"Content-Disposition": "attachment; filename=positions.gpkg"},
    )


@router.get("/export/geotiff")
async def export_geotiff(db: AsyncSession = Depends(get_db)) -> Response:
    """Export coverage grid as GeoTIFF with 32-bit count values."""
    # Lazy import to avoid breaking startup if GDAL libraries are missing
    try:
        import numpy as np
        import rasterio
        from rasterio.crs import CRS
        from rasterio.transform import from_bounds
    except ImportError as e:
        raise HTTPException(
            status_code=501,
            detail=f"GeoTIFF export requires numpy and rasterio with GDAL libraries: {e}",
        )

    result = await db.execute(select(CoverageCell))
    cells = result.scalars().all()

    if not cells:
        raise HTTPException(status_code=404, detail="No coverage data to export")

    # Calculate grid bounds and cell size
    min_lat = min(c.south for c in cells)
    max_lat = max(c.north for c in cells)
    min_lng = min(c.west for c in cells)
    max_lng = max(c.east for c in cells)

    # Get cell size from first cell (assuming uniform grid)
    cell_height = cells[0].north - cells[0].south
    cell_width = cells[0].east - cells[0].west

    # Calculate grid dimensions
    num_rows = round((max_lat - min_lat) / cell_height)
    num_cols = round((max_lng - min_lng) / cell_width)

    # Create the raster array (initialize with nodata value)
    nodata_value = -1
    raster = np.full((num_rows, num_cols), nodata_value, dtype=np.int32)

    # Fill in cell values
    for cell in cells:
        # Calculate row/col indices (row 0 is at top/north)
        row = num_rows - 1 - round((cell.south - min_lat) / cell_height)
        col = round((cell.west - min_lng) / cell_width)

        if 0 <= row < num_rows and 0 <= col < num_cols:
            raster[row, col] = cell.count

    # Create transform (from bounds)
    transform = from_bounds(min_lng, min_lat, max_lng, max_lat, num_cols, num_rows)

    # Write to in-memory file
    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        tmp_path = tmp.name

    with rasterio.open(
        tmp_path,
        "w",
        driver="GTiff",
        height=num_rows,
        width=num_cols,
        count=1,
        dtype=np.int32,
        crs=CRS.from_epsg(4326),  # WGS84
        transform=transform,
        nodata=nodata_value,
    ) as dst:
        dst.write(raster, 1)
        # Add metadata
        dst.update_tags(
            TIFFTAG_IMAGEDESCRIPTION="MeshManager Coverage Map",
            TIFFTAG_SOFTWARE="MeshManager",
            coverage_cells=str(len(cells)),
            generated_at=datetime.now(UTC).isoformat(),
        )

    # Read the file content
    with open(tmp_path, "rb") as f:
        geotiff_content = f.read()

    # Clean up temp file
    import os

    os.unlink(tmp_path)

    return Response(
        content=geotiff_content,
        media_type="image/tiff",
        headers={"Content-Disposition": "attachment; filename=coverage.tif"},
    )


class MessageActivityPoint(BaseModel):
    """A single message activity point for heatmap rendering."""

    lat: float
    lng: float
    count: int = 1


@router.get("/message-activity", response_model=list[MessageActivityPoint])
async def get_message_activity(
    lookback_days: int = 7,
    bounds_south: float | None = None,
    bounds_west: float | None = None,
    bounds_north: float | None = None,
    bounds_east: float | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[MessageActivityPoint]:
    """Get message activity points for heatmap rendering.

    Each point represents telemetry/messages sent from a node's location.
    Points are aggregated by node to show activity counts per location.
    Uses Telemetry data (which includes device, environment, power, position data).
    """
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)

    # Use SQL aggregation to group by rounded coordinates (~11m precision)
    # This avoids loading all rows into memory
    lat_rounded = func.round(cast(Node.latitude, Numeric), 4).label("lat")
    lng_rounded = func.round(cast(Node.longitude, Numeric), 4).label("lng")

    query = (
        select(
            lat_rounded,
            lng_rounded,
            func.count().label("count"),
        )
        .select_from(Telemetry)
        .join(
            Node,
            (Telemetry.node_num == Node.node_num)
            & (Telemetry.source_id == Node.source_id),
        )
        .where(Telemetry.received_at >= cutoff)
        .where(Node.latitude.isnot(None))
        .where(Node.longitude.isnot(None))
    )

    # Apply bounds filter in SQL if specified
    if all([bounds_south, bounds_west, bounds_north, bounds_east]):
        query = query.where(
            Node.latitude >= bounds_south,
            Node.latitude <= bounds_north,
            Node.longitude >= bounds_west,
            Node.longitude <= bounds_east,
        )

    query = query.group_by(lat_rounded, lng_rounded)

    result = await db.execute(query)
    rows = result.all()

    return [
        MessageActivityPoint(lat=float(row.lat), lng=float(row.lng), count=row.count)
        for row in rows
    ]
