"""UI data endpoints (internal use for frontend)."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Node, SolarProduction, Source, Telemetry, Traceroute
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


@router.get("/analysis/solar-nodes")
async def identify_solar_nodes(
    db: AsyncSession = Depends(get_db),
    lookback_days: int = Query(default=7, ge=1, le=90, description="Days of history to analyze"),
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

    # Fetch all battery_level and voltage telemetry for the period
    result = await db.execute(
        select(Telemetry, Source.name.label("source_name"))
        .join(Source)
        .where(Telemetry.received_at >= cutoff)
        .where(
            (Telemetry.battery_level.isnot(None)) | (Telemetry.voltage.isnot(None))
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
    # Structure: {node_num: {date: [{"time": datetime, "battery": val, "voltage": val}]}}
    node_data: dict[int, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))

    for telemetry, source_name in rows:
        date_str = telemetry.received_at.strftime("%Y-%m-%d")
        node_data[telemetry.node_num][date_str].append({
            "time": telemetry.received_at,
            "battery": telemetry.battery_level,
            "voltage": telemetry.voltage,
        })

    # Analyze each node's daily patterns
    solar_candidates = []

    for node_num, daily_data in node_data.items():
        days_with_pattern = 0
        total_days = 0
        daily_patterns = []

        for date_str, readings in daily_data.items():
            if len(readings) < 3:  # Need at least 3 readings to detect a pattern
                continue

            total_days += 1

            # Sort by time
            readings.sort(key=lambda x: x["time"])

            # Separate battery and voltage readings to avoid mixing scales
            battery_values = []
            voltage_values = []
            for r in readings:
                if r["battery"] is not None:
                    battery_values.append({"time": r["time"], "value": r["battery"]})
                if r["voltage"] is not None:
                    voltage_values.append({"time": r["time"], "value": r["voltage"]})

            # Prefer battery readings if we have enough, otherwise use voltage
            # Don't mix the two as they're on different scales
            if len(battery_values) >= 3:
                values = battery_values
                min_variance = 10  # Battery: require at least 10% swing
            elif len(voltage_values) >= 3:
                values = voltage_values
                min_variance = 0.3  # Voltage: require at least 0.3V swing
            else:
                continue

            # Calculate daily variance - nodes on wall power have near-constant values
            all_values = [v["value"] for v in values]
            min_value = min(all_values)
            max_value = max(all_values)
            daily_range = max_value - min_value
            if daily_range < min_variance:
                continue

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

            # Check for solar pattern:
            # Key indicator: significant rise from morning to afternoon during daylight
            # The fall may happen overnight, so we don't require it within same day
            min_rise_threshold = max(min_variance, daily_range * 0.3)
            has_solar_pattern = (
                rise >= min_rise_threshold and
                peak_time.hour >= 10 and peak_time.hour <= 18 and  # Peak during daylight
                sunrise_time.hour <= 12 and  # Low should be in morning
                sunrise_value < peak_value * 0.95  # Morning low should be noticeably lower
            )

            if has_solar_pattern:
                days_with_pattern += 1
                daily_patterns.append({
                    "date": date_str,
                    "sunrise": {
                        "time": sunrise_time.strftime("%H:%M"),
                        "value": round(sunrise_value, 1),
                    },
                    "peak": {
                        "time": peak_time.strftime("%H:%M"),
                        "value": round(peak_value, 1),
                    },
                    "sunset": {
                        "time": sunset_time.strftime("%H:%M"),
                        "value": round(sunset_value, 1),
                    },
                    "rise": round(rise, 1),
                    "fall": round(fall, 1),
                })

        # Consider a node solar-powered if it shows the pattern on at least 50% of analyzed days
        if total_days >= 2 and days_with_pattern / total_days >= 0.5:
            solar_score = round((days_with_pattern / total_days) * 100, 1)

            # Collect all telemetry data points for this node for charting
            # Determine which metric type was used (battery or voltage)
            all_chart_data = []
            metric_type = "battery"  # default
            for date_str, readings in daily_data.items():
                battery_count = sum(1 for r in readings if r["battery"] is not None)
                voltage_count = sum(1 for r in readings if r["voltage"] is not None)
                if voltage_count > battery_count:
                    metric_type = "voltage"
                for r in readings:
                    value = r["battery"] if metric_type == "battery" else r["voltage"]
                    if value is not None:
                        all_chart_data.append({
                            "timestamp": int(r["time"].timestamp() * 1000),
                            "value": round(value, 2),
                        })

            # Sort by timestamp and deduplicate
            all_chart_data.sort(key=lambda x: x["timestamp"])

            solar_candidates.append({
                "node_num": node_num,
                "node_name": node_names.get(node_num, f"!{node_num:08x}"),
                "solar_score": solar_score,
                "days_analyzed": total_days,
                "days_with_pattern": days_with_pattern,
                "recent_patterns": daily_patterns[-3:],  # Last 3 days with patterns
                "metric_type": metric_type,
                "chart_data": all_chart_data,
            })

    # Sort by solar score descending
    solar_candidates.sort(key=lambda x: x["solar_score"], reverse=True)

    # Fetch solar production data for the lookback period (for chart overlay)
    solar_result = await db.execute(
        select(
            SolarProduction.timestamp,
            func.avg(SolarProduction.watt_hours).label("avg_watt_hours"),
        )
        .where(SolarProduction.timestamp >= cutoff)
        .group_by(SolarProduction.timestamp)
        .order_by(SolarProduction.timestamp.asc())
    )
    solar_rows = solar_result.all()
    solar_chart_data = [
        {
            "timestamp": int(row.timestamp.timestamp() * 1000),
            "wattHours": round(row.avg_watt_hours, 2),
        }
        for row in solar_rows
    ]

    return {
        "lookback_days": lookback_days,
        "total_nodes_analyzed": len(node_data),
        "solar_nodes_count": len(solar_candidates),
        "solar_nodes": solar_candidates,
        "solar_production": solar_chart_data,
    }


@router.get("/solar")
async def get_solar_averages(
    db: AsyncSession = Depends(get_db),
    hours: int = Query(default=168, ge=1, le=8760, description="Hours of history to fetch"),
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


