"""UI data endpoints (internal use for frontend)."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import require_tab_access
from app.database import get_db
from app.models import (
    Message,
    Node,
    PacketRecord,
    SolarProduction,
    Source,
    SystemSetting,
    Telemetry,
    Traceroute,
)
from app.models.packet_record import PacketRecordType
from app.models.source import SourceType
from app.models.telemetry import TelemetryType
from app.schemas.node import NodeResponse, NodeSummary
from app.schemas.telemetry import TelemetryHistory, TelemetryHistoryPoint, TelemetryResponse
from app.services.collector_manager import collector_manager
from app.telemetry_registry import CAMEL_TO_METRIC, METRIC_REGISTRY

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
    _access: None = Depends(require_tab_access("map")),
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
    _access: None = Depends(require_tab_access("map")),
) -> list[NodeSummary]:
    """List all nodes across all sources.

    Returns all node records from all sources so the frontend can filter
    by enabled sources and then deduplicate, ensuring nodes visible from
    multiple sources remain shown when any of their sources is enabled.
    """
    query = select(Node, Source.name.label("source_name")).join(Source)

    if source_id:
        query = query.where(Node.source_id == source_id)

    if active_only:
        cutoff = datetime.now(UTC) - timedelta(hours=active_hours)
        query = query.where(Node.last_heard >= cutoff)

    query = query.order_by(Node.last_heard.desc().nullslast())

    result = await db.execute(query)
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


@router.get("/nodes/by-node-num/{node_num}")
async def get_nodes_by_node_num(
    node_num: int,
    db: AsyncSession = Depends(get_db),
    _access: None = Depends(require_tab_access("nodes")),
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
    _access: None = Depends(require_tab_access("map")),
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
    _access: None = Depends(require_tab_access("nodes")),
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
    _access: None = Depends(require_tab_access("nodes")),
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


@router.get("/telemetry/{node_num}/metrics")
async def get_available_metrics(
    node_num: int,
    db: AsyncSession = Depends(get_db),
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history to check"),
    _access: None = Depends(require_tab_access("nodes")),
) -> dict:
    """Get available telemetry metrics for a node.

    Returns metrics grouped by telemetry type, with label/unit from registry.
    Only returns metrics that have actual data in the given time window.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    result = await db.execute(
        select(
            Telemetry.metric_name,
            Telemetry.telemetry_type,
            func.count().label("count"),
        )
        .where(Telemetry.node_num == node_num)
        .where(Telemetry.received_at >= cutoff)
        .where(Telemetry.metric_name.is_not(None))
        .group_by(Telemetry.metric_name, Telemetry.telemetry_type)
    )
    rows = result.all()

    # Consolidate aliases into canonical names and group by telemetry type
    consolidated: dict[str, dict] = {}  # canonical_name → {type_key, label, unit, count}
    for metric_name, telem_type, count in rows:
        metric_def = METRIC_REGISTRY.get(metric_name)
        if not metric_def:
            resolved = CAMEL_TO_METRIC.get(metric_name)
            if resolved:
                metric_def = METRIC_REGISTRY.get(resolved)

        canonical = metric_def.name if metric_def else metric_name
        type_key = telem_type.value if telem_type else "device"

        if canonical in consolidated:
            consolidated[canonical]["count"] += count
        else:
            consolidated[canonical] = {
                "name": canonical,
                "label": metric_def.label if metric_def else metric_name,
                "unit": metric_def.unit if metric_def else "",
                "type_key": type_key,
                "count": count,
            }

    # Group by telemetry type
    grouped: dict[str, list[dict]] = {}
    for entry in consolidated.values():
        type_key = entry.pop("type_key")
        if type_key not in grouped:
            grouped[type_key] = []
        grouped[type_key].append(entry)

    # Sort metrics within each group alphabetically by label
    for type_key in grouped:
        grouped[type_key].sort(key=lambda m: m["label"])

    return {
        "node_num": node_num,
        "hours": hours,
        "metrics": grouped,
    }


@router.get("/telemetry/{node_num}/history/{metric}")
async def get_telemetry_history(
    node_num: int,
    metric: str,
    db: AsyncSession = Depends(get_db),
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history to fetch"),
    _access: None = Depends(require_tab_access("graphs")),
) -> TelemetryHistory:
    """Get historical data for a specific telemetry metric."""
    # Look up metric in registry (accept both snake_case and camelCase)
    metric_def = METRIC_REGISTRY.get(metric)
    if not metric_def:
        resolved = CAMEL_TO_METRIC.get(metric)
        if resolved:
            metric_def = METRIC_REGISTRY.get(resolved)

    if not metric_def:
        raise HTTPException(status_code=400, detail=f"Unknown metric: {metric}")

    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    # Match both the requested name and the canonical snake_case name,
    # plus any camelCase variants that map to this metric
    metric_names = {metric, metric_def.name}
    for camel, snake in CAMEL_TO_METRIC.items():
        if snake == metric_def.name:
            metric_names.add(camel)

    result = await db.execute(
        select(Telemetry, Source.name.label("source_name"))
        .join(Source)
        .where(Telemetry.node_num == node_num)
        .where(Telemetry.received_at >= cutoff)
        .where(Telemetry.metric_name.in_(metric_names))
        .where(Telemetry.raw_value.isnot(None))
        .order_by(Telemetry.received_at.asc())
    )
    rows = result.all()

    data = []
    seen_timestamps: set[tuple] = set()
    for t, source_name in rows:
        key = (t.received_at, t.source_id)
        if key in seen_timestamps:
            continue
        seen_timestamps.add(key)
        data.append(
            TelemetryHistoryPoint(
                timestamp=t.received_at,
                source_id=t.source_id,
                source_name=source_name,
                value=float(t.raw_value),
            )
        )

    # Backward compat: also check dedicated column for old data without metric_name
    if metric_def.dedicated_column:
        col = getattr(Telemetry, metric_def.dedicated_column, None)
        if col is not None:
            legacy_result = await db.execute(
                select(Telemetry, Source.name.label("source_name"))
                .join(Source)
                .where(Telemetry.node_num == node_num)
                .where(Telemetry.received_at >= cutoff)
                .where(col.isnot(None))
                .where(Telemetry.metric_name.is_(None))
                .order_by(Telemetry.received_at.asc())
            )
            for t, source_name in legacy_result.all():
                key = (t.received_at, t.source_id)
                if key in seen_timestamps:
                    continue
                seen_timestamps.add(key)
                value = getattr(t, metric_def.dedicated_column)
                if value is not None:
                    data.append(
                        TelemetryHistoryPoint(
                            timestamp=t.received_at,
                            source_id=t.source_id,
                            source_name=source_name,
                            value=float(value),
                        )
                    )

    # Sort all data by timestamp
    data.sort(key=lambda p: p.timestamp)

    return TelemetryHistory(metric=metric_def.label, unit=metric_def.unit, data=data)


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
    _access: None = Depends(require_tab_access("map")),
) -> list[dict]:
    """Get historical position data for coverage analysis.

    Returns all position telemetry records within the specified time range.
    Each record contains node_num, latitude, longitude, and timestamp.
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Get position records (rows with both lat and lon populated)
    # Works for both MeshMonitor (separate metric rows) and MQTT (combined rows)
    result = await db.execute(
        select(Telemetry)
        .where(Telemetry.received_at >= cutoff)
        .where(Telemetry.latitude.isnot(None))
        .where(Telemetry.longitude.isnot(None))
        .order_by(Telemetry.received_at.desc())
    )
    records = result.scalars().all()

    return [
        {
            "node_num": r.node_num,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "timestamp": r.received_at.isoformat(),
        }
        for r in records
    ]


@router.get("/traceroutes")
async def list_traceroutes(
    db: AsyncSession = Depends(get_db),
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history"),
    _access: None = Depends(require_tab_access("map")),
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
            "route_positions": t.route_positions,
            "received_at": t.received_at.isoformat(),
        }
        for t in traceroutes
    ]


@router.get("/connections")
async def get_node_connections(
    db: AsyncSession = Depends(get_db),
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history"),
    node_num: int | None = Query(default=None, description="Filter connections for specific node"),
    _access: None = Depends(require_tab_access("map")),
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
    )
    nodes = result.scalars().all()

    # Build node map (all nodes, even without positions)
    node_map = {n.node_num: n for n in nodes}

    # Build position lookup: prefer route_positions, fall back to node DB positions
    # This ensures nodes that have moved since a traceroute still render at
    # their historical location, and nodes without DB positions but captured
    # in route_positions can still form edges.
    node_positions: dict[int, dict] = {}
    for t in traceroutes:
        if t.route_positions:
            for num_str, pos in t.route_positions.items():
                num = int(num_str)
                if num not in node_positions and pos:
                    node_positions[num] = pos

    # Overlay current DB positions (fill gaps not covered by route_positions)
    for n in nodes:
        if n.node_num not in node_positions and n.latitude is not None and n.longitude is not None:
            node_positions[n.node_num] = {"lat": n.latitude, "lng": n.longitude}

    node_nums_with_data = set(node_positions.keys())

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
    for num in node_nums_with_data:
        node = node_map.get(num)
        pos = node_positions[num]
        nodes_data.append({
            "id": num,
            "node_num": num,
            "name": (node.long_name or node.short_name or f"Node {num}") if node else f"Node {num}",
            "short_name": node.short_name if node else None,
            "long_name": node.long_name if node else None,
            "latitude": pos.get("lat"),
            "longitude": pos.get("lng"),
            "role": node.role if node else None,
            "hw_model": node.hw_model if node else None,
            "last_heard": node.last_heard.isoformat() if node and node.last_heard else None,
        })

    edges_data = list(edges_map.values())

    return {
        "nodes": nodes_data,
        "edges": edges_data,
    }


def _analyze_metric_for_solar_patterns(
    values: list[dict],
    is_battery: bool,
    previous_day_sunset: dict | None,
) -> dict | None:
    """Analyze a single metric (battery or voltage) for solar patterns.

    Args:
        values: List of {"time": datetime, "value": float} dicts, sorted by time
        is_battery: True for battery_level, False for voltage
        previous_day_sunset: Previous day's sunset data for discharge calculation

    Returns:
        Dict with pattern data if solar pattern detected, None otherwise
    """
    # Minimum time threshold for rate calculations (30 minutes)
    # Prevents division by very small numbers which could produce extreme rates
    min_hours_for_rate = 0.5

    if len(values) < 3:
        return None

    # Calculate daily variance - nodes on wall power have near-constant values
    all_values = [v["value"] for v in values]
    min_value = min(all_values)
    max_value = max(all_values)
    daily_range = max_value - min_value

    # Set thresholds based on metric type
    min_variance = 10 if is_battery else 0.3  # Battery: 10%, Voltage: 0.3V

    # Determine if this is potentially a "high-efficiency solar" setup
    # These nodes have large batteries/panels that stay 90-100% with minimal swing
    is_high_efficiency_candidate = False
    if is_battery:
        # Battery: stays above 90% with small but present swing (2-10%)
        is_high_efficiency_candidate = (
            min_value >= 90 and
            max_value >= 95 and
            daily_range >= 2 and daily_range < min_variance
        )
    else:
        # Voltage: stays above 4.0V with small but present swing (0.05-0.3V)
        is_high_efficiency_candidate = (
            min_value >= 4.0 and
            max_value >= 4.1 and
            daily_range >= 0.05 and daily_range < min_variance
        )

    # Skip days with truly constant values (wall power)
    # But allow high-efficiency candidates through
    if daily_range < min_variance and not is_high_efficiency_candidate:
        return None

    # Find morning values (6am-10am) and afternoon values (12pm-6pm)
    morning_values = [v for v in values if 6 <= v["time"].hour <= 10]
    afternoon_values = [v for v in values if 12 <= v["time"].hour <= 18]

    # If we don't have readings in both time windows, use simpler peak detection
    if morning_values and afternoon_values:
        # Solar pattern: morning low < afternoon high (charging during daylight)
        morning_low = min(morning_values, key=lambda v: v["value"])
        afternoon_high = max(afternoon_values, key=lambda v: v["value"])

        sunrise_value = morning_low["value"]
        sunrise_time = morning_low["time"]
        peak_value = afternoon_high["value"]
        peak_time = afternoon_high["time"]

        # Rise is the key solar indicator: morning-to-afternoon charge
        rise = peak_value - sunrise_value

        # Find the last reading of the day as "sunset" for display
        sunset_value = values[-1]["value"]
        sunset_time = values[-1]["time"]
        fall = peak_value - sunset_value
    else:
        # Fallback: use overall min/max with time constraints
        peak_idx = max(range(len(values)), key=lambda i: values[i]["value"])
        peak_value = values[peak_idx]["value"]
        peak_time = values[peak_idx]["time"]

        # Find lowest value before peak as sunrise
        sunrise_idx = 0
        min_before_peak = float("inf")
        for i in range(peak_idx + 1):
            if values[i]["value"] < min_before_peak:
                min_before_peak = values[i]["value"]
                sunrise_idx = i

        sunrise_time = values[sunrise_idx]["time"]
        sunrise_value = values[sunrise_idx]["value"]
        sunset_value = values[-1]["value"]
        sunset_time = values[-1]["time"]
        rise = peak_value - sunrise_value
        fall = peak_value - sunset_value

    # Check for solar pattern
    if is_high_efficiency_candidate:
        # Relaxed thresholds for high-efficiency solar
        min_rise_threshold = 1 if is_battery else 0.02
        min_ratio = 0.98
    else:
        min_rise_threshold = max(min_variance, daily_range * 0.3)
        min_ratio = 0.95

    has_solar_pattern = (
        rise >= min_rise_threshold and
        peak_time.hour >= 10 and peak_time.hour <= 18 and
        sunrise_time.hour <= 12 and
        sunrise_value <= peak_value * min_ratio
    )

    if not has_solar_pattern:
        return None

    # Calculate charge rate per hour (sunrise -> peak/100%)
    effective_peak_time = peak_time
    effective_peak_value = peak_value
    if is_battery:
        # Find if battery hits 100% between sunrise and sunset
        for v in values:
            if v["time"] > sunrise_time and v["time"] <= sunset_time and v["value"] >= 100:
                effective_peak_time = v["time"]
                effective_peak_value = v["value"]
                break

    charging_hours = (effective_peak_time - sunrise_time).total_seconds() / 3600
    charge_rate = (effective_peak_value - sunrise_value) / charging_hours if charging_hours >= min_hours_for_rate else None

    # Track daylight/charging hours (sunrise -> sunset)
    daylight_hours = (sunset_time - sunrise_time).total_seconds() / 3600

    # Calculate discharge rate per hour (previous sunset -> this sunrise)
    discharge_rate = None
    discharge_hours = None
    if previous_day_sunset is not None:
        prev_sunset_time = previous_day_sunset["time"]
        prev_sunset_value = previous_day_sunset["value"]
        discharge_hours = (sunrise_time - prev_sunset_time).total_seconds() / 3600
        if discharge_hours >= min_hours_for_rate:
            discharge_rate = (prev_sunset_value - sunrise_value) / discharge_hours

    return {
        "has_pattern": True,
        "is_high_efficiency": is_high_efficiency_candidate,
        "sunrise": {"time": sunrise_time, "value": sunrise_value},
        "peak": {"time": peak_time, "value": peak_value},
        "sunset": {"time": sunset_time, "value": sunset_value},
        "rise": rise,
        "fall": fall,
        "charge_rate": charge_rate,
        "discharge_rate": discharge_rate,
        "daylight_hours": daylight_hours if daylight_hours > 0 else None,
        "discharge_hours": discharge_hours,
        "daily_range": daily_range,
    }


@router.get("/analysis/solar-nodes")
async def identify_solar_nodes(
    db: AsyncSession = Depends(get_db),
    lookback_days: int = Query(default=7, ge=1, le=90, description="Days of history to analyze"),
    _access: None = Depends(require_tab_access("analysis")),
) -> dict:
    """Analyze telemetry to identify nodes that are likely solar-powered.

    Examines battery_level and voltage patterns over time to identify
    nodes that show a solar charging profile:
    - Rising values during daylight hours (sunrise to peak)
    - Falling values during night hours (peak to next sunrise)

    Returns a list of nodes with their solar score and daily patterns.
    """
    from collections import defaultdict

    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)

    # Fetch all battery_level, voltage, and INA voltage telemetry for the period
    # INA sensors report voltage as ch1Voltage, ch2Voltage, ch3Voltage with value in raw_value
    result = await db.execute(
        select(Telemetry, Source.name.label("source_name"))
        .join(Source)
        .where(Telemetry.received_at >= cutoff)
        .where(
            (Telemetry.battery_level.isnot(None)) |
            (Telemetry.voltage.isnot(None)) |
            (Telemetry.metric_name.like("%Voltage"))  # INA sensor voltage channels
        )
        .order_by(Telemetry.received_at.asc())
    )
    rows = result.all()

    # Get node names for display
    node_result = await db.execute(select(Node))
    nodes = node_result.scalars().all()
    node_names: dict[int, str] = {}
    for node in nodes:
        if node.long_name:
            node_names[node.node_num] = node.long_name
        elif node.short_name:
            node_names[node.node_num] = node.short_name
        else:
            node_names[node.node_num] = f"!{node.node_num:08x}"

    # Group data by node_num and date
    # Structure: {node_num: {date: [{"time": datetime, "battery": val, "voltage": val, "ina_voltages": {}}]}}
    node_data: dict[int, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))

    for telemetry, source_name in rows:
        date_str = telemetry.received_at.strftime("%Y-%m-%d")

        # Extract INA voltage from metric_name pattern (ch1Voltage, ch2Voltage, ch3Voltage)
        ina_voltages: dict[str, float] = {}
        if telemetry.metric_name and telemetry.metric_name.endswith("Voltage") and telemetry.metric_name != "voltage":
            # This is an INA voltage channel (e.g., ch1Voltage, ch2Voltage, ch3Voltage)
            ina_voltages[telemetry.metric_name] = telemetry.raw_value

        node_data[telemetry.node_num][date_str].append({
            "time": telemetry.received_at,
            "battery": telemetry.battery_level,
            "voltage": telemetry.voltage,
            "ina_voltages": ina_voltages,
        })

    # Analyze each node's daily patterns
    solar_candidates = []

    # Global tracking for average hours calculations
    all_charging_hours = []  # Hours between sunrise and sunset (daylight/charging period)
    all_discharge_hours = []  # Hours between sunset and next sunrise (overnight/discharge period)

    for node_num, daily_data in node_data.items():
        # Track patterns independently for battery and voltage
        battery_stats = {
            "days_with_pattern": 0,
            "total_days": 0,
            "high_efficiency_days": 0,
            "daily_patterns": [],
            "charge_rates": [],
            "discharge_rates": [],
            "previous_day_sunset": None,
            "total_variance": 0,  # Sum of daily ranges to pick best metric
        }
        voltage_stats = {
            "days_with_pattern": 0,
            "total_days": 0,
            "high_efficiency_days": 0,
            "daily_patterns": [],
            "charge_rates": [],
            "discharge_rates": [],
            "previous_day_sunset": None,
            "total_variance": 0,
        }

        # Track INA voltage channels dynamically (ch1Voltage, ch2Voltage, ch3Voltage, etc.)
        ina_channel_stats: dict[str, dict] = {}

        # First pass: identify all INA channels present for this node
        ina_channels_seen: set[str] = set()
        for readings in daily_data.values():
            for r in readings:
                for channel_name in r.get("ina_voltages", {}).keys():
                    ina_channels_seen.add(channel_name)

        # Initialize stats for each INA channel
        for channel_name in ina_channels_seen:
            ina_channel_stats[channel_name] = {
                "days_with_pattern": 0,
                "total_days": 0,
                "high_efficiency_days": 0,
                "daily_patterns": [],
                "charge_rates": [],
                "discharge_rates": [],
                "previous_day_sunset": None,
                "total_variance": 0,
            }

        # Sort dates to process in chronological order for discharge calculation
        sorted_dates = sorted(daily_data.keys())

        for date_str in sorted_dates:
            readings = daily_data[date_str]
            if len(readings) < 3:  # Need at least 3 readings to detect a pattern
                continue

            # Sort by time
            readings.sort(key=lambda x: x["time"])

            # Separate battery, voltage, and INA voltage readings
            battery_values = []
            voltage_values = []
            ina_channel_values: dict[str, list[dict]] = {ch: [] for ch in ina_channels_seen}

            for r in readings:
                if r["battery"] is not None:
                    battery_values.append({"time": r["time"], "value": r["battery"]})
                if r["voltage"] is not None:
                    voltage_values.append({"time": r["time"], "value": r["voltage"]})
                # Collect INA voltage values
                for channel_name, value in r.get("ina_voltages", {}).items():
                    if value is not None:
                        ina_channel_values[channel_name].append({"time": r["time"], "value": value})

            # Analyze battery independently
            if len(battery_values) >= 3:
                battery_result = _analyze_metric_for_solar_patterns(
                    battery_values, is_battery=True, previous_day_sunset=battery_stats["previous_day_sunset"]
                )
                if battery_result:
                    battery_stats["days_with_pattern"] += 1
                    battery_stats["charge_rates"].append(battery_result["charge_rate"])
                    if battery_result["discharge_rate"] is not None:
                        battery_stats["discharge_rates"].append(battery_result["discharge_rate"])
                    if battery_result["daylight_hours"]:
                        all_charging_hours.append(battery_result["daylight_hours"])
                    if battery_result["discharge_hours"]:
                        all_discharge_hours.append(battery_result["discharge_hours"])
                    battery_stats["total_variance"] += battery_result["daily_range"]
                    if battery_result["is_high_efficiency"]:
                        battery_stats["high_efficiency_days"] += 1
                    battery_stats["daily_patterns"].append({
                        "date": date_str,
                        "sunrise": {
                            "time": battery_result["sunrise"]["time"].strftime("%H:%M"),
                            "value": round(battery_result["sunrise"]["value"], 1),
                        },
                        "peak": {
                            "time": battery_result["peak"]["time"].strftime("%H:%M"),
                            "value": round(battery_result["peak"]["value"], 1),
                        },
                        "sunset": {
                            "time": battery_result["sunset"]["time"].strftime("%H:%M"),
                            "value": round(battery_result["sunset"]["value"], 1),
                        },
                        "rise": round(battery_result["rise"], 1) if battery_result["rise"] is not None else None,
                        "fall": round(battery_result["fall"], 1) if battery_result["fall"] is not None else None,
                        "charge_rate_per_hour": round(battery_result["charge_rate"], 2) if battery_result["charge_rate"] is not None else None,
                        "discharge_rate_per_hour": round(battery_result["discharge_rate"], 2) if battery_result["discharge_rate"] is not None else None,
                    })
                    # Track sunset for next day's discharge calculation
                    battery_stats["previous_day_sunset"] = {
                        "time": battery_result["sunset"]["time"],
                        "value": battery_result["sunset"]["value"],
                    }
                    battery_stats["total_days"] += 1
                elif battery_values:
                    # Day analyzed but no pattern - still count for total_days if variance check passed
                    all_vals = [v["value"] for v in battery_values]
                    daily_range = max(all_vals) - min(all_vals)
                    if daily_range >= 2:  # Had enough variance to consider
                        battery_stats["total_days"] += 1

            # Analyze voltage independently
            if len(voltage_values) >= 3:
                voltage_result = _analyze_metric_for_solar_patterns(
                    voltage_values, is_battery=False, previous_day_sunset=voltage_stats["previous_day_sunset"]
                )
                if voltage_result:
                    voltage_stats["days_with_pattern"] += 1
                    voltage_stats["charge_rates"].append(voltage_result["charge_rate"])
                    if voltage_result["discharge_rate"] is not None:
                        voltage_stats["discharge_rates"].append(voltage_result["discharge_rate"])
                    if voltage_result["daylight_hours"]:
                        all_charging_hours.append(voltage_result["daylight_hours"])
                    if voltage_result["discharge_hours"]:
                        all_discharge_hours.append(voltage_result["discharge_hours"])
                    voltage_stats["total_variance"] += voltage_result["daily_range"]
                    if voltage_result["is_high_efficiency"]:
                        voltage_stats["high_efficiency_days"] += 1
                    voltage_stats["daily_patterns"].append({
                        "date": date_str,
                        "sunrise": {
                            "time": voltage_result["sunrise"]["time"].strftime("%H:%M"),
                            "value": round(voltage_result["sunrise"]["value"], 1),
                        },
                        "peak": {
                            "time": voltage_result["peak"]["time"].strftime("%H:%M"),
                            "value": round(voltage_result["peak"]["value"], 1),
                        },
                        "sunset": {
                            "time": voltage_result["sunset"]["time"].strftime("%H:%M"),
                            "value": round(voltage_result["sunset"]["value"], 1),
                        },
                        "rise": round(voltage_result["rise"], 1) if voltage_result["rise"] is not None else None,
                        "fall": round(voltage_result["fall"], 1) if voltage_result["fall"] is not None else None,
                        "charge_rate_per_hour": round(voltage_result["charge_rate"], 2) if voltage_result["charge_rate"] is not None else None,
                        "discharge_rate_per_hour": round(voltage_result["discharge_rate"], 2) if voltage_result["discharge_rate"] is not None else None,
                    })
                    # Track sunset for next day's discharge calculation
                    voltage_stats["previous_day_sunset"] = {
                        "time": voltage_result["sunset"]["time"],
                        "value": voltage_result["sunset"]["value"],
                    }
                    voltage_stats["total_days"] += 1
                elif voltage_values:
                    # Day analyzed but no pattern
                    all_vals = [v["value"] for v in voltage_values]
                    daily_range = max(all_vals) - min(all_vals)
                    if daily_range >= 0.05:  # Had enough variance to consider
                        voltage_stats["total_days"] += 1

            # Analyze each INA voltage channel independently
            for channel_name, channel_values in ina_channel_values.items():
                if len(channel_values) >= 3:
                    stats = ina_channel_stats[channel_name]
                    ina_result = _analyze_metric_for_solar_patterns(
                        channel_values, is_battery=False, previous_day_sunset=stats["previous_day_sunset"]
                    )
                    if ina_result:
                        stats["days_with_pattern"] += 1
                        stats["charge_rates"].append(ina_result["charge_rate"])
                        if ina_result["discharge_rate"] is not None:
                            stats["discharge_rates"].append(ina_result["discharge_rate"])
                        if ina_result["daylight_hours"]:
                            all_charging_hours.append(ina_result["daylight_hours"])
                        if ina_result["discharge_hours"]:
                            all_discharge_hours.append(ina_result["discharge_hours"])
                        stats["total_variance"] += ina_result["daily_range"]
                        if ina_result["is_high_efficiency"]:
                            stats["high_efficiency_days"] += 1
                        stats["daily_patterns"].append({
                            "date": date_str,
                            "sunrise": {
                                "time": ina_result["sunrise"]["time"].strftime("%H:%M"),
                                "value": round(ina_result["sunrise"]["value"], 3),
                            },
                            "peak": {
                                "time": ina_result["peak"]["time"].strftime("%H:%M"),
                                "value": round(ina_result["peak"]["value"], 3),
                            },
                            "sunset": {
                                "time": ina_result["sunset"]["time"].strftime("%H:%M"),
                                "value": round(ina_result["sunset"]["value"], 3),
                            },
                            "rise": round(ina_result["rise"], 3) if ina_result["rise"] is not None else None,
                            "fall": round(ina_result["fall"], 3) if ina_result["fall"] is not None else None,
                            "charge_rate_per_hour": round(ina_result["charge_rate"], 4) if ina_result["charge_rate"] is not None else None,
                            "discharge_rate_per_hour": round(ina_result["discharge_rate"], 4) if ina_result["discharge_rate"] is not None else None,
                        })
                        stats["previous_day_sunset"] = {
                            "time": ina_result["sunset"]["time"],
                            "value": ina_result["sunset"]["value"],
                        }
                        stats["total_days"] += 1
                    elif channel_values:
                        all_vals = [v["value"] for v in channel_values]
                        daily_range = max(all_vals) - min(all_vals)
                        if daily_range >= 0.01:  # INA sensors can have smaller variance
                            stats["total_days"] += 1

        # Determine if node is solar-powered based on ANY metric showing patterns
        # A node is solar if battery, voltage, OR any INA channel shows solar patterns
        battery_is_solar = False
        voltage_is_solar = False
        ina_channels_solar: dict[str, bool] = {}

        # Check battery
        if battery_stats["total_days"] >= 2:
            is_mostly_high_eff = battery_stats["high_efficiency_days"] > battery_stats["total_days"] * 0.5
            min_ratio = 0.33 if is_mostly_high_eff else 0.5
            if battery_stats["days_with_pattern"] / battery_stats["total_days"] >= min_ratio:
                battery_is_solar = True

        # Check voltage
        if voltage_stats["total_days"] >= 2:
            is_mostly_high_eff = voltage_stats["high_efficiency_days"] > voltage_stats["total_days"] * 0.5
            min_ratio = 0.33 if is_mostly_high_eff else 0.5
            if voltage_stats["days_with_pattern"] / voltage_stats["total_days"] >= min_ratio:
                voltage_is_solar = True

        # Check INA voltage channels
        for channel_name, stats in ina_channel_stats.items():
            if stats["total_days"] >= 2:
                is_mostly_high_eff = stats["high_efficiency_days"] > stats["total_days"] * 0.5
                min_ratio = 0.33 if is_mostly_high_eff else 0.5
                if stats["days_with_pattern"] / stats["total_days"] >= min_ratio:
                    ina_channels_solar[channel_name] = True

        # Node is solar if ANY metric shows patterns (battery, voltage, or INA channel)
        any_ina_solar = any(ina_channels_solar.values())
        if battery_is_solar or voltage_is_solar or any_ina_solar:
            # Choose the best metric for charting based on variance
            # Prefer the metric that shows more variation (avoids stuck-at-100% battery)
            # Consider battery, voltage, and INA channels
            chosen_stats = None
            metric_type = None
            best_variance = 0

            # Collect all solar metrics with their normalized variance
            metric_candidates = []
            if battery_is_solar:
                # Battery variance is already in % (0-100)
                metric_candidates.append(("battery", battery_stats, battery_stats["total_variance"]))
            if voltage_is_solar:
                # Normalize voltage variance: 0.3V swing ~ 10% battery swing
                normalized = voltage_stats["total_variance"] * (100 / 5)
                metric_candidates.append(("voltage", voltage_stats, normalized))
            for channel_name, is_solar in ina_channels_solar.items():
                if is_solar:
                    stats = ina_channel_stats[channel_name]
                    # Normalize INA voltage variance similar to device voltage
                    normalized = stats["total_variance"] * (100 / 5)
                    metric_candidates.append((channel_name, stats, normalized))

            # Pick the metric with highest normalized variance
            for name, stats, variance in metric_candidates:
                if variance > best_variance:
                    best_variance = variance
                    chosen_stats = stats
                    metric_type = name

            # Fallback to battery if no variance comparison possible
            if chosen_stats is None:
                if battery_is_solar:
                    chosen_stats = battery_stats
                    metric_type = "battery"
                elif voltage_is_solar:
                    chosen_stats = voltage_stats
                    metric_type = "voltage"
                elif ina_channels_solar:
                    # Pick first INA channel that's solar
                    for channel_name, is_solar in ina_channels_solar.items():
                        if is_solar:
                            chosen_stats = ina_channel_stats[channel_name]
                            metric_type = channel_name
                            break

            # Calculate solar score from the best metric
            total_days = chosen_stats["total_days"]
            days_with_pattern = chosen_stats["days_with_pattern"]
            solar_score = round((days_with_pattern / total_days) * 100, 1) if total_days > 0 else 0

            # Collect chart data for the chosen metric
            all_chart_data = []
            for date_str, readings in daily_data.items():
                for r in readings:
                    if metric_type == "battery":
                        value = r["battery"]
                    elif metric_type == "voltage":
                        value = r["voltage"]
                    else:
                        # INA channel - get from ina_voltages dict
                        value = r.get("ina_voltages", {}).get(metric_type)
                    if value is not None:
                        all_chart_data.append({
                            "timestamp": int(r["time"].timestamp() * 1000),
                            "value": round(value, 3),
                        })
            all_chart_data.sort(key=lambda x: x["timestamp"])

            # Calculate average rates from chosen metric (filter None values)
            charge_rates = [r for r in chosen_stats["charge_rates"] if r is not None]
            discharge_rates = [r for r in chosen_stats["discharge_rates"] if r is not None]
            avg_charge_rate = round(sum(charge_rates) / len(charge_rates), 2) if charge_rates else None
            avg_discharge_rate = round(sum(discharge_rates) / len(discharge_rates), 2) if discharge_rates else None

            # Indicate which metrics showed solar patterns
            metrics_detected = []
            if battery_is_solar:
                metrics_detected.append("battery")
            if voltage_is_solar:
                metrics_detected.append("voltage")
            # Add INA channels that showed patterns
            for channel_name, is_solar in ina_channels_solar.items():
                if is_solar:
                    metrics_detected.append(channel_name)

            solar_candidates.append({
                "node_num": node_num,
                "node_name": node_names.get(node_num, f"!{node_num:08x}"),
                "solar_score": solar_score,
                "days_analyzed": total_days,
                "days_with_pattern": days_with_pattern,
                "recent_patterns": chosen_stats["daily_patterns"][-3:],
                "metric_type": metric_type,
                "metrics_detected": metrics_detected,
                "chart_data": all_chart_data,
                "avg_charge_rate_per_hour": avg_charge_rate,
                "avg_discharge_rate_per_hour": avg_discharge_rate,
            })

    # Sort by solar score descending
    solar_candidates.sort(key=lambda x: x["solar_score"], reverse=True)

    # Fetch solar production data for the lookback period (for chart overlay)
    # Group by hour and average watt_hours across sources
    hour_trunc = func.date_trunc("hour", SolarProduction.timestamp)
    solar_result = await db.execute(
        select(
            hour_trunc.label("hour"),
            func.avg(SolarProduction.watt_hours).label("avg_watt_hours"),
        )
        .where(SolarProduction.timestamp >= cutoff)
        .group_by(literal_column("1"))
        .order_by(literal_column("1").asc())
    )
    solar_rows = solar_result.all()
    solar_chart_data = [
        {
            "timestamp": int(row.hour.timestamp() * 1000),
            "wattHours": round(row.avg_watt_hours, 2),
        }
        for row in solar_rows
    ]

    # Calculate global averages
    avg_charging_hours_per_day = round(sum(all_charging_hours) / len(all_charging_hours), 1) if all_charging_hours else None
    avg_discharge_hours_per_day = round(sum(all_discharge_hours) / len(all_discharge_hours), 1) if all_discharge_hours else None

    # Add insufficient_solar flag to each node
    # Formula: if (charge_rate * charging_hours) <= (discharge_rate * discharge_hours) * 1.1
    # This means the node isn't generating enough to keep up with its overnight discharge
    #
    # IMPORTANT: Nodes that regularly reach full charge (>= 98%) are considered to have
    # sufficient solar, even if their charge_rate appears low. When a battery is already
    # at 100%, it reports 0 charge rate since it can't charge further, which would
    # incorrectly flag it as insufficient.
    for node in solar_candidates:
        charge_rate = node.get("avg_charge_rate_per_hour")
        discharge_rate = node.get("avg_discharge_rate_per_hour")
        recent_patterns = node.get("recent_patterns", [])

        # Check if node regularly reaches full charge (peak >= 98%)
        # If most recent days show near-full battery, solar is sufficient
        if recent_patterns:
            peak_values = [p.get("peak", {}).get("value", 0) for p in recent_patterns]
            days_at_full = sum(1 for pv in peak_values if pv >= 98)
            # If majority of recent days reached full charge, solar is sufficient
            if days_at_full >= len(peak_values) / 2:
                node["insufficient_solar"] = False
                continue

        if charge_rate is not None and discharge_rate is not None and avg_charging_hours_per_day and avg_discharge_hours_per_day:
            total_charge = charge_rate * avg_charging_hours_per_day
            total_discharge = discharge_rate * avg_discharge_hours_per_day
            # Flag if charging doesn't exceed discharge by at least 10%
            node["insufficient_solar"] = total_charge <= (total_discharge * 1.1)
        else:
            node["insufficient_solar"] = None  # Unknown - insufficient data

    return {
        "lookback_days": lookback_days,
        "total_nodes_analyzed": len(node_data),
        "solar_nodes_count": len(solar_candidates),
        "solar_nodes": solar_candidates,
        "solar_production": solar_chart_data,
        "avg_charging_hours_per_day": avg_charging_hours_per_day,
        "avg_discharge_hours_per_day": avg_discharge_hours_per_day,
    }


@router.get("/analysis/solar-forecast")
async def analyze_solar_forecast(
    db: AsyncSession = Depends(get_db),
    lookback_days: int = Query(default=7, ge=1, le=90, description="Days of history to analyze"),
    _access: None = Depends(require_tab_access("analysis")),
) -> dict:
    """Analyze solar forecast and simulate node battery states.

    Compares forecast solar production to historical averages and simulates
    battery state for identified solar nodes to predict if they will drop
    below critical levels.

    Returns:
    - low_output_warning: True if forecast output is >25% below historical average
    - nodes_at_risk: List of nodes predicted to drop below 50% battery
    - forecast_vs_historical: Comparison data for display
    """
    from collections import defaultdict

    now = datetime.now(UTC)
    cutoff = now - timedelta(days=lookback_days)

    # Get historical solar production (past days, not including today's future)
    # First sum hourly values per source per day, then average across sources
    day_trunc = func.date_trunc("day", SolarProduction.timestamp)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Subquery: sum watt_hours per source per day
    source_daily_totals = (
        select(
            day_trunc.label("day"),
            SolarProduction.source_id,
            func.sum(SolarProduction.watt_hours).label("daily_wh"),
        )
        .where(SolarProduction.timestamp >= cutoff)
        .where(SolarProduction.timestamp < today_start)
        .group_by(day_trunc, SolarProduction.source_id)
        .subquery()
    )

    # Main query: average daily totals across sources
    historical_result = await db.execute(
        select(
            source_daily_totals.c.day,
            func.avg(source_daily_totals.c.daily_wh).label("avg_wh"),
        )
        .group_by(source_daily_totals.c.day)
        .order_by(source_daily_totals.c.day)
    )
    historical_rows = historical_result.all()

    # Get forecast solar production (today and future)
    # Subquery: sum watt_hours per source per day for forecast period
    forecast_source_daily = (
        select(
            day_trunc.label("day"),
            SolarProduction.source_id,
            func.sum(SolarProduction.watt_hours).label("daily_wh"),
        )
        .where(SolarProduction.timestamp >= today_start)
        .group_by(day_trunc, SolarProduction.source_id)
        .subquery()
    )

    # Main query: average daily totals across sources
    forecast_result = await db.execute(
        select(
            forecast_source_daily.c.day,
            func.avg(forecast_source_daily.c.daily_wh).label("avg_wh"),
        )
        .group_by(forecast_source_daily.c.day)
        .order_by(forecast_source_daily.c.day)
    )
    forecast_rows = forecast_result.all()

    # Calculate historical average daily output
    historical_daily_wh = [row.avg_wh for row in historical_rows if row.avg_wh]
    avg_historical_daily_wh = sum(historical_daily_wh) / len(historical_daily_wh) if historical_daily_wh else 0

    # Analyze forecast days - extend to 5 days into the future
    forecast_days = []
    low_output_warning = False

    # Create a dict of actual forecast data by date
    actual_forecast_by_date = {}
    for row in forecast_rows:
        actual_forecast_by_date[row.day.strftime("%Y-%m-%d")] = row.avg_wh or 0

    # Only generate forecast days for dates where we have actual solar forecast data
    # This limits the forecast to the data available from Forecast.Solar (typically today + 1 day)
    for day_offset in range(5):  # Check up to 5 days but only include those with data
        forecast_date = (today_start + timedelta(days=day_offset)).strftime("%Y-%m-%d")

        # Only include days where we have actual forecast data from Forecast.Solar
        if forecast_date not in actual_forecast_by_date:
            continue  # Skip days without actual solar forecast data

        forecast_wh = actual_forecast_by_date[forecast_date]
        pct_of_avg = (forecast_wh / avg_historical_daily_wh * 100) if avg_historical_daily_wh > 0 else 100
        is_low = pct_of_avg < 75  # Less than 75% of average = warning

        if is_low:
            low_output_warning = True

        forecast_days.append({
            "date": forecast_date,
            "forecast_wh": round(forecast_wh, 1),
            "avg_historical_wh": round(avg_historical_daily_wh, 1),
            "pct_of_average": round(pct_of_avg, 1),
            "is_low": is_low,
        })

    # Get the solar nodes analysis to simulate battery levels
    # First, get battery/voltage/INA telemetry for identified solar nodes
    telemetry_result = await db.execute(
        select(Telemetry, Source.name.label("source_name"))
        .join(Source)
        .where(Telemetry.received_at >= cutoff)
        .where(
            (Telemetry.battery_level.isnot(None)) |
            (Telemetry.voltage.isnot(None)) |
            (Telemetry.metric_name.like("%Voltage"))  # INA sensor voltage channels
        )
        .order_by(Telemetry.received_at.asc())
    )
    telemetry_rows = telemetry_result.all()

    # Get node names
    node_result = await db.execute(select(Node))
    nodes = node_result.scalars().all()
    node_names: dict[int, str] = {}
    for node in nodes:
        if node.long_name:
            node_names[node.node_num] = node.long_name
        elif node.short_name:
            node_names[node.node_num] = node.short_name
        else:
            node_names[node.node_num] = f"!{node.node_num:08x}"

    # Group telemetry by node and date to identify solar nodes and their patterns
    node_data: dict[int, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))

    for telemetry, source_name in telemetry_rows:
        date_str = telemetry.received_at.strftime("%Y-%m-%d")

        # Extract INA voltage from metric_name pattern (ch1Voltage, ch2Voltage, ch3Voltage)
        ina_voltages: dict[str, float] = {}
        if telemetry.metric_name and telemetry.metric_name.endswith("Voltage") and telemetry.metric_name != "voltage":
            ina_voltages[telemetry.metric_name] = telemetry.raw_value

        node_data[telemetry.node_num][date_str].append({
            "time": telemetry.received_at,
            "battery": telemetry.battery_level,
            "voltage": telemetry.voltage,
            "ina_voltages": ina_voltages,
        })

    # Track nodes at risk based on forecast
    nodes_at_risk = []
    # Track simulation for all solar nodes (not just at-risk)
    all_solar_simulations = []

    # Global tracking for average hours calculations
    all_charging_hours = []
    all_discharge_hours = []

    # Analyze each node's daily patterns (similar to solar-nodes endpoint)
    for node_num, daily_data in node_data.items():
        # Track patterns independently for battery and voltage
        battery_stats = {
            "days_with_pattern": 0,
            "total_days": 0,
            "high_efficiency_days": 0,
            "charge_rates": [],
            "discharge_rates": [],
            "previous_day_sunset": None,
            "total_variance": 0,
        }
        voltage_stats = {
            "days_with_pattern": 0,
            "total_days": 0,
            "high_efficiency_days": 0,
            "charge_rates": [],
            "discharge_rates": [],
            "previous_day_sunset": None,
            "total_variance": 0,
        }

        # Track INA voltage channels dynamically
        ina_channel_stats: dict[str, dict] = {}
        ina_channels_seen: set[str] = set()
        for readings in daily_data.values():
            for r in readings:
                for channel_name in r.get("ina_voltages", {}).keys():
                    ina_channels_seen.add(channel_name)
        for channel_name in ina_channels_seen:
            ina_channel_stats[channel_name] = {
                "days_with_pattern": 0,
                "total_days": 0,
                "high_efficiency_days": 0,
                "charge_rates": [],
                "discharge_rates": [],
                "previous_day_sunset": None,
                "total_variance": 0,
            }

        # Track last known battery level (independent of pattern detection)
        last_known_battery = None

        sorted_dates = sorted(daily_data.keys())

        for date_str in sorted_dates:
            readings = daily_data[date_str]
            if len(readings) < 3:
                continue

            readings.sort(key=lambda x: x["time"])

            # Separate battery, voltage, and INA voltage readings
            battery_values = []
            voltage_values = []
            ina_channel_values: dict[str, list[dict]] = {ch: [] for ch in ina_channels_seen}

            for r in readings:
                if r["battery"] is not None:
                    battery_values.append({"time": r["time"], "value": r["battery"]})
                    # Always track last known battery level
                    last_known_battery = r["battery"]
                if r["voltage"] is not None:
                    voltage_values.append({"time": r["time"], "value": r["voltage"]})
                # Collect INA voltage values
                for channel_name, value in r.get("ina_voltages", {}).items():
                    if value is not None:
                        ina_channel_values[channel_name].append({"time": r["time"], "value": value})

            # Analyze battery independently
            if len(battery_values) >= 3:
                battery_result = _analyze_metric_for_solar_patterns(
                    battery_values, is_battery=True, previous_day_sunset=battery_stats["previous_day_sunset"]
                )
                if battery_result:
                    battery_stats["days_with_pattern"] += 1
                    battery_stats["charge_rates"].append(battery_result["charge_rate"])
                    if battery_result["discharge_rate"] is not None:
                        battery_stats["discharge_rates"].append(battery_result["discharge_rate"])
                    if battery_result["daylight_hours"]:
                        all_charging_hours.append(battery_result["daylight_hours"])
                    if battery_result["discharge_hours"]:
                        all_discharge_hours.append(battery_result["discharge_hours"])
                    battery_stats["total_variance"] += battery_result["daily_range"]
                    if battery_result["is_high_efficiency"]:
                        battery_stats["high_efficiency_days"] += 1
                    battery_stats["previous_day_sunset"] = {
                        "time": battery_result["sunset"]["time"],
                        "value": battery_result["sunset"]["value"],
                    }
                    battery_stats["total_days"] += 1
                elif battery_values:
                    all_vals = [v["value"] for v in battery_values]
                    daily_range = max(all_vals) - min(all_vals)
                    if daily_range >= 2:
                        battery_stats["total_days"] += 1

            # Analyze voltage independently
            if len(voltage_values) >= 3:
                voltage_result = _analyze_metric_for_solar_patterns(
                    voltage_values, is_battery=False, previous_day_sunset=voltage_stats["previous_day_sunset"]
                )
                if voltage_result:
                    voltage_stats["days_with_pattern"] += 1
                    voltage_stats["charge_rates"].append(voltage_result["charge_rate"])
                    if voltage_result["discharge_rate"] is not None:
                        voltage_stats["discharge_rates"].append(voltage_result["discharge_rate"])
                    if voltage_result["daylight_hours"]:
                        all_charging_hours.append(voltage_result["daylight_hours"])
                    if voltage_result["discharge_hours"]:
                        all_discharge_hours.append(voltage_result["discharge_hours"])
                    voltage_stats["total_variance"] += voltage_result["daily_range"]
                    if voltage_result["is_high_efficiency"]:
                        voltage_stats["high_efficiency_days"] += 1
                    voltage_stats["previous_day_sunset"] = {
                        "time": voltage_result["sunset"]["time"],
                        "value": voltage_result["sunset"]["value"],
                    }
                    voltage_stats["total_days"] += 1
                elif voltage_values:
                    all_vals = [v["value"] for v in voltage_values]
                    daily_range = max(all_vals) - min(all_vals)
                    if daily_range >= 0.05:
                        voltage_stats["total_days"] += 1

            # Analyze each INA voltage channel independently
            for channel_name, channel_values in ina_channel_values.items():
                if len(channel_values) >= 3:
                    stats = ina_channel_stats[channel_name]
                    ina_result = _analyze_metric_for_solar_patterns(
                        channel_values, is_battery=False, previous_day_sunset=stats["previous_day_sunset"]
                    )
                    if ina_result:
                        stats["days_with_pattern"] += 1
                        stats["charge_rates"].append(ina_result["charge_rate"])
                        if ina_result["discharge_rate"] is not None:
                            stats["discharge_rates"].append(ina_result["discharge_rate"])
                        if ina_result["daylight_hours"]:
                            all_charging_hours.append(ina_result["daylight_hours"])
                        if ina_result["discharge_hours"]:
                            all_discharge_hours.append(ina_result["discharge_hours"])
                        stats["total_variance"] += ina_result["daily_range"]
                        if ina_result["is_high_efficiency"]:
                            stats["high_efficiency_days"] += 1
                        stats["previous_day_sunset"] = {
                            "time": ina_result["sunset"]["time"],
                            "value": ina_result["sunset"]["value"],
                        }
                        stats["total_days"] += 1
                    elif channel_values:
                        all_vals = [v["value"] for v in channel_values]
                        daily_range = max(all_vals) - min(all_vals)
                        if daily_range >= 0.01:
                            stats["total_days"] += 1

        # Determine if node is solar-powered based on ANY metric showing patterns
        battery_is_solar = False
        voltage_is_solar = False
        ina_channels_solar: dict[str, bool] = {}

        if battery_stats["total_days"] >= 2:
            is_mostly_high_eff = battery_stats["high_efficiency_days"] > battery_stats["total_days"] * 0.5
            min_ratio = 0.33 if is_mostly_high_eff else 0.5
            if battery_stats["days_with_pattern"] / battery_stats["total_days"] >= min_ratio:
                battery_is_solar = True

        if voltage_stats["total_days"] >= 2:
            is_mostly_high_eff = voltage_stats["high_efficiency_days"] > voltage_stats["total_days"] * 0.5
            min_ratio = 0.33 if is_mostly_high_eff else 0.5
            if voltage_stats["days_with_pattern"] / voltage_stats["total_days"] >= min_ratio:
                voltage_is_solar = True

        # Check INA voltage channels
        for channel_name, stats in ina_channel_stats.items():
            if stats["total_days"] >= 2:
                is_mostly_high_eff = stats["high_efficiency_days"] > stats["total_days"] * 0.5
                min_ratio = 0.33 if is_mostly_high_eff else 0.5
                if stats["days_with_pattern"] / stats["total_days"] >= min_ratio:
                    ina_channels_solar[channel_name] = True

        # Node is solar if ANY metric shows patterns
        any_ina_solar = any(ina_channels_solar.values())
        if (battery_is_solar or voltage_is_solar or any_ina_solar) and last_known_battery is not None:
            # Choose which metric's rates to use for simulation
            # Consider battery, voltage, and INA channels - pick the one with best variance
            chosen_stats = None
            best_variance = 0

            # Collect all solar metrics with their normalized variance
            metric_candidates = []
            if battery_is_solar:
                metric_candidates.append(("battery", battery_stats, battery_stats["total_variance"]))
            if voltage_is_solar:
                normalized = voltage_stats["total_variance"] * (100 / 5)
                metric_candidates.append(("voltage", voltage_stats, normalized))
            for channel_name, is_solar in ina_channels_solar.items():
                if is_solar:
                    stats = ina_channel_stats[channel_name]
                    normalized = stats["total_variance"] * (100 / 5)
                    metric_candidates.append((channel_name, stats, normalized))

            # Pick the metric with highest normalized variance
            chosen_metric_type = None
            for name, stats, variance in metric_candidates:
                if variance > best_variance:
                    best_variance = variance
                    chosen_stats = stats
                    chosen_metric_type = name

            # Fallback
            if chosen_stats is None:
                if battery_is_solar:
                    chosen_stats = battery_stats
                    chosen_metric_type = "battery"
                elif voltage_is_solar:
                    chosen_stats = voltage_stats
                    chosen_metric_type = "voltage"
                elif ina_channels_solar:
                    for channel_name, is_solar in ina_channels_solar.items():
                        if is_solar:
                            chosen_stats = ina_channel_stats[channel_name]
                            chosen_metric_type = channel_name
                            break

            charge_rates = [r for r in (chosen_stats["charge_rates"] if chosen_stats else []) if r is not None]
            discharge_rates = [r for r in (chosen_stats["discharge_rates"] if chosen_stats else []) if r is not None]
            avg_charge_rate = sum(charge_rates) / len(charge_rates) if charge_rates else 0
            avg_discharge_rate = sum(discharge_rates) / len(discharge_rates) if discharge_rates else 0
            valid_charging_hours = [h for h in all_charging_hours if h is not None]
            valid_discharge_hours = [h for h in all_discharge_hours if h is not None]
            avg_charging_hours = sum(valid_charging_hours) / len(valid_charging_hours) if valid_charging_hours else 10
            avg_discharge_hours = sum(valid_discharge_hours) / len(valid_discharge_hours) if valid_discharge_hours else 14

            # Simulate using battery level (we always need battery for the simulation)
            if last_known_battery is not None:
                # Simulate battery level for forecast period
                simulated_battery = last_known_battery
                min_simulated = last_known_battery
                forecast_simulation = []

                # Add a "now" point as the starting point for the forecast
                forecast_simulation.append({
                    "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "simulated_battery": round(last_known_battery, 1),
                    "phase": "current",
                    "forecast_factor": 1.0,
                })

                for day_idx, day_forecast in enumerate(forecast_days):
                    # Adjust charge rate based on forecast solar output
                    forecast_factor = day_forecast["pct_of_average"] / 100 if day_forecast["pct_of_average"] > 0 else 0.5
                    effective_charge_rate = avg_charge_rate * forecast_factor
                    day_date = day_forecast["date"]

                    # Parse the day date for time comparisons
                    day_start = datetime.strptime(day_date, "%Y-%m-%d").replace(tzinfo=UTC)
                    sunrise_time = day_start.replace(hour=12)  # 12:00 UTC = ~7am EST
                    peak_time = day_start.replace(hour=19)     # 19:00 UTC = ~2pm EST
                    sunset_time = day_start.replace(hour=23)   # 23:00 UTC = ~6pm EST

                    # For the first day (today), only add points that are in the future
                    is_first_day = day_idx == 0

                    # Point 1: Sunrise (~7am) - battery level after overnight discharge
                    if not is_first_day or sunrise_time > now:
                        # Only apply full overnight discharge for future days
                        if not is_first_day:
                            simulated_battery -= avg_discharge_rate * avg_discharge_hours
                        else:
                            # For today, calculate hours until sunrise if it's in the future
                            hours_until_sunrise = (sunrise_time - now).total_seconds() / 3600
                            if hours_until_sunrise > 0:
                                simulated_battery -= avg_discharge_rate * hours_until_sunrise
                        simulated_battery = max(0, min(100, simulated_battery))
                        sunrise_battery = simulated_battery
                        min_simulated = min(min_simulated, sunrise_battery)
                        forecast_simulation.append({
                            "timestamp": f"{day_date}T12:00:00Z",
                            "simulated_battery": round(sunrise_battery, 1),
                            "phase": "sunrise",
                            "forecast_factor": round(forecast_factor, 2),
                        })

                    # Point 2: Peak (~2pm) - battery level at max charge
                    if not is_first_day or peak_time > now:
                        if is_first_day and sunrise_time <= now < peak_time:
                            # Currently in charging phase - calculate partial charge
                            hours_charging = (peak_time - now).total_seconds() / 3600
                            simulated_battery += effective_charge_rate * hours_charging
                        elif not is_first_day or sunrise_time > now:
                            # Full charging phase
                            simulated_battery += effective_charge_rate * avg_charging_hours
                        simulated_battery = max(0, min(100, simulated_battery))
                        peak_battery = simulated_battery
                        forecast_simulation.append({
                            "timestamp": f"{day_date}T19:00:00Z",
                            "simulated_battery": round(peak_battery, 1),
                            "phase": "peak",
                            "forecast_factor": round(forecast_factor, 2),
                        })

                    # Point 3: Sunset (~6pm) - battery level when discharging starts
                    if not is_first_day or sunset_time > now:
                        # Slight discharge during afternoon (2pm-6pm is ~4 hours of lower efficiency)
                        afternoon_hours = 4
                        if is_first_day and peak_time <= now < sunset_time:
                            # Currently in afternoon discharge
                            hours_remaining = (sunset_time - now).total_seconds() / 3600
                            simulated_battery -= avg_discharge_rate * hours_remaining * 0.3
                        else:
                            simulated_battery -= avg_discharge_rate * afternoon_hours * 0.3
                        simulated_battery = max(0, min(100, simulated_battery))
                        sunset_battery = simulated_battery
                        forecast_simulation.append({
                            "timestamp": f"{day_date}T23:00:00Z",
                            "simulated_battery": round(sunset_battery, 1),
                            "phase": "sunset",
                            "forecast_factor": round(forecast_factor, 2),
                        })

                # Add to all solar simulations list (for chart display)
                # At-risk threshold only applies to battery-based nodes (40%)
                at_risk_threshold = 40 if chosen_metric_type == "battery" else None
                all_solar_simulations.append({
                    "node_num": node_num,
                    "node_name": node_names.get(node_num, f"!{node_num:08x}"),
                    "current_battery": round(last_known_battery, 1),
                    "min_simulated_battery": round(min_simulated, 1),
                    "avg_charge_rate_per_hour": round(avg_charge_rate, 2),
                    "avg_discharge_rate_per_hour": round(avg_discharge_rate, 2),
                    "simulation": forecast_simulation,
                    "metric_type": chosen_metric_type,
                    "at_risk_threshold": at_risk_threshold,
                })

                # Flag if simulation shows battery dropping below 40% threshold
                # Only applies to battery-based nodes since simulation uses battery percentage
                # Voltage/INA nodes are excluded because their chart shows voltage but simulation uses battery %
                if chosen_metric_type == "battery" and min_simulated < 40:
                    nodes_at_risk.append({
                        "node_num": node_num,
                        "node_name": node_names.get(node_num, f"!{node_num:08x}"),
                        "current_battery": round(last_known_battery, 1),
                        "min_simulated_battery": round(min_simulated, 1),
                        "avg_charge_rate_per_hour": round(avg_charge_rate, 2),
                        "avg_discharge_rate_per_hour": round(avg_discharge_rate, 2),
                        "simulation": forecast_simulation,
                        "metric_type": "battery",
                        "at_risk_threshold": 40,
                    })

    # Sort nodes at risk by minimum simulated battery (lowest first)
    nodes_at_risk.sort(key=lambda x: x["min_simulated_battery"])

    return {
        "lookback_days": lookback_days,
        "historical_days_analyzed": len(historical_daily_wh),
        "avg_historical_daily_wh": round(avg_historical_daily_wh, 1),
        "low_output_warning": low_output_warning,
        "forecast_days": forecast_days,
        "nodes_at_risk_count": len(nodes_at_risk),
        "nodes_at_risk": nodes_at_risk,
        "solar_simulations": all_solar_simulations,
    }


@router.get("/solar")
async def get_solar_averages(
    db: AsyncSession = Depends(get_db),
    hours: int = Query(default=168, ge=1, le=8760, description="Hours of history to fetch"),
    _access: None = Depends(require_tab_access("analysis")),
) -> list[dict]:
    """Get averaged solar production data across all sources.

    Groups solar production data by timestamp (hourly buckets) and averages
    watt_hours across all sources that have data for each time point.

    Returns data suitable for rendering a solar background on telemetry charts.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    # Query to group by timestamp and average watt_hours across sources
    result = await db.execute(
        select(
            SolarProduction.timestamp,
            func.avg(SolarProduction.watt_hours).label("avg_watt_hours"),
            func.count(SolarProduction.source_id).label("source_count"),
        )
        .where(SolarProduction.timestamp >= cutoff)
        .group_by(SolarProduction.timestamp)
        .order_by(SolarProduction.timestamp.asc())
    )
    rows = result.all()

    return [
        {
            "timestamp": int(row.timestamp.timestamp() * 1000),  # milliseconds for JS
            "wattHours": round(row.avg_watt_hours, 2),
            "sourceCount": row.source_count,
        }
        for row in rows
    ]


# Solar schedule settings key
SOLAR_SCHEDULE_KEY = "solar_analysis.schedule"


@router.get("/settings/solar-schedule")
async def get_solar_schedule_settings(
    db: AsyncSession = Depends(get_db),
    _access: None = Depends(require_tab_access("analysis")),
) -> dict:
    """Get solar analysis schedule settings."""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == SOLAR_SCHEDULE_KEY)
    )
    setting = result.scalar_one_or_none()

    if not setting:
        return {
            "enabled": False,
            "schedules": [],
            "apprise_urls": [],
            "lookback_days": 7,
        }
    return setting.value


@router.put("/settings/solar-schedule")
async def update_solar_schedule_settings(
    settings: dict,
    db: AsyncSession = Depends(get_db),
    _access: None = Depends(require_tab_access("analysis", "write")),
) -> dict:
    """Update solar analysis schedule settings.

    Settings schema:
    - enabled: bool - Whether scheduled analysis is enabled
    - schedules: list[str] - List of times in "HH:MM" format
    - apprise_urls: list[str] - List of Apprise notification URLs
    - lookback_days: int - Days of history to analyze (1-90)
    """
    # Validate and sanitize settings
    validated = {
        "enabled": bool(settings.get("enabled", False)),
        "schedules": [],
        "apprise_urls": [],
        "lookback_days": min(max(int(settings.get("lookback_days", 7)), 1), 90),
    }

    # Validate schedule times (HH:MM format)
    for time_str in settings.get("schedules", []):
        if isinstance(time_str, str) and len(time_str) == 5:
            try:
                hours, minutes = time_str.split(":")
                if 0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59:
                    validated["schedules"].append(time_str)
            except (ValueError, AttributeError):
                pass  # Skip invalid times

    # Validate Apprise URLs (basic validation - just check they're non-empty strings)
    for url in settings.get("apprise_urls", []):
        if isinstance(url, str) and url.strip():
            validated["apprise_urls"].append(url.strip())

    # Update or create setting
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == SOLAR_SCHEDULE_KEY)
    )
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = validated
    else:
        db.add(SystemSetting(key=SOLAR_SCHEDULE_KEY, value=validated))

    await db.commit()
    return validated


@router.post("/settings/solar-schedule/test")
async def test_solar_notification(
    db: AsyncSession = Depends(get_db),
    _access: None = Depends(require_tab_access("analysis", "write")),
) -> dict:
    """Send a test notification with current solar analysis.

    Uses the current schedule settings to send a test notification.
    Returns success status and any error message.
    """
    from app.services.scheduler import scheduler_service

    # Get current settings
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == SOLAR_SCHEDULE_KEY)
    )
    setting = result.scalar_one_or_none()

    if not setting or not setting.value.get("apprise_urls"):
        raise HTTPException(
            status_code=400,
            detail="No Apprise URLs configured. Add at least one notification URL first.",
        )

    # Run test notification
    test_result = await scheduler_service.run_test_notification(setting.value)

    if not test_result["success"]:
        raise HTTPException(
            status_code=500,
            detail=f"Notification failed: {test_result.get('error', 'Unknown error')}",
        )

    return {"success": True, "message": "Test notification sent successfully"}


@router.get("/analysis/message-utilization")
async def analyze_message_utilization(
    db: AsyncSession = Depends(get_db),
    lookback_days: int = Query(default=7, ge=1, le=90, description="Days of history to analyze"),
    include_text: bool = Query(default=True, description="Include text messages"),
    include_device: bool = Query(default=True, description="Include device telemetry"),
    include_environment: bool = Query(default=True, description="Include environment telemetry"),
    include_power: bool = Query(default=True, description="Include power telemetry"),
    include_position: bool = Query(default=True, description="Include position telemetry"),
    include_air_quality: bool = Query(default=True, description="Include air quality telemetry"),
    include_traceroute: bool = Query(default=True, description="Include traceroute packets"),
    include_nodeinfo: bool = Query(default=True, description="Include nodeinfo packets"),
    include_encrypted: bool = Query(default=True, description="Include encrypted/undecryptable packets"),
    include_unknown: bool = Query(default=True, description="Include unknown portnum packets"),
    exclude_local_nodes: bool = Query(default=False, description="Exclude telemetry from nodes directly connected to sources (hops_away=0)"),
    _access: None = Depends(require_tab_access("analysis")),
) -> dict:
    """Analyze message utilization across the mesh network.

    Returns:
    - top_nodes: Top 10 nodes by message count
    - hourly_histogram: Message count by hour of day (0-23)
    - type_breakdown: Message count by type
    - total_messages: Total message count
    """
    from collections import defaultdict

    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)

    # Get node names for display and identify local nodes
    node_result = await db.execute(select(Node))
    nodes = node_result.scalars().all()
    node_names: dict[int, str] = {}
    # Track local nodes: set of (source_id, node_num) tuples for nodes with hops_away == 0
    local_nodes: set[tuple[str, int]] = set()
    for node in nodes:
        if node.long_name:
            node_names[node.node_num] = node.long_name
        elif node.short_name:
            node_names[node.node_num] = node.short_name
        else:
            node_names[node.node_num] = f"!{node.node_num:08x}"
        # Track locally connected nodes (hops_away == 0 or NULL)
        # NULL typically means the node is the local node (source's own node)
        if node.hops_away is None or node.hops_away == 0:
            local_nodes.add((node.source_id, node.node_num))

    # Build lookup of local node numbers per MeshMonitor source
    source_result = await db.execute(
        select(Source).where(Source.type == SourceType.MESHMONITOR)
    )
    meshmonitor_source_ids = {s.id for s in source_result.scalars().all()}

    meshmonitor_local_nodes: dict[str, set[int]] = defaultdict(set)
    for source_id, node_num in local_nodes:
        if source_id in meshmonitor_source_ids:
            meshmonitor_local_nodes[source_id].add(node_num)

    # Track counts
    node_counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    hourly_counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    type_totals: dict[str, int] = defaultdict(int)

    def _record(from_node: int, type_key: str, hour: int) -> None:
        """Record a counted packet in all tracking dicts."""
        node_counts[from_node][type_key] += 1
        hourly_counts[hour][type_key] += 1
        type_totals[type_key] += 1

    # Query text messages if enabled
    if include_text:
        msg_result = await db.execute(
            select(Message)
            .where(Message.received_at >= cutoff)
        )
        messages = msg_result.scalars().all()

        seen_msgs: set[tuple] = set()
        for msg in messages:
            # Always exclude MeshMonitor internal messages (never traverse the mesh)
            if msg.source_id in meshmonitor_local_nodes:
                local_nums = meshmonitor_local_nodes[msg.source_id]
                if msg.from_node_num in local_nums and msg.to_node_num in local_nums:
                    continue
            # Skip messages from locally connected nodes if flag is set
            if exclude_local_nodes and (msg.source_id, msg.from_node_num) in local_nodes:
                continue
            # Dedup: same packet seen via multiple sources
            dedup_key = (msg.from_node_num, msg.meshtastic_id)
            if msg.meshtastic_id is not None and dedup_key in seen_msgs:
                continue
            seen_msgs.add(dedup_key)
            _record(msg.from_node_num, "text", msg.received_at.hour)

    # Build telemetry type filters
    telemetry_types = []
    if include_device:
        telemetry_types.append(TelemetryType.DEVICE)
    if include_environment:
        telemetry_types.append(TelemetryType.ENVIRONMENT)
    if include_power:
        telemetry_types.append(TelemetryType.POWER)
    if include_position:
        telemetry_types.append(TelemetryType.POSITION)
    if include_air_quality:
        telemetry_types.append(TelemetryType.AIR_QUALITY)

    # Query telemetry if any types are enabled
    if telemetry_types:
        telemetry_result = await db.execute(
            select(Telemetry)
            .where(Telemetry.received_at >= cutoff)
            .where(Telemetry.telemetry_type.in_(telemetry_types))
        )
        telemetry_rows = telemetry_result.scalars().all()

        seen_telemetry: set[tuple] = set()
        for t in telemetry_rows:
            # Skip telemetry from locally connected nodes if flag is set
            if exclude_local_nodes and (t.source_id, t.node_num) in local_nodes:
                continue
            # Dedup: prefer meshtastic_id, fall back to timestamp-based key.
            # Use telemetry_type (not metric_name) because one packet produces
            # multiple metric rows — we want to count packets, not metrics.
            if t.meshtastic_id is not None:
                dedup_key = (t.node_num, t.meshtastic_id)
            else:
                dedup_key = (t.node_num, t.telemetry_type, t.received_at)
            if dedup_key in seen_telemetry:
                continue
            seen_telemetry.add(dedup_key)
            _record(t.node_num, t.telemetry_type.value, t.received_at.hour)

    # Query traceroutes if enabled
    if include_traceroute:
        traceroute_result = await db.execute(
            select(Traceroute).where(Traceroute.received_at >= cutoff)
        )
        traceroute_rows = traceroute_result.scalars().all()

        seen_traceroutes: set[tuple] = set()
        for tr in traceroute_rows:
            # Exclude MeshMonitor internal traceroutes (both nodes local)
            if tr.source_id in meshmonitor_local_nodes:
                local_nums = meshmonitor_local_nodes[tr.source_id]
                if tr.from_node_num in local_nums and tr.to_node_num in local_nums:
                    continue
            if exclude_local_nodes and (tr.source_id, tr.from_node_num) in local_nodes:
                continue
            # Dedup: prefer meshtastic_id, fall back to timestamp-based key
            if tr.meshtastic_id is not None:
                dedup_key = (tr.from_node_num, tr.meshtastic_id)
            else:
                dedup_key = (tr.from_node_num, tr.to_node_num, tr.received_at)
            if dedup_key in seen_traceroutes:
                continue
            seen_traceroutes.add(dedup_key)
            _record(tr.from_node_num, "traceroute", tr.received_at.hour)

    # Query packet records (encrypted, unknown, nodeinfo) if any are enabled
    packet_record_types = []
    if include_nodeinfo:
        packet_record_types.append(PacketRecordType.NODEINFO)
    if include_encrypted:
        packet_record_types.append(PacketRecordType.ENCRYPTED)
    if include_unknown:
        packet_record_types.append(PacketRecordType.UNKNOWN)

    if packet_record_types:
        pr_result = await db.execute(
            select(PacketRecord)
            .where(PacketRecord.received_at >= cutoff)
            .where(PacketRecord.packet_type.in_(packet_record_types))
        )
        pr_rows = pr_result.scalars().all()

        seen_packets: set[tuple] = set()
        for pr in pr_rows:
            # Exclude MeshMonitor internal packets (both nodes local) — only if to_node is set
            if pr.to_node_num is not None and pr.source_id in meshmonitor_local_nodes:
                local_nums = meshmonitor_local_nodes[pr.source_id]
                if pr.from_node_num in local_nums and pr.to_node_num in local_nums:
                    continue
            if exclude_local_nodes and (pr.source_id, pr.from_node_num) in local_nodes:
                continue
            # Dedup: prefer meshtastic_id, fall back to timestamp-based key
            if pr.meshtastic_id is not None:
                dedup_key = (pr.from_node_num, pr.meshtastic_id)
            else:
                dedup_key = (pr.from_node_num, pr.packet_type, pr.received_at)
            if dedup_key in seen_packets:
                continue
            seen_packets.add(dedup_key)
            _record(pr.from_node_num, pr.packet_type.value, pr.received_at.hour)

    # Calculate top 10 nodes by total message count
    node_totals = []
    for node_num, type_counts in node_counts.items():
        total = sum(type_counts.values())
        node_totals.append({
            "node_num": node_num,
            "node_name": node_names.get(node_num, f"!{node_num:08x}"),
            "total": total,
            "breakdown": dict(type_counts),
        })

    node_totals.sort(key=lambda x: x["total"], reverse=True)
    top_nodes = node_totals[:10]

    # Build hourly histogram
    hourly_histogram = []
    for hour in range(24):
        type_counts = hourly_counts.get(hour, {})
        hourly_histogram.append({
            "hour": hour,
            "total": sum(type_counts.values()),
            "breakdown": dict(type_counts),
        })

    # Calculate total messages
    total_messages = sum(type_totals.values())

    return {
        "lookback_days": lookback_days,
        "total_messages": total_messages,
        "total_nodes": len(node_counts),
        "type_breakdown": dict(type_totals),
        "top_nodes": top_nodes,
        "hourly_histogram": hourly_histogram,
        "filters": {
            "text": include_text,
            "device": include_device,
            "environment": include_environment,
            "power": include_power,
            "position": include_position,
            "air_quality": include_air_quality,
            "traceroute": include_traceroute,
            "nodeinfo": include_nodeinfo,
            "encrypted": include_encrypted,
            "unknown": include_unknown,
            "exclude_local_nodes": exclude_local_nodes,
        },
        "local_nodes_excluded": len(local_nodes) if exclude_local_nodes else 0,
    }
