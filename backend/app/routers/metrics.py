"""Prometheus metrics endpoint."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Gauge, generate_latest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Message, Node, Source, Telemetry, Traceroute

router = APIRouter(tags=["metrics"])


async def collect_metrics(db: AsyncSession) -> bytes:
    """Collect all metrics and return Prometheus format."""
    registry = CollectorRegistry()

    # Source health metrics
    source_healthy = Gauge(
        "meshmanager_source_healthy",
        "Source collection status (1=healthy, 0=error)",
        ["source", "type"],
        registry=registry,
    )
    source_last_collection = Gauge(
        "meshmanager_source_last_collection_timestamp",
        "Last successful collection timestamp",
        ["source"],
        registry=registry,
    )

    # Node metrics
    node_battery = Gauge(
        "meshmanager_node_battery_level",
        "Node battery level (0-100)",
        ["source", "node_id", "short_name"],
        registry=registry,
    )
    node_voltage = Gauge(
        "meshmanager_node_voltage",
        "Node voltage",
        ["source", "node_id", "short_name"],
        registry=registry,
    )
    node_last_heard = Gauge(
        "meshmanager_node_last_heard_timestamp",
        "Node last heard timestamp (Unix seconds)",
        ["source", "node_id", "short_name"],
        registry=registry,
    )
    node_channel_util = Gauge(
        "meshmanager_node_channel_utilization",
        "Node channel utilization (0-100)",
        ["source", "node_id", "short_name"],
        registry=registry,
    )

    # Network metrics
    active_nodes = Gauge(
        "meshmanager_active_nodes_total",
        "Total active nodes per source (heard in last hour)",
        ["source"],
        registry=registry,
    )
    total_nodes = Gauge(
        "meshmanager_nodes_total",
        "Total nodes ever seen per source",
        ["source"],
        registry=registry,
    )
    messages_last_hour = Gauge(
        "meshmanager_messages_last_hour",
        "Messages received in last hour",
        ["source"],
        registry=registry,
    )

    # Database metrics
    db_rows = Gauge(
        "meshmanager_db_rows_total",
        "Database row counts",
        ["table"],
        registry=registry,
    )

    # Fetch sources
    sources_result = await db.execute(select(Source))
    sources = sources_result.scalars().all()

    one_hour_ago = datetime.now(UTC) - timedelta(hours=1)

    for source in sources:
        source_name = source.name
        source_type = source.type.value

        # Source health
        is_healthy = source.enabled and source.last_error is None
        source_healthy.labels(source=source_name, type=source_type).set(1 if is_healthy else 0)

        if source.last_poll_at:
            source_last_collection.labels(source=source_name).set(
                source.last_poll_at.timestamp()
            )

        # Count nodes
        total_count = await db.execute(
            select(func.count()).select_from(Node).where(Node.source_id == source.id)
        )
        total_nodes.labels(source=source_name).set(total_count.scalar() or 0)

        active_count = await db.execute(
            select(func.count())
            .select_from(Node)
            .where(Node.source_id == source.id, Node.last_heard >= one_hour_ago)
        )
        active_nodes.labels(source=source_name).set(active_count.scalar() or 0)

        # Count messages in last hour
        msg_count = await db.execute(
            select(func.count())
            .select_from(Message)
            .where(Message.source_id == source.id, Message.received_at >= one_hour_ago)
        )
        messages_last_hour.labels(source=source_name).set(msg_count.scalar() or 0)

        # Get latest telemetry for each node
        nodes_result = await db.execute(
            select(Node).where(Node.source_id == source.id)
        )
        nodes = nodes_result.scalars().all()

        for node in nodes:
            node_id = node.node_id or f"!{node.node_num:08x}"
            short_name = node.short_name or "unknown"

            if node.last_heard:
                node_last_heard.labels(
                    source=source_name, node_id=node_id, short_name=short_name
                ).set(node.last_heard.timestamp())

            # Get latest telemetry
            telemetry_result = await db.execute(
                select(Telemetry)
                .where(Telemetry.source_id == source.id, Telemetry.node_num == node.node_num)
                .order_by(Telemetry.received_at.desc())
                .limit(1)
            )
            telemetry = telemetry_result.scalar()

            if telemetry:
                if telemetry.battery_level is not None:
                    node_battery.labels(
                        source=source_name, node_id=node_id, short_name=short_name
                    ).set(telemetry.battery_level)
                if telemetry.voltage is not None:
                    node_voltage.labels(
                        source=source_name, node_id=node_id, short_name=short_name
                    ).set(telemetry.voltage)
                if telemetry.channel_utilization is not None:
                    node_channel_util.labels(
                        source=source_name, node_id=node_id, short_name=short_name
                    ).set(telemetry.channel_utilization)

    # Database row counts
    for table_name, model in [
        ("nodes", Node),
        ("messages", Message),
        ("telemetry", Telemetry),
        ("traceroutes", Traceroute),
    ]:
        count_result = await db.execute(select(func.count()).select_from(model))
        db_rows.labels(table=table_name).set(count_result.scalar() or 0)

    return generate_latest(registry)


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics(db: AsyncSession = Depends(get_db)) -> PlainTextResponse:
    """Prometheus metrics endpoint."""
    metrics_data = await collect_metrics(db)
    return PlainTextResponse(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
