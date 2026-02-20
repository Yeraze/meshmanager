"""Message and channel endpoints for the Communication page."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import String, case, distinct, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import require_tab_access
from app.database import get_db
from app.models import Channel, Message, Node, Source
from app.models.source import SourceType

# Roles that never relay packets (should be excluded from relay node resolution)
_MUTE_ROLES = {"1", "CLIENT_MUTE", "8", "CLIENT_HIDDEN"}

# Roles that are relay-capable (preferred when resolving relay node)
_RELAY_ROLES = {
    "2", "ROUTER",
    "3", "ROUTER_CLIENT",
    "4", "REPEATER",
    "11", "ROUTER_LATE",
    "12", "CLIENT_BASE",
}

router = APIRouter(prefix="/api/messages", tags=["messages"])


def _channel_key_expr():
    """Return a channel key based on the message's own source channel name.

    Uses a correlated subquery to look up the channel name from the same source
    that recorded the message.  This ensures each source's naming is respected
    (e.g. MQTT "MediumFast" vs "LongFast") while unnamed channels fall back to
    the stringified channel index.
    """
    source_name = (
        select(Channel.name)
        .where(Channel.source_id == Message.source_id)
        .where(Channel.channel_index == Message.channel)
        .where(Channel.name.isnot(None))
        .where(Channel.name != "")
        .correlate(Message)
        .scalar_subquery()
    )
    return func.coalesce(source_name, func.cast(Message.channel, String))


# Response schemas
class ChannelSourceName(BaseModel):
    """Channel name from a specific source."""

    source_name: str
    channel_name: str | None


class ChannelSummary(BaseModel):
    """Summary of a channel with message counts."""

    channel_key: str
    display_name: str
    message_count: int
    last_message_at: datetime | None
    source_names: list[ChannelSourceName]


class MessageResponse(BaseModel):
    """A deduplicated message response."""

    packet_id: str
    meshtastic_id: int | None
    from_node_num: int
    to_node_num: int | None
    channel_key: str
    text: str | None
    emoji: str | None
    reply_id: int | None
    hop_limit: int | None
    hop_start: int | None
    rx_time: datetime | None
    received_at: datetime
    from_short_name: str | None
    from_long_name: str | None
    source_count: int


class MessagesListResponse(BaseModel):
    """Paginated list of messages."""

    messages: list[MessageResponse]
    has_more: bool
    next_cursor: str | None


class MessageSourceDetail(BaseModel):
    """Per-source reception details for a message."""

    source_id: str
    source_name: str
    rx_snr: float | None
    rx_rssi: int | None
    hop_limit: int | None
    hop_start: int | None
    hop_count: int | None
    relay_node: int | None
    relay_node_name: str | None
    gateway_node_num: int | None
    gateway_node_name: str | None
    rx_time: datetime | None
    received_at: datetime


@router.get("/channels", response_model=list[ChannelSummary])
async def list_channels(
    db: AsyncSession = Depends(get_db),
    _access: None = Depends(require_tab_access("communication")),
) -> list[ChannelSummary]:
    """List all channels with message counts, grouped by per-source channel name."""
    channel_key = _channel_key_expr().label("channel_key")

    # Group by channel name (per-source lookup).  Channels with the same name
    # across different sources merge naturally; unnamed channels fall back to
    # their stringified index.
    query = (
        select(
            channel_key,
            func.count(distinct(Message.meshtastic_id)).label("message_count"),
            func.max(Message.received_at).label("last_message_at"),
        )
        .where(or_(Message.text.isnot(None), Message.emoji.isnot(None)))
        .where(Message.channel >= 0)
        .group_by(channel_key)
        .order_by(text("last_message_at DESC NULLS LAST"))
    )

    result = await db.execute(query)
    rows = result.all()

    # Collect the set of channel_keys from the main query
    channel_keys = {row.channel_key for row in rows}

    # Build per-source channel info.  Each Channel record's key is determined
    # by its own name (empty → stringified index).
    all_channels_query = (
        select(
            Channel.channel_index,
            Channel.name.label("channel_name"),
            Source.name.label("source_name"),
        )
        .select_from(Channel)
        .join(Source, Channel.source_id == Source.id)
    )
    all_channels_result = await db.execute(all_channels_query)

    # Map each Channel record to its channel_key and collect source info
    channel_source_names: dict[str, list[ChannelSourceName]] = {}
    seen: set[tuple[str, str]] = set()  # (key, source_name) dedup
    for row in all_channels_result:
        key = row.channel_name if row.channel_name else str(row.channel_index)
        if key not in channel_keys:
            continue  # No messages for this channel
        dedup = (key, row.source_name)
        if dedup in seen:
            continue
        seen.add(dedup)
        channel_source_names.setdefault(key, []).append(
            ChannelSourceName(source_name=row.source_name, channel_name=row.channel_name)
        )

    return [
        ChannelSummary(
            channel_key=row.channel_key,
            display_name=(
                row.channel_key
                if not row.channel_key.isdigit()
                else f"Channel {row.channel_key}"
            ),
            message_count=row.message_count,
            last_message_at=row.last_message_at,
            source_names=channel_source_names.get(row.channel_key, []),
        )
        for row in rows
    ]


@router.get("", response_model=MessagesListResponse)
async def list_messages(
    channel_key: Annotated[str, Query(description="Channel key to filter by")],
    limit: Annotated[int, Query(ge=1, le=100, description="Number of messages to return")] = 50,
    before: Annotated[
        str | None, Query(description="Cursor for pagination (ISO timestamp)")
    ] = None,
    source_names: Annotated[
        list[str] | None,
        Query(description="Filter to messages from these sources"),
    ] = None,
    db: AsyncSession = Depends(get_db),
    _access: None = Depends(require_tab_access("communication")),
) -> MessagesListResponse:
    """List messages for a channel, deduplicated by packet_id.

    Messages are returned oldest-first (ascending by received_at).
    Use 'before' cursor to load older messages (for infinite scroll up).
    Optionally filter by source names to show only messages from specific sources.
    """
    ck_expr = _channel_key_expr()

    # Build subquery to get distinct messages by meshtastic_id (cross-source dedup)
    # and count how many source copies exist
    subquery = (
        select(
            Message.meshtastic_id,
            func.min(Message.received_at).label("first_received_at"),
            func.count(Message.id).label("source_count"),
        )
        .where(ck_expr == channel_key)
        .where(or_(Message.text.isnot(None), Message.emoji.isnot(None)))
        .where(Message.meshtastic_id.isnot(None))
    )

    # Filter by source names if provided
    if source_names:
        subquery = subquery.join(Source, Message.source_id == Source.id).where(
            Source.name.in_(source_names)
        )

    subquery = subquery.group_by(Message.meshtastic_id)

    if before:
        # Parse ISO timestamp cursor
        try:
            before_time = datetime.fromisoformat(before.replace("Z", "+00:00"))
            subquery = subquery.having(
                func.coalesce(func.min(Message.rx_time), func.min(Message.received_at))
                < before_time
            )
        except ValueError:
            pass  # Invalid cursor, ignore

    subquery = subquery.subquery()

    # Join back to get full message data for each deduplicated message
    # Use the row with best SNR as the representative
    query = (
        select(
            Message.packet_id,
            Message.meshtastic_id,
            Message.from_node_num,
            Message.to_node_num,
            Message.channel,
            Message.text,
            Message.emoji,
            Message.reply_id,
            Message.hop_limit,
            Message.hop_start,
            Message.rx_time,
            Message.received_at,
            Node.short_name.label("from_short_name"),
            Node.long_name.label("from_long_name"),
            subquery.c.source_count,
        )
        .join(subquery, Message.meshtastic_id == subquery.c.meshtastic_id)
        .outerjoin(
            Node,
            (Message.from_node_num == Node.node_num) & (Message.source_id == Node.source_id),
        )
        .where(ck_expr == channel_key)
        .where(or_(Message.text.isnot(None), Message.emoji.isnot(None)))
        .distinct(Message.meshtastic_id)
        .order_by(Message.meshtastic_id, Message.rx_snr.desc().nullslast())
    )

    # Filter main query by source too, so DISTINCT ON picks from the correct pool
    if source_names:
        query = query.join(Source, Message.source_id == Source.id).where(
            Source.name.in_(source_names)
        )

    # Execute and get results
    result = await db.execute(query)
    rows = result.all()

    # Sort by display timestamp ascending (oldest first) and limit.
    # Use rx_time (device time) when available, falling back to received_at,
    # to match the frontend's getMessageTimestamp() display logic.
    sorted_rows = sorted(rows, key=lambda r: r.rx_time or r.received_at)

    # For "before" pagination, we want the N most recent messages before the cursor
    # So take the last N items
    if before:
        sorted_rows = sorted_rows[-(limit + 1) :] if len(sorted_rows) > limit else sorted_rows
    else:
        # Initial load: get the most recent messages (last N)
        sorted_rows = sorted_rows[-(limit + 1) :] if len(sorted_rows) > limit else sorted_rows

    has_more = len(sorted_rows) > limit
    if has_more:
        sorted_rows = sorted_rows[-limit:]  # Take the last 'limit' items

    # Compute channel_key for each message row
    # Since we filtered by channel_key already, all rows share the same key
    messages = [
        MessageResponse(
            packet_id=row.packet_id,
            meshtastic_id=row.meshtastic_id,
            from_node_num=row.from_node_num,
            to_node_num=row.to_node_num,
            channel_key=channel_key,
            text=row.text,
            emoji=row.emoji,
            reply_id=row.reply_id,
            hop_limit=row.hop_limit,
            hop_start=row.hop_start,
            rx_time=row.rx_time,
            received_at=row.received_at,
            from_short_name=row.from_short_name,
            from_long_name=row.from_long_name,
            source_count=row.source_count,
        )
        for row in sorted_rows
    ]

    # Next cursor is the display timestamp of the oldest message returned
    next_cursor = None
    if has_more and messages:
        next_cursor = (messages[0].rx_time or messages[0].received_at).isoformat()

    return MessagesListResponse(
        messages=messages,
        has_more=has_more,
        next_cursor=next_cursor,
    )


async def _resolve_relay_node_name(
    db: AsyncSession,
    source_id: str,
    relay_node_byte: int,
    message_rssi: int | None,
    gateway_node_num: int | None = None,
) -> str | None:
    """Resolve a relay_node byte to the best-guess node name.

    Meshtastic's relay_node field contains only the last byte of the relaying
    node's 32-bit node number.  We match by ``(node_num & 0xFF) == relay_node_byte``,
    exclude non-relaying roles, require the node to be a direct neighbor
    (hops_away <= 1), and pick the best candidate using relay-capable role
    preference and RSSI proximity.

    For MQTT messages with a known gateway, we additionally exclude the gateway
    itself (it can't relay to itself) and prefer candidates geographically
    closer to the gateway.
    """
    rssi_ref = message_rssi if message_rssi is not None else -999

    query = (
        select(
            func.coalesce(Node.long_name, Node.short_name).label("name"),
        )
        .where(
            Node.source_id == source_id,
            (Node.node_num.op("&")(255) == relay_node_byte),
        )
        .where(Node.role.notin_(_MUTE_ROLES) | Node.role.is_(None))
        # A relay node must be a direct neighbor of the receiver
        .where(or_(Node.hops_away <= 1, Node.hops_away.is_(None)))
    )

    # If we know the gateway, exclude it from candidates (can't relay to itself)
    if gateway_node_num is not None:
        query = query.where(Node.node_num != gateway_node_num)

    query = query.order_by(
        Node.hops_away.asc().nullslast(),
        case(
            (Node.role.in_(_RELAY_ROLES), 0),
            else_=1,
        ),
        func.abs(func.coalesce(Node.rssi, -999) - rssi_ref).asc(),
    ).limit(1)

    result = await db.execute(query)
    return result.scalar()


@router.get("/{packet_id}/sources", response_model=list[MessageSourceDetail])
async def get_message_sources(
    packet_id: str,
    db: AsyncSession = Depends(get_db),
    _access: None = Depends(require_tab_access("communication")),
) -> list[MessageSourceDetail]:
    """Get per-source reception details for a specific message.

    Finds all copies across sources by matching meshtastic_id,
    falling back to exact packet_id match.
    """
    # First try to find by exact packet_id to get the meshtastic_id
    lookup = await db.execute(
        select(Message.meshtastic_id).where(Message.packet_id == packet_id).limit(1)
    )
    mesh_id = lookup.scalar()

    if mesh_id is not None:
        # Find all copies across sources with the same meshtastic_id
        filter_clause = Message.meshtastic_id == mesh_id
    else:
        # Fallback to exact packet_id match
        filter_clause = Message.packet_id == packet_id

    query = (
        select(
            Message.source_id,
            Source.name.label("source_name"),
            Source.type.label("source_type"),
            Message.rx_snr,
            Message.rx_rssi,
            Message.hop_limit,
            Message.hop_start,
            Message.relay_node,
            Message.gateway_node_num,
            Message.rx_time,
            Message.received_at,
        )
        .join(Source, Message.source_id == Source.id)
        .where(filter_clause)
        .order_by(Message.rx_snr.desc().nullslast())
    )

    result = await db.execute(query)
    rows = result.all()

    sources = []
    for row in rows:
        relay_node_name = None
        if row.relay_node is not None:
            relay_node_name = await _resolve_relay_node_name(
                db,
                str(row.source_id),
                row.relay_node,
                row.rx_rssi,
                gateway_node_num=row.gateway_node_num,
            )

        # Resolve gateway node name if present (try same source first, then any source)
        gateway_node_name = None
        if row.gateway_node_num is not None:
            gw_result = await db.execute(
                select(func.coalesce(Node.long_name, Node.short_name))
                .where(Node.source_id == row.source_id, Node.node_num == row.gateway_node_num)
                .limit(1)
            )
            gateway_node_name = gw_result.scalar()
            if not gateway_node_name:
                # Fall back to any source that has a name for this node
                gw_result = await db.execute(
                    select(func.coalesce(Node.long_name, Node.short_name))
                    .where(
                        Node.node_num == row.gateway_node_num,
                        func.coalesce(Node.long_name, Node.short_name).isnot(None),
                    )
                    .limit(1)
                )
                gateway_node_name = gw_result.scalar()

        sources.append(
            MessageSourceDetail(
                source_id=str(row.source_id),
                source_name=row.source_name,
                # Convert SNR from stored int (dB * 4) to actual dB
                rx_snr=row.rx_snr / 4.0 if row.rx_snr is not None else None,
                rx_rssi=row.rx_rssi,
                hop_limit=row.hop_limit,
                hop_start=row.hop_start,
                # Calculate hop count if both values present
                hop_count=(row.hop_start - row.hop_limit)
                if row.hop_start is not None and row.hop_limit is not None
                else None,
                relay_node=row.relay_node,
                relay_node_name=relay_node_name,
                gateway_node_num=row.gateway_node_num,
                gateway_node_name=gateway_node_name,
                rx_time=row.rx_time,
                received_at=row.received_at,
            )
        )

    # Resolve gateway for MeshMonitor sources that have no gateway_node_num.
    # Each MeshMonitor instance IS a gateway — the local node (hops_away=0).
    mm_sources = [
        s for s, row in zip(sources, rows)
        if row.source_type == SourceType.MESHMONITOR and s.gateway_node_num is None
    ]
    if mm_sources:
        # Batch-query: find the local node (hops_away=0) with position for each source
        mm_source_ids = list({s.source_id for s in mm_sources})
        local_q = await db.execute(
            select(
                Node.source_id,
                Node.node_num,
                func.coalesce(Node.long_name, Node.short_name).label("node_name"),
            )
            .where(
                Node.source_id.in_(mm_source_ids),
                Node.hops_away == 0,
                Node.latitude.isnot(None),
                Node.longitude.isnot(None),
            )
            .distinct(Node.source_id)
        )
        local_nodes = {str(r.source_id): r for r in local_q.all()}

        for s in mm_sources:
            local = local_nodes.get(s.source_id)
            if local:
                s.gateway_node_num = local.node_num
                s.gateway_node_name = local.node_name

    return sources
