"""Message and channel endpoints for the Communication page."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import String, case, distinct, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Channel, Message, Node, Source

router = APIRouter(prefix="/api/messages", tags=["messages"])


def _normalized_channel_name():
    """Return NULLIF(Channel.name, '') so NULL and empty string are treated equally."""
    return func.nullif(Channel.name, "")


def _channel_key_expr():
    """Return a SQLAlchemy CASE expression that produces the channel key.

    If the channel has a non-empty name, use the name; otherwise fall back to
    the stringified channel index from the Message table.
    """
    normed = _normalized_channel_name()
    return case(
        (normed.isnot(None), normed),
        else_=func.cast(Message.channel, String),
    )


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
    rx_time: datetime | None
    received_at: datetime


@router.get("/channels", response_model=list[ChannelSummary])
async def list_channels(
    db: AsyncSession = Depends(get_db),
) -> list[ChannelSummary]:
    """List all channels with message counts, grouped by channel name (or index)."""
    channel_key = _channel_key_expr().label("channel_key")

    # Join messages to channels to compute channel_key, then aggregate.
    # Group by the channel_key label to correctly merge NULL and empty-string
    # channel names that both resolve to the same key.
    query = (
        select(
            channel_key,
            func.count(distinct(Message.meshtastic_id)).label("message_count"),
            func.max(Message.received_at).label("last_message_at"),
        )
        .outerjoin(
            Channel,
            (Message.source_id == Channel.source_id) & (Message.channel == Channel.channel_index),
        )
        .where(or_(Message.text.isnot(None), Message.emoji.isnot(None)))
        .where(Message.channel >= 0)
        .group_by(channel_key)
        .order_by(text("last_message_at DESC NULLS LAST"))
    )

    result = await db.execute(query)
    rows = result.all()

    # For each channel_key, gather per-source names using DISTINCT instead of
    # GROUP BY to avoid the same PostgreSQL CASE-in-GROUP-BY issue.
    source_names_query = (
        select(
            _channel_key_expr().label("channel_key"),
            Source.name.label("source_name"),
            Channel.name.label("channel_name"),
        )
        .distinct()
        .select_from(Channel)
        .join(Source, Channel.source_id == Source.id)
        .outerjoin(
            Message,
            (Message.source_id == Channel.source_id) & (Message.channel == Channel.channel_index),
        )
        .where(or_(Message.text.isnot(None), Message.emoji.isnot(None)))
        .where(Message.channel >= 0)
    )
    source_result = await db.execute(source_names_query)

    channel_source_names: dict[str, list[ChannelSourceName]] = {}
    for row in source_result:
        key = row.channel_key
        if key not in channel_source_names:
            channel_source_names[key] = []
        channel_source_names[key].append(
            ChannelSourceName(source_name=row.source_name, channel_name=row.channel_name)
        )

    return [
        ChannelSummary(
            channel_key=row.channel_key,
            display_name=(
                row.channel_key if not row.channel_key.isdigit() else f"Channel {row.channel_key}"
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
        .outerjoin(
            Channel,
            (Message.source_id == Channel.source_id) & (Message.channel == Channel.channel_index),
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
            subquery = subquery.having(func.min(Message.received_at) < before_time)
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
        .outerjoin(Node, Message.from_node_num == Node.node_num)
        .outerjoin(
            Channel,
            (Message.source_id == Channel.source_id) & (Message.channel == Channel.channel_index),
        )
        .where(ck_expr == channel_key)
        .where(or_(Message.text.isnot(None), Message.emoji.isnot(None)))
        .distinct(Message.meshtastic_id)
        .order_by(Message.meshtastic_id, Message.rx_snr.desc().nullslast())
    )

    # Execute and get results
    result = await db.execute(query)
    rows = result.all()

    # Sort by received_at ascending (oldest first) and limit
    sorted_rows = sorted(rows, key=lambda r: r.received_at)

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

    # Next cursor is the timestamp of the oldest message returned
    next_cursor = None
    if has_more and messages:
        next_cursor = messages[0].received_at.isoformat()

    return MessagesListResponse(
        messages=messages,
        has_more=has_more,
        next_cursor=next_cursor,
    )


@router.get("/{packet_id}/sources", response_model=list[MessageSourceDetail])
async def get_message_sources(
    packet_id: str,
    db: AsyncSession = Depends(get_db),
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
            Message.rx_snr,
            Message.rx_rssi,
            Message.hop_limit,
            Message.hop_start,
            Message.rx_time,
            Message.received_at,
        )
        .join(Source, Message.source_id == Source.id)
        .where(filter_clause)
        .order_by(Message.rx_snr.desc().nullslast())
    )

    result = await db.execute(query)
    rows = result.all()

    return [
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
            rx_time=row.rx_time,
            received_at=row.received_at,
        )
        for row in rows
    ]
