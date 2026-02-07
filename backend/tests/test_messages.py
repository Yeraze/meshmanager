"""Tests for message and channel schemas and API."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.routers.messages import ChannelSummary, MessageResponse, MessagesListResponse


class TestChannelSummarySchema:
    """Tests for ChannelSummary schema."""

    def test_channel_key_accepts_string_name(self):
        """ChannelSummary should accept a string channel_key (channel name)."""
        summary = ChannelSummary(
            channel_key="gauntlet",
            display_name="gauntlet",
            message_count=42,
            last_message_at=datetime(2024, 1, 15, tzinfo=UTC),
            source_names=[],
        )
        assert summary.channel_key == "gauntlet"
        assert summary.display_name == "gauntlet"

    def test_channel_key_accepts_stringified_index(self):
        """ChannelSummary should accept a stringified index as channel_key."""
        summary = ChannelSummary(
            channel_key="0",
            display_name="Channel 0",
            message_count=10,
            last_message_at=None,
            source_names=[],
        )
        assert summary.channel_key == "0"

    def test_channel_key_rejects_missing(self):
        """ChannelSummary should reject missing channel_key."""
        with pytest.raises(ValidationError):
            ChannelSummary(
                display_name="test",
                message_count=0,
                last_message_at=None,
                source_names=[],
            )

    def test_source_names_populated(self):
        """ChannelSummary should carry per-source channel info."""
        summary = ChannelSummary(
            channel_key="gauntlet",
            display_name="gauntlet",
            message_count=5,
            last_message_at=None,
            source_names=[
                {"source_name": "mesh", "channel_name": "gauntlet"},
                {"source_name": "wynwood", "channel_name": "gauntlet"},
            ],
        )
        assert len(summary.source_names) == 2
        assert summary.source_names[0].source_name == "mesh"
        assert summary.source_names[1].channel_name == "gauntlet"


class TestMessageResponseSchema:
    """Tests for MessageResponse schema."""

    def test_channel_key_accepts_string(self):
        """MessageResponse should use channel_key as a string."""
        msg = MessageResponse(
            packet_id="abc123",
            meshtastic_id=100,
            from_node_num=12345678,
            to_node_num=None,
            channel_key="gauntlet",
            text="Hello world",
            emoji=None,
            reply_id=None,
            hop_limit=3,
            hop_start=3,
            rx_time=None,
            received_at=datetime(2024, 1, 15, tzinfo=UTC),
            from_short_name="TST1",
            from_long_name="Test Node",
            source_count=2,
        )
        assert msg.channel_key == "gauntlet"

    def test_channel_key_index_fallback(self):
        """MessageResponse should accept stringified index as channel_key."""
        msg = MessageResponse(
            packet_id="def456",
            meshtastic_id=None,
            from_node_num=12345678,
            to_node_num=None,
            channel_key="0",
            text="test",
            emoji=None,
            reply_id=None,
            hop_limit=None,
            hop_start=None,
            rx_time=None,
            received_at=datetime(2024, 1, 15, tzinfo=UTC),
            from_short_name=None,
            from_long_name=None,
            source_count=1,
        )
        assert msg.channel_key == "0"

    def test_channel_key_rejects_missing(self):
        """MessageResponse should reject missing channel_key."""
        with pytest.raises(ValidationError):
            MessageResponse(
                packet_id="abc",
                meshtastic_id=None,
                from_node_num=1,
                to_node_num=None,
                text="test",
                emoji=None,
                reply_id=None,
                hop_limit=None,
                hop_start=None,
                rx_time=None,
                received_at=datetime(2024, 1, 15, tzinfo=UTC),
                from_short_name=None,
                from_long_name=None,
                source_count=1,
            )


class TestMessagesListResponseSchema:
    """Tests for MessagesListResponse schema."""

    def test_valid_response(self):
        """MessagesListResponse should accept valid paginated data."""
        resp = MessagesListResponse(
            messages=[
                MessageResponse(
                    packet_id="abc",
                    meshtastic_id=200,
                    from_node_num=1,
                    to_node_num=None,
                    channel_key="gauntlet",
                    text="hello",
                    emoji=None,
                    reply_id=None,
                    hop_limit=None,
                    hop_start=None,
                    rx_time=None,
                    received_at=datetime(2024, 1, 15, tzinfo=UTC),
                    from_short_name=None,
                    from_long_name=None,
                    source_count=1,
                ),
            ],
            has_more=True,
            next_cursor="2024-01-15T00:00:00+00:00",
        )
        assert len(resp.messages) == 1
        assert resp.has_more is True
        assert resp.messages[0].channel_key == "gauntlet"

    def test_empty_response(self):
        """MessagesListResponse should accept empty message list."""
        resp = MessagesListResponse(
            messages=[],
            has_more=False,
            next_cursor=None,
        )
        assert len(resp.messages) == 0
        assert resp.has_more is False
