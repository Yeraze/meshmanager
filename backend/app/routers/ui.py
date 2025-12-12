"""UI data endpoints (internal use for frontend)."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, literal_column, select
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

    # Global tracking for average hours calculations
    all_charging_hours = []  # Hours between sunrise and sunset (daylight/charging period)
    all_discharge_hours = []  # Hours between sunset and next sunrise (overnight/discharge period)

    for node_num, daily_data in node_data.items():
        days_with_pattern = 0
        total_days = 0
        high_efficiency_days = 0
        daily_patterns = []
        charge_rates = []  # List of charge rates per hour for averaging
        discharge_rates = []  # List of discharge rates per hour for averaging
        previous_day_sunset = None  # Track previous day's sunset for discharge calculation

        # Sort dates to process in chronological order for discharge calculation
        sorted_dates = sorted(daily_data.keys())

        for date_str in sorted_dates:
            readings = daily_data[date_str]
            if len(readings) < 3:  # Need at least 3 readings to detect a pattern
                continue

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

            # Determine if this is potentially a "high-efficiency solar" setup
            # These nodes have large batteries/panels that stay 90-100% with minimal swing
            is_battery = len(battery_values) >= 3
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
                continue

            # Count this as a valid day for analysis
            total_days += 1

            # Track high-efficiency days for threshold adjustment
            if is_high_efficiency_candidate:
                high_efficiency_days += 1

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
            if is_high_efficiency_candidate:
                # Relaxed thresholds for high-efficiency solar (nodes that stay 90-100%)
                # These nodes show the TIME pattern but with smaller swings
                min_rise_threshold = 1 if is_battery else 0.02  # 1% for battery, 0.02V for voltage
                min_ratio = 0.98  # Morning can be within 2% of peak
            else:
                min_rise_threshold = max(min_variance, daily_range * 0.3)
                min_ratio = 0.95  # Morning should be at least 5% below peak

            has_solar_pattern = (
                rise >= min_rise_threshold and
                peak_time.hour >= 10 and peak_time.hour <= 18 and  # Peak during daylight
                sunrise_time.hour <= 12 and  # Low should be in morning
                sunrise_value <= peak_value * min_ratio  # Morning low should be noticeably lower
            )

            if has_solar_pattern:
                days_with_pattern += 1

                # Calculate charge rate per hour (sunrise -> peak/100%)
                # If battery hits 100% before peak, use that time instead
                effective_peak_time = peak_time
                effective_peak_value = peak_value
                if is_battery:
                    # Find if battery hits 100% between sunrise and sunset
                    for v in values:
                        if v["time"] > sunrise_time and v["time"] <= sunset_time and v["value"] >= 100:
                            # Use the first time it hits 100%
                            effective_peak_time = v["time"]
                            effective_peak_value = v["value"]
                            break

                charging_hours = (effective_peak_time - sunrise_time).total_seconds() / 3600
                charge_rate = (effective_peak_value - sunrise_value) / charging_hours if charging_hours > 0 else 0
                charge_rates.append(charge_rate)

                # Track daylight/charging hours (sunrise -> sunset)
                daylight_hours = (sunset_time - sunrise_time).total_seconds() / 3600
                if daylight_hours > 0:
                    all_charging_hours.append(daylight_hours)

                # Calculate discharge rate per hour (previous sunset -> this sunrise)
                discharge_rate = None
                if previous_day_sunset is not None:
                    prev_sunset_time = previous_day_sunset["time"]
                    prev_sunset_value = previous_day_sunset["value"]
                    # Calculate hours between previous sunset and current sunrise
                    discharge_hours = (sunrise_time - prev_sunset_time).total_seconds() / 3600
                    if discharge_hours > 0:
                        # Discharge is previous_sunset - current_sunrise (should be positive if discharging)
                        discharge_rate = (prev_sunset_value - sunrise_value) / discharge_hours
                        discharge_rates.append(discharge_rate)
                        # Track overnight/discharge hours
                        all_discharge_hours.append(discharge_hours)

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
                    "charge_rate_per_hour": round(charge_rate, 2),
                    "discharge_rate_per_hour": round(discharge_rate, 2) if discharge_rate is not None else None,
                })

            # Track this day's sunset for next day's discharge calculation
            # Only track if we have valid sunset data
            if sunset_time and sunset_value is not None:
                previous_day_sunset = {
                    "time": sunset_time,
                    "value": sunset_value,
                }

        # Consider a node solar-powered if it shows the pattern on enough analyzed days
        # High-efficiency nodes (stay 90-100%) use a lower threshold since small swings
        # make patterns harder to detect consistently
        is_mostly_high_efficiency = high_efficiency_days > total_days * 0.5
        min_pattern_ratio = 0.33 if is_mostly_high_efficiency else 0.5
        if total_days >= 2 and days_with_pattern / total_days >= min_pattern_ratio:
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

            # Calculate average rates
            avg_charge_rate = round(sum(charge_rates) / len(charge_rates), 2) if charge_rates else None
            avg_discharge_rate = round(sum(discharge_rates) / len(discharge_rates), 2) if discharge_rates else None

            solar_candidates.append({
                "node_num": node_num,
                "node_name": node_names.get(node_num, f"!{node_num:08x}"),
                "solar_score": solar_score,
                "days_analyzed": total_days,
                "days_with_pattern": days_with_pattern,
                "recent_patterns": daily_patterns[-3:],  # Last 3 days with patterns
                "metric_type": metric_type,
                "chart_data": all_chart_data,
                "avg_charge_rate_per_hour": avg_charge_rate,
                "avg_discharge_rate_per_hour": avg_discharge_rate,
            })

    # Sort by solar score descending
    solar_candidates.sort(key=lambda x: x["solar_score"], reverse=True)

    # Fetch solar production data for the lookback period (for chart overlay)
    # Group by hour and sum watt_hours from all sources to get complete hourly totals
    hour_trunc = func.date_trunc("hour", SolarProduction.timestamp)
    solar_result = await db.execute(
        select(
            hour_trunc.label("hour"),
            func.sum(SolarProduction.watt_hours).label("total_watt_hours"),
        )
        .where(SolarProduction.timestamp >= cutoff)
        .group_by(literal_column("1"))
        .order_by(literal_column("1").asc())
    )
    solar_rows = solar_result.all()
    solar_chart_data = [
        {
            "timestamp": int(row.hour.timestamp() * 1000),
            "wattHours": round(row.total_watt_hours, 2),
        }
        for row in solar_rows
    ]

    # Calculate global averages
    avg_charging_hours_per_day = round(sum(all_charging_hours) / len(all_charging_hours), 1) if all_charging_hours else None
    avg_discharge_hours_per_day = round(sum(all_discharge_hours) / len(all_discharge_hours), 1) if all_discharge_hours else None

    # Add insufficient_solar flag to each node
    # Formula: if (charge_rate * charging_hours) <= (discharge_rate * discharge_hours) * 1.1
    # This means the node isn't generating enough to keep up with its overnight discharge
    for node in solar_candidates:
        charge_rate = node.get("avg_charge_rate_per_hour")
        discharge_rate = node.get("avg_discharge_rate_per_hour")

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
    day_trunc = func.date_trunc("day", SolarProduction.timestamp)
    historical_result = await db.execute(
        select(
            day_trunc.label("day"),
            func.sum(SolarProduction.watt_hours).label("total_wh"),
        )
        .where(SolarProduction.timestamp >= cutoff)
        .where(SolarProduction.timestamp < now.replace(hour=0, minute=0, second=0, microsecond=0))
        .group_by(literal_column("1"))
        .order_by(literal_column("1"))
    )
    historical_rows = historical_result.all()

    # Get forecast solar production (today and future)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    forecast_result = await db.execute(
        select(
            day_trunc.label("day"),
            func.sum(SolarProduction.watt_hours).label("total_wh"),
        )
        .where(SolarProduction.timestamp >= today_start)
        .group_by(literal_column("1"))
        .order_by(literal_column("1"))
    )
    forecast_rows = forecast_result.all()

    # Calculate historical average daily output
    historical_daily_wh = [row.total_wh for row in historical_rows if row.total_wh]
    avg_historical_daily_wh = sum(historical_daily_wh) / len(historical_daily_wh) if historical_daily_wh else 0

    # Analyze forecast days - extend to 5 days into the future
    forecast_days = []
    low_output_warning = False

    # Create a dict of actual forecast data by date
    actual_forecast_by_date = {}
    for row in forecast_rows:
        actual_forecast_by_date[row.day.strftime("%Y-%m-%d")] = row.total_wh or 0

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
    # First, get battery/voltage telemetry for identified solar nodes
    telemetry_result = await db.execute(
        select(Telemetry, Source.name.label("source_name"))
        .join(Source)
        .where(Telemetry.received_at >= cutoff)
        .where(
            (Telemetry.battery_level.isnot(None)) | (Telemetry.voltage.isnot(None))
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
        node_data[telemetry.node_num][date_str].append({
            "time": telemetry.received_at,
            "battery": telemetry.battery_level,
            "voltage": telemetry.voltage,
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
        days_with_pattern = 0
        total_days = 0
        charge_rates = []
        discharge_rates = []
        previous_day_sunset = None
        last_known_battery = None
        metric_type = "battery"

        sorted_dates = sorted(daily_data.keys())

        for date_str in sorted_dates:
            readings = daily_data[date_str]
            if len(readings) < 3:
                continue

            readings.sort(key=lambda x: x["time"])

            # Separate battery and voltage
            battery_values = []
            voltage_values = []
            for r in readings:
                if r["battery"] is not None:
                    battery_values.append({"time": r["time"], "value": r["battery"]})
                if r["voltage"] is not None:
                    voltage_values.append({"time": r["time"], "value": r["voltage"]})

            if len(battery_values) >= 3:
                values = battery_values
                min_variance = 10
                metric_type = "battery"
            elif len(voltage_values) >= 3:
                values = voltage_values
                min_variance = 0.3
                metric_type = "voltage"
            else:
                continue

            all_values = [v["value"] for v in values]
            min_value = min(all_values)
            max_value = max(all_values)
            daily_range = max_value - min_value

            is_battery = len(battery_values) >= 3
            is_high_efficiency_candidate = False
            if is_battery:
                is_high_efficiency_candidate = (
                    min_value >= 90 and max_value >= 95 and
                    daily_range >= 2 and daily_range < min_variance
                )
            else:
                is_high_efficiency_candidate = (
                    min_value >= 4.0 and max_value >= 4.1 and
                    daily_range >= 0.05 and daily_range < min_variance
                )

            if daily_range < min_variance and not is_high_efficiency_candidate:
                continue

            total_days += 1

            # Track last known battery level
            if is_battery:
                last_known_battery = values[-1]["value"]

            # Find morning and afternoon values
            morning_values = [v for v in values if 6 <= v["time"].hour <= 10]
            afternoon_values = [v for v in values if 12 <= v["time"].hour <= 18]

            if morning_values and afternoon_values:
                morning_low = min(morning_values, key=lambda v: v["value"])
                afternoon_high = max(afternoon_values, key=lambda v: v["value"])

                sunrise_value = morning_low["value"]
                sunrise_time = morning_low["time"]
                peak_value = afternoon_high["value"]
                peak_time = afternoon_high["time"]
                sunset_value = values[-1]["value"]
                sunset_time = values[-1]["time"]
                rise = peak_value - sunrise_value
            else:
                peak_idx = max(range(len(values)), key=lambda i: values[i]["value"])
                peak_value = values[peak_idx]["value"]
                peak_time = values[peak_idx]["time"]

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

            if is_high_efficiency_candidate:
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

            if has_solar_pattern:
                days_with_pattern += 1

                # Calculate charge rate
                effective_peak_time = peak_time
                effective_peak_value = peak_value
                if is_battery:
                    for v in values:
                        if v["time"] > sunrise_time and v["time"] <= sunset_time and v["value"] >= 100:
                            effective_peak_time = v["time"]
                            effective_peak_value = v["value"]
                            break

                charging_hours = (effective_peak_time - sunrise_time).total_seconds() / 3600
                charge_rate = (effective_peak_value - sunrise_value) / charging_hours if charging_hours > 0 else 0
                charge_rates.append(charge_rate)

                daylight_hours = (sunset_time - sunrise_time).total_seconds() / 3600
                if daylight_hours > 0:
                    all_charging_hours.append(daylight_hours)

                # Calculate discharge rate
                if previous_day_sunset is not None:
                    prev_sunset_time = previous_day_sunset["time"]
                    prev_sunset_value = previous_day_sunset["value"]
                    discharge_hours = (sunrise_time - prev_sunset_time).total_seconds() / 3600
                    if discharge_hours > 0:
                        discharge_rate = (prev_sunset_value - sunrise_value) / discharge_hours
                        discharge_rates.append(discharge_rate)
                        all_discharge_hours.append(discharge_hours)

            if sunset_time and sunset_value is not None:
                previous_day_sunset = {"time": sunset_time, "value": sunset_value}

        # Only process nodes that show solar patterns
        is_mostly_high_efficiency = total_days > 0 and (
            sum(1 for d in sorted_dates if len(daily_data[d]) >= 3) > total_days * 0.5
        )
        min_pattern_ratio = 0.33 if is_mostly_high_efficiency else 0.5

        if total_days >= 2 and days_with_pattern / total_days >= min_pattern_ratio:
            avg_charge_rate = sum(charge_rates) / len(charge_rates) if charge_rates else 0
            avg_discharge_rate = sum(discharge_rates) / len(discharge_rates) if discharge_rates else 0
            avg_charging_hours = sum(all_charging_hours) / len(all_charging_hours) if all_charging_hours else 10
            avg_discharge_hours = sum(all_discharge_hours) / len(all_discharge_hours) if all_discharge_hours else 14

            # Only simulate for battery metrics
            if metric_type == "battery" and last_known_battery is not None:
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
                all_solar_simulations.append({
                    "node_num": node_num,
                    "node_name": node_names.get(node_num, f"!{node_num:08x}"),
                    "current_battery": round(last_known_battery, 1),
                    "min_simulated_battery": round(min_simulated, 1),
                    "avg_charge_rate_per_hour": round(avg_charge_rate, 2),
                    "avg_discharge_rate_per_hour": round(avg_discharge_rate, 2),
                    "simulation": forecast_simulation,
                })

                # Flag if simulation shows battery dropping below 50%
                if min_simulated < 50:
                    nodes_at_risk.append({
                        "node_num": node_num,
                        "node_name": node_names.get(node_num, f"!{node_num:08x}"),
                        "current_battery": round(last_known_battery, 1),
                        "min_simulated_battery": round(min_simulated, 1),
                        "avg_charge_rate_per_hour": round(avg_charge_rate, 2),
                        "avg_discharge_rate_per_hour": round(avg_discharge_rate, 2),
                        "simulation": forecast_simulation,
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


