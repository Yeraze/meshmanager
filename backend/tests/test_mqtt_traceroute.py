"""Tests for MQTT traceroute handling."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.collectors.mqtt import MqttCollector
from app.models import Source


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


@pytest.fixture
def mock_db():
    """Create a mock DB session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    # Default execute returns a result with empty .all() for route position lookups
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_result.__iter__ = lambda self: iter([])
    db.execute = AsyncMock(return_value=mock_result)
    return db


class TestHandleTracerouteJSON:
    """Tests for JSON traceroute handling."""

    async def test_basic_json_traceroute(self, collector, mock_db):
        """Traceroute with integer route arrays stores correctly."""
        data = {
            "type": "traceroute",
            "from": 111,
            "to": 222,
            "payload": {
                "route": [333, 444],
                "route_back": [444, 333],
                "snr_towards": [10, 20],
                "snr_back": [15, 25],
            },
            "timestamp": 1770481094,
        }
        await collector._handle_traceroute(mock_db, data)

        mock_db.add.assert_called_once()
        tr = mock_db.add.call_args[0][0]
        # from/to should be swapped (requester/responder convention)
        assert tr.from_node_num == 222
        assert tr.to_node_num == 111
        assert tr.route == [333, 444]
        assert tr.route_back == [444, 333]
        assert tr.snr_towards == [10, 20]
        assert tr.snr_back == [15, 25]
        assert tr.source_id == "test-source-id"

    async def test_string_route_entries_resolved(self, collector, mock_db):
        """Route arrays with node names (strings) are resolved via DB lookup."""
        # Mock DB to return node_num mappings for the names
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([
            MagicMock(long_name="Node A", node_num=1001),
            MagicMock(long_name="Node B", node_num=1002),
            MagicMock(long_name="Node C", node_num=1003),
        ])
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = {
            "type": "traceroute",
            "from": 111,
            "to": 222,
            "payload": {
                "route": ["Node A", "Node B", "Node C"],
                "route_back": ["Node C", "Node A"],
                "snr_towards": [6.25, 10],
                "snr_back": [-0.25],
            },
            "timestamp": 1770481094,
        }
        await collector._handle_traceroute(mock_db, data)

        tr = mock_db.add.call_args[0][0]
        assert tr.route == [1001, 1002, 1003]
        assert tr.route_back == [1003, 1001]

    async def test_mixed_route_entries_resolved(self, collector, mock_db):
        """Route arrays with mixed types resolve names and keep ints."""
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([
            MagicMock(long_name="Node A", node_num=1001),
            MagicMock(long_name="Node B", node_num=1002),
        ])
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = {
            "from": 111,
            "to": 222,
            "payload": {
                "route": ["Node A", 333, "Node B", 444],
            },
        }
        await collector._handle_traceroute(mock_db, data)

        tr = mock_db.add.call_args[0][0]
        assert tr.route == [1001, 333, 1002, 444]

    async def test_float_snr_converted_to_db4(self, collector, mock_db):
        """Float SNR values (actual dB) are converted to int (dB * 4)."""
        data = {
            "from": 111,
            "to": 222,
            "payload": {
                "route": [],
                "snr_towards": [6.25, -0.5],
                "snr_back": [2.75],
            },
        }
        await collector._handle_traceroute(mock_db, data)

        tr = mock_db.add.call_args[0][0]
        assert tr.snr_towards == [25, -2]
        assert tr.snr_back == [11]

    async def test_int_snr_preserved(self, collector, mock_db):
        """Integer SNR values (already dB*4) are preserved as-is."""
        data = {
            "from": 111,
            "to": 222,
            "payload": {
                "route": [],
                "snr_towards": [25, -8],
            },
        }
        await collector._handle_traceroute(mock_db, data)

        tr = mock_db.add.call_args[0][0]
        assert tr.snr_towards == [25, -8]

    async def test_hex_node_ids(self, collector, mock_db):
        """Hex node IDs (e.g. !a2e4ff4c) are converted to integers."""
        data = {
            "from": "!a2e4ff4c",
            "to": "!69859134",
            "payload": {"route": []},
        }
        await collector._handle_traceroute(mock_db, data)

        tr = mock_db.add.call_args[0][0]
        # Swapped: from=to_original, to=from_original
        assert tr.from_node_num == 0x69859134
        assert tr.to_node_num == 0xA2E4FF4C

    async def test_from_to_swap(self, collector, mock_db):
        """In TRACEROUTE_APP replies, from/to are swapped to match MeshMonitor."""
        data = {
            "from": 100,  # responder
            "to": 200,  # requester
            "payload": {"route": []},
        }
        await collector._handle_traceroute(mock_db, data)

        tr = mock_db.add.call_args[0][0]
        assert tr.from_node_num == 200  # requester becomes from
        assert tr.to_node_num == 100  # responder becomes to

    async def test_missing_from_skips(self, collector, mock_db):
        """Missing 'from' field causes handler to return without storing."""
        data = {"to": 222, "payload": {"route": []}}
        await collector._handle_traceroute(mock_db, data)
        mock_db.add.assert_not_called()

    async def test_missing_to_skips(self, collector, mock_db):
        """Missing 'to' field causes handler to return without storing."""
        data = {"from": 111, "payload": {"route": []}}
        await collector._handle_traceroute(mock_db, data)
        mock_db.add.assert_not_called()

    async def test_timestamp_parsed(self, collector, mock_db):
        """Unix timestamp from JSON is parsed into received_at."""
        data = {
            "from": 111,
            "to": 222,
            "payload": {"route": []},
            "timestamp": 1770481094,
        }
        await collector._handle_traceroute(mock_db, data)

        tr = mock_db.add.call_args[0][0]
        assert tr.received_at is not None
        assert tr.received_at.tzinfo is not None  # timezone-aware

    async def test_camelcase_json_fields(self, collector, mock_db):
        """CamelCase JSON field names (snrTowards, routeBack) are handled."""
        data = {
            "from": 111,
            "to": 222,
            "payload": {
                "route": [333],
                "routeBack": [333],
                "snrTowards": [5],
                "snrBack": [10],
            },
        }
        await collector._handle_traceroute(mock_db, data)

        tr = mock_db.add.call_args[0][0]
        assert tr.route == [333]
        assert tr.route_back == [333]
        assert tr.snr_towards == [5]
        assert tr.snr_back == [10]

    async def test_flattened_top_level_fields(self, collector, mock_db):
        """Handles MQTT bridges that put route fields at top level with non-dict payload."""
        data = {
            "from": 111,
            "to": 222,
            "payload": "raw-string-payload",
            "route": [333],
            "route_back": [444],
            "snr_towards": [5],
            "snr_back": [10],
        }
        await collector._handle_traceroute(mock_db, data)

        tr = mock_db.add.call_args[0][0]
        assert tr.route == [333]
        assert tr.route_back == [444]

    async def test_empty_snr_arrays_become_none(self, collector, mock_db):
        """Empty SNR arrays are stored as None."""
        data = {
            "from": 111,
            "to": 222,
            "payload": {
                "route": [],
                "snr_towards": [],
                "snr_back": [],
            },
        }
        await collector._handle_traceroute(mock_db, data)

        tr = mock_db.add.call_args[0][0]
        assert tr.snr_towards is None
        assert tr.snr_back is None


    async def test_unresolvable_names_dropped(self, collector, mock_db):
        """String route entries not found in DB are dropped."""
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([
            MagicMock(long_name="Known Node", node_num=999),
        ])
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = {
            "from": 111,
            "to": 222,
            "payload": {
                "route": ["Known Node", "Unknown Node"],
            },
        }
        await collector._handle_traceroute(mock_db, data)

        tr = mock_db.add.call_args[0][0]
        assert tr.route == [999]


class TestResolveRouteNames:
    """Tests for the _resolve_route_names helper."""

    async def test_empty_list(self, collector, mock_db):
        result = await collector._resolve_route_names(mock_db, [])
        assert result == []

    async def test_all_ints_no_db_query(self, collector, mock_db):
        """All-integer routes skip the DB query entirely."""
        result = await collector._resolve_route_names(mock_db, [111, 222, 333])
        assert result == [111, 222, 333]
        mock_db.execute.assert_not_called()

    async def test_all_strings_resolved(self, collector, mock_db):
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([
            MagicMock(long_name="Alpha", node_num=100),
            MagicMock(long_name="Beta", node_num=200),
        ])
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await collector._resolve_route_names(mock_db, ["Alpha", "Beta"])
        assert result == [100, 200]

    async def test_preserves_order(self, collector, mock_db):
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([
            MagicMock(long_name="B", node_num=200),
            MagicMock(long_name="A", node_num=100),
        ])
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await collector._resolve_route_names(mock_db, ["A", 555, "B"])
        assert result == [100, 555, 200]

    async def test_duplicate_names_resolved(self, collector, mock_db):
        """Duplicate node names in route are each resolved correctly."""
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([
            MagicMock(long_name="Relay", node_num=500),
        ])
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await collector._resolve_route_names(mock_db, ["Relay", 111, "Relay"])
        assert result == [500, 111, 500]


class TestHandleTracerouteProtobuf:
    """Tests for protobuf traceroute handling."""

    async def test_protobuf_route_discovery(self, collector, mock_db):
        """Protobuf RouteDiscovery payload is decoded correctly."""
        try:
            from meshtastic import mesh_pb2
        except ImportError:
            pytest.skip("meshtastic library not available")

        rd = mesh_pb2.RouteDiscovery()
        rd.route.extend([333, 444])
        rd.route_back.extend([444, 333])
        rd.snr_towards.extend([25, -8])
        rd.snr_back.extend([12])

        data = {
            "from": 111,
            "to": 222,
            "payload": rd.SerializeToString(),
        }
        await collector._handle_traceroute(mock_db, data)

        tr = mock_db.add.call_args[0][0]
        assert tr.route == [333, 444]
        assert tr.route_back == [444, 333]
        assert tr.snr_towards == [25, -8]
        assert tr.snr_back == [12]

    async def test_protobuf_decode_failure_skips(self, collector, mock_db):
        """Invalid protobuf payload causes graceful skip."""
        data = {
            "from": 111,
            "to": 222,
            "payload": b"\xff\xff\xff\xff\xff",
        }
        # Should not raise, should just skip
        await collector._handle_traceroute(mock_db, data)
        # Depending on whether meshtastic is available and the bytes parse,
        # we either get an add or a skip — but no exception
        # (protobuf is permissive with unknown bytes, may still parse)


class TestCoerceSNRArray:
    """Tests for the _coerce_snr_array helper."""

    def test_none_returns_none(self):
        assert MqttCollector._coerce_snr_array(None) is None

    def test_empty_list_returns_none(self):
        assert MqttCollector._coerce_snr_array([]) is None

    def test_ints_preserved(self):
        assert MqttCollector._coerce_snr_array([10, -5, 0]) == [10, -5, 0]

    def test_floats_converted_to_db4(self):
        assert MqttCollector._coerce_snr_array([2.5, -1.25, 0.0]) == [10, -5, 0]

    def test_mixed_int_float(self):
        assert MqttCollector._coerce_snr_array([10, 2.5]) == [10, 10]

    def test_rounding(self):
        # 3.3 * 4 = 13.2 -> rounds to 13
        assert MqttCollector._coerce_snr_array([3.3]) == [13]


class TestProtobufDispatcher:
    """Tests for TRACEROUTE_APP routing in _handle_decoded_packet."""

    async def test_traceroute_app_dispatched(self, collector, mock_db):
        """TRACEROUTE_APP portnum routes to _handle_traceroute."""
        decoded = {
            "portnum": "TRACEROUTE_APP",
            "from": 111,
            "to": 222,
            "payload": b"",
        }
        with patch.object(collector, "_handle_traceroute", new_callable=AsyncMock) as mock:
            await collector._handle_decoded_packet(mock_db, decoded)
            mock.assert_called_once_with(mock_db, decoded)

    async def test_unknown_portnum_ignored(self, collector, mock_db):
        """Unknown portnums don't cause errors."""
        decoded = {"portnum": "UNKNOWN_APP", "from": 111, "to": 222}
        # Should not raise
        await collector._handle_decoded_packet(mock_db, decoded)
