"""Tests for MQTT topic parsing and gateway/channel extraction."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.collectors.mqtt import MqttCollector
from app.models import Channel, Message, Source


@pytest.fixture
def mqtt_source():
    """Create a mock MQTT source."""
    source = MagicMock(spec=Source)
    source.id = "test-source-id"
    source.name = "test-mqtt"
    source.mqtt_host = "localhost"
    source.mqtt_port = 1883
    source.mqtt_username = None
    source.mqtt_password = None
    source.mqtt_topic_pattern = "msh/US/#"
    return source


@pytest.fixture
def collector(mqtt_source):
    """Create an MqttCollector instance."""
    return MqttCollector(mqtt_source)


# ---------------------------------------------------------------------------
# _parse_mqtt_topic unit tests
# ---------------------------------------------------------------------------


class TestParseMqttTopic:
    """Unit tests for _parse_mqtt_topic static method."""

    def test_standard_json_topic(self):
        channel, gw = MqttCollector._parse_mqtt_topic(
            "msh/US/FL/2/json/MediumFast/!435730e4"
        )
        assert channel == "MediumFast"
        assert gw == 0x435730E4

    def test_standard_protobuf_topic(self):
        channel, gw = MqttCollector._parse_mqtt_topic(
            "msh/US/FL/2/e/LongFast/!9e9fb878"
        )
        assert channel == "LongFast"
        assert gw == 0x9E9FB878

    def test_extra_path_segments(self):
        """Topics with additional region segments still parse correctly."""
        channel, gw = MqttCollector._parse_mqtt_topic(
            "msh/US/FL/LWS/2/e/LongFast/!3c9ff0bc"
        )
        assert channel == "LongFast"
        assert gw == 0x3C9FF0BC

    def test_short_topic_returns_none(self):
        """Topic with only one segment cannot be parsed."""
        channel, gw = MqttCollector._parse_mqtt_topic("short")
        assert channel is None
        assert gw is None

    def test_empty_topic(self):
        channel, gw = MqttCollector._parse_mqtt_topic("")
        assert channel is None
        assert gw is None

    def test_no_gateway_prefix(self):
        """Gateway ID missing '!' prefix — gateway is None."""
        channel, gw = MqttCollector._parse_mqtt_topic(
            "msh/US/FL/2/json/MediumFast/435730e4"
        )
        assert channel == "MediumFast"
        assert gw is None

    def test_invalid_hex_gateway(self):
        """Invalid hex after '!' — gateway is None."""
        channel, gw = MqttCollector._parse_mqtt_topic(
            "msh/US/FL/2/json/LongFast/!not_hex"
        )
        assert channel == "LongFast"
        assert gw is None

    def test_two_segment_topic(self):
        """Minimal valid topic with just channel and gateway."""
        channel, gw = MqttCollector._parse_mqtt_topic("LongFast/!abcdef01")
        assert channel == "LongFast"
        assert gw == 0xABCDEF01

    def test_empty_channel_name(self):
        """Empty channel segment returns None for channel."""
        channel, gw = MqttCollector._parse_mqtt_topic("msh//!435730e4")
        assert channel is None
        assert gw == 0x435730E4


# ---------------------------------------------------------------------------
# _process_json_message integration tests
# ---------------------------------------------------------------------------


class TestProcessJsonMessageGateway:
    """Tests that _process_json_message extracts gateway from topic."""

    @pytest.mark.asyncio
    async def test_gateway_injected_from_topic(self, collector):
        """JSON messages should get gatewayNodeNum from the MQTT topic."""
        data = {
            "type": "text",
            "from": "!12345678",
            "to": "!ffffffff",
            "id": 99999,
            "channel": 0,
            "text": "Hello",
        }
        topic = "msh/US/FL/2/json/LongFast/!aabbccdd"
        added_objects = []

        mock_db = AsyncMock()
        mock_db.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
        mock_db.commit = AsyncMock()
        # First call: channel lookup by name (no match)
        # Second call: _ensure_channel lookup (no match)
        no_result = MagicMock()
        no_result.scalar = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=no_result)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.collectors.mqtt.async_session_maker", return_value=mock_session):
            await collector._process_json_message(topic, data)

        # Find the Message object
        messages = [o for o in added_objects if isinstance(o, Message)]
        assert len(messages) == 1
        assert messages[0].gateway_node_num == 0xAABBCCDD

    @pytest.mark.asyncio
    async def test_gateway_not_overridden_if_present(self, collector):
        """If gatewayNodeNum is already in data, topic should not override it."""
        data = {
            "type": "text",
            "from": "!12345678",
            "to": "!ffffffff",
            "id": 99998,
            "channel": 0,
            "text": "Hello",
            "gatewayNodeNum": 111,
        }
        topic = "msh/US/FL/2/json/LongFast/!aabbccdd"
        added_objects = []

        mock_db = AsyncMock()
        mock_db.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
        mock_db.commit = AsyncMock()
        no_result = MagicMock()
        no_result.scalar = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=no_result)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.collectors.mqtt.async_session_maker", return_value=mock_session):
            await collector._process_json_message(topic, data)

        messages = [o for o in added_objects if isinstance(o, Message)]
        assert len(messages) == 1
        assert messages[0].gateway_node_num == 111


class TestProcessJsonMessageChannel:
    """Tests that _process_json_message resolves channel from topic."""

    @pytest.mark.asyncio
    async def test_channel_resolved_by_name(self, collector):
        """When a channel with matching name exists, its index replaces data['channel']."""
        data = {
            "type": "text",
            "from": "!12345678",
            "to": "!ffffffff",
            "id": 88888,
            "channel": 0,  # JSON always reports 0
            "text": "Test",
        }
        topic = "msh/US/FL/2/json/LongFast/!aabbccdd"
        added_objects = []

        # Mock channel with index 8 and name "LongFast"
        existing_channel = MagicMock(spec=Channel)
        existing_channel.channel_index = 8
        existing_channel.name = "LongFast"

        mock_db = AsyncMock()
        mock_db.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
        mock_db.commit = AsyncMock()

        # execute calls:
        # 1. channel lookup by name -> returns existing_channel
        # 2. _ensure_channel lookup by index -> returns existing_channel
        result_with_channel = MagicMock()
        result_with_channel.scalar = MagicMock(return_value=existing_channel)
        mock_db.execute = AsyncMock(return_value=result_with_channel)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.collectors.mqtt.async_session_maker", return_value=mock_session):
            await collector._process_json_message(topic, data)

        messages = [o for o in added_objects if isinstance(o, Message)]
        assert len(messages) == 1
        # Channel should be 8 (from DB lookup), not 0 (from JSON)
        assert messages[0].channel == 8

    @pytest.mark.asyncio
    async def test_channel_unchanged_when_no_match(self, collector):
        """When no channel matches the topic name, data['channel'] stays as-is."""
        data = {
            "type": "text",
            "from": "!12345678",
            "to": "!ffffffff",
            "id": 77777,
            "channel": 0,
            "text": "Test",
        }
        topic = "msh/US/FL/2/json/LongFast/!aabbccdd"
        added_objects = []

        mock_db = AsyncMock()
        mock_db.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
        mock_db.commit = AsyncMock()
        no_result = MagicMock()
        no_result.scalar = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=no_result)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.collectors.mqtt.async_session_maker", return_value=mock_session):
            await collector._process_json_message(topic, data)

        messages = [o for o in added_objects if isinstance(o, Message)]
        assert len(messages) == 1
        assert messages[0].channel == 0


# ---------------------------------------------------------------------------
# _ensure_channel name backfill tests
# ---------------------------------------------------------------------------


class TestEnsureChannelNameBackfill:
    """Tests that _ensure_channel updates empty channel names."""

    @pytest.mark.asyncio
    async def test_backfills_empty_name(self, collector):
        """Channel with empty name should be updated when channelId is available."""
        existing = MagicMock(spec=Channel)
        existing.name = None
        existing.channel_index = 8

        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar = MagicMock(return_value=existing)
        mock_db.execute = AsyncMock(return_value=result)

        data = {"channel": 8, "channelId": "LongFast"}
        await collector._ensure_channel(mock_db, data)

        assert existing.name == "LongFast"

    @pytest.mark.asyncio
    async def test_does_not_overwrite_existing_name(self, collector):
        """Channel with an existing name should not be overwritten."""
        existing = MagicMock(spec=Channel)
        existing.name = "OldName"
        existing.channel_index = 8

        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar = MagicMock(return_value=existing)
        mock_db.execute = AsyncMock(return_value=result)

        data = {"channel": 8, "channelId": "NewName"}
        await collector._ensure_channel(mock_db, data)

        assert existing.name == "OldName"

    @pytest.mark.asyncio
    async def test_creates_channel_with_name(self, collector):
        """New channel should be created with channelId as name."""
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.add = MagicMock()

        data = {"channel": 31, "channelId": "MediumFast"}
        await collector._ensure_channel(mock_db, data)

        assert mock_db.add.call_count == 1
        new_channel = mock_db.add.call_args[0][0]
        assert isinstance(new_channel, Channel)
        assert new_channel.name == "MediumFast"
        assert new_channel.channel_index == 31

    @pytest.mark.asyncio
    async def test_no_channel_index_is_noop(self, collector):
        """No channel index in data should be a no-op."""
        mock_db = AsyncMock()
        data = {"channelId": "LongFast"}  # no "channel" key
        await collector._ensure_channel(mock_db, data)
        mock_db.execute.assert_not_called()


# ---------------------------------------------------------------------------
# _process_protobuf_message channelId injection
# ---------------------------------------------------------------------------


class TestProtobufChannelIdInjection:
    """Tests that protobuf path injects channelId from topic."""

    @pytest.mark.asyncio
    async def test_channelid_injected_when_missing(self, collector):
        """Decoded protobuf without channelId should get it from topic."""
        decoded = {
            "portnum": "TEXT_MESSAGE_APP",
            "from": 12345678,
            "to": 4294967295,
            "id": 55555,
            "channel": 8,
            "text": "Hello",
        }

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        no_result = MagicMock()
        no_result.scalar = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=no_result)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        topic = "msh/US/FL/2/e/LongFast/!9e9fb878"

        with (
            patch("app.collectors.mqtt.async_session_maker", return_value=mock_session),
            patch.object(collector, "_get_encryption_keys", return_value=[]),
            patch(
                "app.collectors.mqtt.decode_meshtastic_packet",
                return_value=decoded,
            ),
        ):
            await collector._process_protobuf_message(topic, b"\x00")

        # channelId should have been injected from topic
        assert decoded["channelId"] == "LongFast"

    @pytest.mark.asyncio
    async def test_channelid_not_overridden_when_present(self, collector):
        """Decoded protobuf with channelId should keep its original value."""
        decoded = {
            "portnum": "TEXT_MESSAGE_APP",
            "from": 12345678,
            "to": 4294967295,
            "id": 55556,
            "channel": 8,
            "channelId": "OriginalChannel",
            "text": "Hello",
        }

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        no_result = MagicMock()
        no_result.scalar = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=no_result)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        topic = "msh/US/FL/2/e/LongFast/!9e9fb878"

        with (
            patch("app.collectors.mqtt.async_session_maker", return_value=mock_session),
            patch.object(collector, "_get_encryption_keys", return_value=[]),
            patch(
                "app.collectors.mqtt.decode_meshtastic_packet",
                return_value=decoded,
            ),
        ):
            await collector._process_protobuf_message(topic, b"\x00")

        assert decoded["channelId"] == "OriginalChannel"
