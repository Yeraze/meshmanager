"""UI data endpoints (internal use for frontend)."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Node, Source, Telemetry, Traceroute
from app.schemas.node import NodeResponse, NodeSummary
from app.schemas.telemetry import TelemetryHistory, TelemetryHistoryPoint, TelemetryResponse
from app.services.collector_manager import collector_manager

router = APIRouter(prefix="/api", tags=["ui"])


class SourceSummary:
    """Simple source summary for public display."""

    def __init__(self, id: str, name: str, type: str, enabled: bool, last_poll_at: datetime | None):
        self.id = id
        self.name = name
        self.type = type
        self.enabled = enabled
        self.last_poll_at = last_poll_at


@router.get("/sources")
async def list_sources_public(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List sources (public, names only)."""
    result = await db.execute(select(Source).order_by(Source.name))
    sources = result.scalars().all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "type": s.type.value,
            "enabled": s.enabled,
            "healthy": s.enabled and s.last_error is None,
        }
        for s in sources
    ]


@router.get("/nodes", response_model=list[NodeSummary])
async def list_nodes(
    db: AsyncSession = Depends(get_db),
    source_id: str | None = Query(default=None, description="Filter by source ID"),
    active_only: bool = Query(default=False, description="Only show recently active nodes"),
    active_hours: int = Query(default=1, ge=1, le=8760, description="Hours to consider a node active (1-8760)"),
) -> list[NodeSummary]:
    """List all nodes across all sources.

    When no source_id filter is applied, returns deduplicated nodes by node_num,
    showing only the record with the most recent last_heard timestamp.
    """
    query = select(Node, Source.name.label("source_name")).join(Source)

    if source_id:
        # When filtering by source, return all nodes from that source
        query = query.where(Node.source_id == source_id)

    if active_only:
        cutoff = datetime.now(UTC) - timedelta(hours=active_hours)
        query = query.where(Node.last_heard >= cutoff)

    query = query.order_by(Node.last_heard.desc().nullslast())

    result = await db.execute(query)
    rows = result.all()

    # If no source filter, deduplicate by node_num keeping the one with newest last_heard
    if not source_id:
        seen_node_nums: dict[int, tuple] = {}
        for node, source_name in rows:
            if node.node_num not in seen_node_nums:
                seen_node_nums[node.node_num] = (node, source_name)
        rows = list(seen_node_nums.values())

    return [
        NodeSummary(
            id=node.id,
            source_id=node.source_id,
            source_name=source_name,
            node_num=node.node_num,
            node_id=node.node_id,
            short_name=node.short_name,
            long_name=node.long_name,
            hw_model=node.hw_model,
            role=node.role,
            latitude=node.latitude,
            longitude=node.longitude,
            snr=node.snr,
            rssi=node.rssi,
            hops_away=node.hops_away,
            last_heard=node.last_heard,
        )
        for node, source_name in rows
    ]


@router.get("/nodes/by-node-num/{node_num}")
async def get_nodes_by_node_num(
    node_num: int,
    db: AsyncSession = Depends(get_db),
) -> list[NodeSummary]:
    """Get all node records across sources for a given node_num."""
    result = await db.execute(
        select(Node, Source.name.label("source_name"))
        .join(Source)
        .where(Node.node_num == node_num)
        .order_by(Node.last_heard.desc().nullslast())
    )
    rows = result.all()

    return [
        NodeSummary(
            id=node.id,
            source_id=node.source_id,
            source_name=source_name,
            node_num=node.node_num,
            node_id=node.node_id,
            short_name=node.short_name,
            long_name=node.long_name,
            hw_model=node.hw_model,
            role=node.role,
            latitude=node.latitude,
            longitude=node.longitude,
            snr=node.snr,
            rssi=node.rssi,
            hops_away=node.hops_away,
            last_heard=node.last_heard,
        )
        for node, source_name in rows
    ]


@router.get("/nodes/roles")
async def list_node_roles(
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """Get list of unique node roles in the database."""
    result = await db.execute(
        select(Node.role).distinct().where(Node.role.isnot(None))
    )
    roles = [row[0] for row in result.all() if row[0]]
    return sorted(roles)


@router.get("/nodes/{node_id}", response_model=NodeResponse)
async def get_node(
    node_id: str,
    db: AsyncSession = Depends(get_db),
) -> NodeResponse:
    """Get a specific node by ID."""
    result = await db.execute(
        select(Node, Source.name.label("source_name"))
        .join(Source)
        .where(Node.id == node_id)
    )
    row = result.first()
    if not row:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Node not found")

    node, source_name = row
    response = NodeResponse.model_validate(node)
    response.source_name = source_name
    return response


@router.get("/telemetry/{node_num}")
async def get_telemetry(
    node_num: int,
    db: AsyncSession = Depends(get_db),
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history to fetch"),
) -> list[TelemetryResponse]:
    """Get recent telemetry for a node across all sources."""
    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    result = await db.execute(
        select(Telemetry, Source.name.label("source_name"))
        .join(Source)
        .where(Telemetry.node_num == node_num)
        .where(Telemetry.received_at >= cutoff)
        .order_by(Telemetry.received_at.desc())
    )
    rows = result.all()

    return [
        TelemetryResponse(
            id=t.id,
            source_id=t.source_id,
            source_name=source_name,
            node_num=t.node_num,
            telemetry_type=t.telemetry_type.value,
            battery_level=t.battery_level,
            voltage=t.voltage,
            channel_utilization=t.channel_utilization,
            air_util_tx=t.air_util_tx,
            uptime_seconds=t.uptime_seconds,
            temperature=t.temperature,
            relative_humidity=t.relative_humidity,
            barometric_pressure=t.barometric_pressure,
            current=t.current,
            snr_local=t.snr_local,
            snr_remote=t.snr_remote,
            rssi=t.rssi,
            received_at=t.received_at,
        )
        for t, source_name in rows
    ]


@router.get("/telemetry/{node_num}/history/{metric}")
async def get_telemetry_history(
    node_num: int,
    metric: str,
    db: AsyncSession = Depends(get_db),
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history to fetch"),
) -> TelemetryHistory:
    """Get historical data for a specific telemetry metric."""
    # Validate metric name
    valid_metrics = {
        "battery_level": ("Battery Level", "%"),
        "voltage": ("Voltage", "V"),
        "channel_utilization": ("Channel Utilization", "%"),
        "air_util_tx": ("Air Utilization TX", "%"),
        "uptime_seconds": ("Uptime", "s"),
        "temperature": ("Temperature", "°C"),
        "relative_humidity": ("Humidity", "%"),
        "barometric_pressure": ("Pressure", "hPa"),
        "current": ("Current", "mA"),
        "snr_local": ("SNR (Local)", "dB"),
        "snr_remote": ("SNR (Remote)", "dB"),
        "rssi": ("RSSI", "dBm"),
    }

    if metric not in valid_metrics:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")

    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    result = await db.execute(
        select(Telemetry, Source.name.label("source_name"))
        .join(Source)
        .where(Telemetry.node_num == node_num)
        .where(Telemetry.received_at >= cutoff)
        .order_by(Telemetry.received_at.asc())
    )
    rows = result.all()

    # Extract the metric values
    data = []
    for t, source_name in rows:
        value = getattr(t, metric, None)
        if value is not None:
            data.append(
                TelemetryHistoryPoint(
                    timestamp=t.received_at,
                    source_id=t.source_id,
                    source_name=source_name,
                    value=float(value),
                )
            )

    metric_name, unit = valid_metrics[metric]
    return TelemetryHistory(metric=metric_name, unit=unit, data=data)


@router.get("/sources/collection-status")
async def get_collection_statuses() -> dict[str, dict]:
    """Get collection status for all sources.

    Returns a dict mapping source_id to status info:
    - status: "idle" | "collecting" | "complete" | "error"
    - current_batch: current batch number (1-based)
    - max_batches: total batches to collect
    - total_collected: records collected so far
    - last_error: error message if status is "error"
    """
    return collector_manager.get_all_collection_statuses()


@router.get("/position-history")
async def get_position_history(
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=7, ge=1, le=365, description="Days of history"),
) -> list[dict]:
    """Get historical position data for coverage analysis.

    Returns all position telemetry records within the specified time range.
    Each record contains node_num, latitude, longitude, and timestamp.
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)

    result = await db.execute(
        select(Telemetry)
        .where(Telemetry.received_at >= cutoff)
        .where(Telemetry.metric_name.in_(["latitude", "estimated_latitude"]))
        .where(Telemetry.latitude.isnot(None))
        .order_by(Telemetry.received_at.desc())
    )
    lat_records = result.scalars().all()

    # Also get longitude records to pair them
    result = await db.execute(
        select(Telemetry)
        .where(Telemetry.received_at >= cutoff)
        .where(Telemetry.metric_name.in_(["longitude", "estimated_longitude"]))
        .where(Telemetry.longitude.isnot(None))
        .order_by(Telemetry.received_at.desc())
    )
    lng_records = result.scalars().all()

    # Create a lookup for longitude by (source_id, node_num, received_at)
    # We need to match latitude and longitude records that came at similar times
    lng_lookup = {}
    for lng in lng_records:
        # Round timestamp to nearest minute for matching
        ts_key = lng.received_at.replace(second=0, microsecond=0)
        # Use str() for source_id to ensure consistent dict keys
        key = (str(lng.source_id), lng.node_num, ts_key)
        if key not in lng_lookup:
            lng_lookup[key] = lng.longitude

    positions = []
    for lat in lat_records:
        ts_key = lat.received_at.replace(second=0, microsecond=0)
        key = (str(lat.source_id), lat.node_num, ts_key)
        lng_value = lng_lookup.get(key)
        if lng_value is not None:
            positions.append({
                "node_num": lat.node_num,
                "latitude": lat.latitude,
                "longitude": lng_value,
                "timestamp": lat.received_at.isoformat(),
            })

    return positions


@router.get("/traceroutes")
async def list_traceroutes(
    db: AsyncSession = Depends(get_db),
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history"),
) -> list[dict]:
    """Get recent traceroutes for rendering on the map."""
    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    result = await db.execute(
        select(Traceroute)
        .where(Traceroute.received_at >= cutoff)
        .order_by(Traceroute.received_at.desc())
    )
    traceroutes = result.scalars().all()

    return [
        {
            "id": t.id,
            "source_id": t.source_id,
            "from_node_num": t.from_node_num,
            "to_node_num": t.to_node_num,
            "route": t.route,
            "route_back": t.route_back,
            "received_at": t.received_at.isoformat(),
        }
        for t in traceroutes
    ]


@router.get("/connections")
async def get_node_connections(
    db: AsyncSession = Depends(get_db),
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history"),
    node_num: int | None = Query(default=None, description="Filter connections for specific node"),
) -> dict:
    """Get node connections graph data from traceroutes.
    
    Returns nodes and edges for graph visualization.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    # Get traceroutes
    query = select(Traceroute).where(Traceroute.received_at >= cutoff)
    if node_num is not None:
        # Filter traceroutes that involve this node
        query = query.where(
            (Traceroute.from_node_num == node_num) |
            (Traceroute.to_node_num == node_num) |
            ((Traceroute.route.isnot(None)) & (Traceroute.route.contains([node_num]))) |
            ((Traceroute.route_back.isnot(None)) & (Traceroute.route_back.contains([node_num])))
        )
    
    result = await db.execute(query.order_by(Traceroute.received_at.desc()))
    traceroutes = result.scalars().all()

    # Get all nodes that appear in traceroutes
    node_nums = set()
    for t in traceroutes:
        if t.route_back is not None:  # Only use complete traceroutes
            node_nums.add(t.from_node_num)
            node_nums.add(t.to_node_num)
            if t.route:
                node_nums.update(t.route)
            if t.route_back:
                node_nums.update(t.route_back)

    # Skip broadcast address
    node_nums.discard(4294967295)

    if not node_nums:
        return {"nodes": [], "edges": []}

    # Get node details
    result = await db.execute(
        select(Node)
        .where(Node.node_num.in_(node_nums))
        .where(Node.latitude.isnot(None))
        .where(Node.longitude.isnot(None))
    )
    nodes = result.scalars().all()

    # Build node map
    node_map = {n.node_num: n for n in nodes}
    node_nums_with_data = set(node_map.keys())

    # Build edges from traceroutes
    edges_map: dict[tuple[int, int], dict] = {}
    
    def add_edge(from_num: int, to_num: int, usage: int = 1):
        """Add or update an edge between two nodes."""
        if from_num == 4294967295 or to_num == 4294967295:
            return
        if from_num not in node_nums_with_data or to_num not in node_nums_with_data:
            return
        
        # Use sorted tuple for undirected edges
        edge_key = tuple(sorted([from_num, to_num]))
        if edge_key in edges_map:
            edges_map[edge_key]["usage"] += usage
        else:
            edges_map[edge_key] = {
                "source": from_num,
                "target": to_num,
                "usage": usage,
            }

    # Process traceroutes to build edges
    for t in traceroutes:
        if t.route_back is None:  # Skip incomplete traceroutes
            continue
        
        # Add direct edge
        add_edge(t.from_node_num, t.to_node_num)
        
        # Add edges from route
        if t.route:
            prev = t.from_node_num
            for hop in t.route:
                add_edge(prev, hop)
                prev = hop
        
        # Add edges from route_back
        if t.route_back:
            prev = t.to_node_num
            for hop in t.route_back:
                add_edge(prev, hop)
                prev = hop

    # Build response
    nodes_data = []
    for node_num, node in node_map.items():
        nodes_data.append({
            "id": node_num,
            "node_num": node.node_num,
            "name": node.long_name or node.short_name or f"Node {node.node_num}",
            "short_name": node.short_name,
            "long_name": node.long_name,
            "latitude": node.latitude,
            "longitude": node.longitude,
            "role": node.role,
            "hw_model": node.hw_model,
            "last_heard": node.last_heard.isoformat() if node.last_heard else None,
        })
    
    edges_data = list(edges_map.values())
    
    return {
        "nodes": nodes_data,
        "edges": edges_data,
    }


