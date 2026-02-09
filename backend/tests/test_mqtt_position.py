"""Tests for MQTT position handling and query compatibility with MQTT-style data."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.collectors.mqtt import MqttCollector
from app.models import Source, Telemetry
from app.models.telemetry import TelemetryType


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
    # Default: no existing node found
    mock_result = MagicMock()
    mock_result.scalar = MagicMock(return_value=None)
    db.execute = AsyncMock(return_value=mock_result)
    return db


class TestHandlePositionCreatesNodeAndTelemetry:
    """Tests that _handle_position() creates both a Node and a Telemetry row."""

    async def test_creates_node_and_telemetry(self, collector, mock_db):
        """Position handler should call db.add() twice: once for Node, once for Telemetry."""
        data = {
            "from": 12345678,
            "payload": {
                "latitude": 40.7128,
                "longitude": -74.006,
                "altitude": 10,
            },
            "rxTime": 1770481094,
        }
        await collector._handle_position(mock_db, data)

        # Should have added 2 objects: Node and Telemetry
        assert mock_db.add.call_count == 2

    async def test_telemetry_row_has_position_type(self, collector, mock_db):
        """The Telemetry row should have telemetry_type=POSITION."""
        data = {
            "from": 12345678,
            "payload": {
                "latitude": 40.7128,
                "longitude": -74.006,
                "altitude": 10,
            },
        }
        await collector._handle_position(mock_db, data)

        # Find the Telemetry object among the add() calls
        telemetry = None
        for call in mock_db.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, Telemetry):
                telemetry = obj
                break

        assert telemetry is not None, "No Telemetry object was added to the session"
        assert telemetry.telemetry_type == TelemetryType.POSITION

    async def test_telemetry_row_has_position_data(self, collector, mock_db):
        """The Telemetry row should contain lat, lon, and altitude."""
        data = {
            "from": 12345678,
            "payload": {
                "latitude": 40.7128,
                "longitude": -74.006,
                "altitude": 150,
            },
        }
        await collector._handle_position(mock_db, data)

        telemetry = None
        for call in mock_db.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, Telemetry):
                telemetry = obj
                break

        assert telemetry is not None
        assert telemetry.latitude == 40.7128
        assert telemetry.longitude == -74.006
        assert telemetry.altitude == 150

    async def test_telemetry_row_has_source_and_node(self, collector, mock_db):
        """The Telemetry row should have source_id and node_num set."""
        data = {
            "from": 12345678,
            "payload": {
                "latitude": 40.7128,
                "longitude": -74.006,
            },
        }
        await collector._handle_position(mock_db, data)

        telemetry = None
        for call in mock_db.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, Telemetry):
                telemetry = obj
                break

        assert telemetry is not None
        assert telemetry.source_id == "test-source-id"
        assert telemetry.node_num == 12345678

    async def test_telemetry_metric_name_is_none(self, collector, mock_db):
        """MQTT position Telemetry rows have metric_name=None (MQTT convention)."""
        data = {
            "from": 12345678,
            "payload": {
                "latitude": 40.7128,
                "longitude": -74.006,
            },
        }
        await collector._handle_position(mock_db, data)

        telemetry = None
        for call in mock_db.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, Telemetry):
                telemetry = obj
                break

        assert telemetry is not None
        assert telemetry.metric_name is None

    async def test_telemetry_received_at_from_rxtime(self, collector, mock_db):
        """Telemetry received_at should be parsed from rxTime."""
        data = {
            "from": 12345678,
            "payload": {
                "latitude": 40.7128,
                "longitude": -74.006,
            },
            "rxTime": 1770481094,
        }
        await collector._handle_position(mock_db, data)

        telemetry = None
        for call in mock_db.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, Telemetry):
                telemetry = obj
                break

        assert telemetry is not None
        assert telemetry.received_at is not None
        assert telemetry.received_at.tzinfo is not None

    async def test_hex_node_id_converted(self, collector, mock_db):
        """Hex node IDs (e.g. !a2e4ff4c) are converted to integers."""
        data = {
            "from": "!a2e4ff4c",
            "payload": {
                "latitude": 40.7128,
                "longitude": -74.006,
            },
        }
        await collector._handle_position(mock_db, data)

        telemetry = None
        for call in mock_db.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, Telemetry):
                telemetry = obj
                break

        assert telemetry is not None
        assert telemetry.node_num == 0xA2E4FF4C

    async def test_missing_lat_lon_skips(self, collector, mock_db):
        """Position with no lat/lon should not create any objects."""
        data = {
            "from": 12345678,
            "payload": {
                "altitude": 10,
            },
        }
        await collector._handle_position(mock_db, data)

        # Only the execute call for node lookup, no add() calls
        mock_db.add.assert_not_called()

    async def test_missing_from_skips(self, collector, mock_db):
        """Missing 'from' field should skip without adding anything."""
        data = {
            "payload": {
                "latitude": 40.7128,
                "longitude": -74.006,
            },
        }
        await collector._handle_position(mock_db, data)
        mock_db.add.assert_not_called()

    async def test_altitude_none_when_missing(self, collector, mock_db):
        """Altitude should be None when not provided."""
        data = {
            "from": 12345678,
            "payload": {
                "latitude": 40.7128,
                "longitude": -74.006,
            },
        }
        await collector._handle_position(mock_db, data)

        telemetry = None
        for call in mock_db.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, Telemetry):
                telemetry = obj
                break

        assert telemetry is not None
        assert telemetry.altitude is None

    async def test_integer_coordinate_format(self, collector, mock_db):
        """Position with integer coordinates (1e-7 format) should be converted."""
        data = {
            "from": 12345678,
            "payload": {
                "latitudeI": 407128000,
                "longitudeI": -740060000,
            },
        }
        await collector._handle_position(mock_db, data)

        telemetry = None
        for call in mock_db.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, Telemetry):
                telemetry = obj
                break

        assert telemetry is not None
        assert abs(telemetry.latitude - 40.7128) < 0.0001
        assert abs(telemetry.longitude - (-74.006)) < 0.0001


class TestTelemetryModelAcceptsPositionData:
    """Tests that the Telemetry model can hold MQTT-style position data."""

    def test_telemetry_with_position_fields(self):
        """Telemetry model accepts position fields (lat, lon, altitude)."""
        t = Telemetry(
            source_id="test-source",
            node_num=12345678,
            telemetry_type=TelemetryType.POSITION,
            latitude=40.7128,
            longitude=-74.006,
            altitude=10,
        )
        assert t.latitude == 40.7128
        assert t.longitude == -74.006
        assert t.altitude == 10
        assert t.telemetry_type == TelemetryType.POSITION

    def test_telemetry_position_with_metric_name_none(self):
        """MQTT-style telemetry has metric_name=None but columns populated."""
        t = Telemetry(
            source_id="test-source",
            node_num=12345678,
            telemetry_type=TelemetryType.POSITION,
            latitude=40.7128,
            longitude=-74.006,
            metric_name=None,
        )
        assert t.metric_name is None
        assert t.latitude is not None
        assert t.longitude is not None

    def test_telemetry_device_with_metric_name_none(self):
        """MQTT-style device telemetry has metric_name=None but columns populated."""
        t = Telemetry(
            source_id="test-source",
            node_num=12345678,
            telemetry_type=TelemetryType.DEVICE,
            channel_utilization=25.5,
            battery_level=85,
            voltage=4.1,
            metric_name=None,
        )
        assert t.metric_name is None
        assert t.channel_utilization == 25.5
        assert t.battery_level == 85

    def test_telemetry_meshmonitor_style_with_metric_name(self):
        """MeshMonitor-style telemetry has metric_name set."""
        t = Telemetry(
            source_id="test-source",
            node_num=12345678,
            telemetry_type=TelemetryType.DEVICE,
            channel_utilization=25.5,
            metric_name="channelUtilization",
        )
        assert t.metric_name == "channelUtilization"
        assert t.channel_utilization == 25.5

    def test_telemetry_position_type_enum(self):
        """TelemetryType.POSITION exists and has the correct value."""
        assert TelemetryType.POSITION == "position"
        assert TelemetryType.POSITION.value == "position"


class TestExtractCoordinate:
    """Tests for the _extract_coordinate static method."""

    def test_float_key(self):
        data = {"latitude": 40.7128}
        result = MqttCollector._extract_coordinate(data, "latitude", "lat", "latitude_i")
        assert result == 40.7128

    def test_short_key(self):
        data = {"lat": 40.7128}
        result = MqttCollector._extract_coordinate(data, "latitude", "lat", "latitude_i")
        assert result == 40.7128

    def test_int_key(self):
        data = {"latitude_i": 407128000}
        result = MqttCollector._extract_coordinate(data, "latitude", "lat", "latitude_i")
        assert abs(result - 40.7128) < 0.0001

    def test_camelcase_int_key(self):
        """Protobuf MessageToDict uses camelCase: latitudeI."""
        data = {"latitudeI": 407128000}
        result = MqttCollector._extract_coordinate(data, "latitude", "lat", "latitude_i")
        assert abs(result - 40.7128) < 0.0001

    def test_no_coordinate_returns_none(self):
        data = {"other_field": 123}
        result = MqttCollector._extract_coordinate(data, "latitude", "lat", "latitude_i")
        assert result is None

    def test_zero_coordinate(self):
        """Zero is a valid coordinate (equator/prime meridian)."""
        data = {"latitude": 0.0}
        result = MqttCollector._extract_coordinate(data, "latitude", "lat", "latitude_i")
        assert result == 0.0

    def test_longitude_camelcase(self):
        """longitudeI camelCase key should work."""
        data = {"longitudeI": -740060000}
        result = MqttCollector._extract_coordinate(data, "longitude", "lon", "longitude_i")
        assert abs(result - (-74.006)) < 0.0001
