"""Tests for MQTT PaxCounter handling."""

from unittest.mock import AsyncMock, MagicMock

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
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_result.__iter__ = lambda self: iter([])
    mock_result.scalar.return_value = None
    db.execute = AsyncMock(return_value=mock_result)
    return db


def _get_all_insert_params(mock_db):
    """Extract values dicts from all pg_insert execute calls."""
    results = []
    for call in mock_db.execute.call_args_list:
        stmt = call[0][0]
        compiled = stmt.compile()
        results.append(compiled.params)
    return results


class TestHandlePaxcounter:
    """Tests for PaxCounter packet handling."""

    async def test_standard_paxcounter(self, collector, mock_db):
        """Standard PaxCounter with wifi, ble, uptime stores three telemetry rows."""
        data = {
            "from": 12345,
            "to": 4294967295,
            "id": 99,
            "portnum": "PAXCOUNTER_APP",
            "payload": {"wifi": 15, "ble": 8, "uptime": 3600},
            "rxTime": 1770481094,
        }
        await collector._handle_paxcounter(mock_db, data)

        params_list = _get_all_insert_params(mock_db)
        assert len(params_list) == 3

        metric_names = {p["metric_name"] for p in params_list}
        assert metric_names == {"paxcounter_wifi", "paxcounter_ble", "paxcounter_uptime"}

        for p in params_list:
            assert p["source_id"] == "test-source-id"
            assert p["node_num"] == 12345
            assert p["meshtastic_id"] == 99

        # Check specific values
        wifi_row = next(p for p in params_list if p["metric_name"] == "paxcounter_wifi")
        assert wifi_row["raw_value"] == 15.0

        ble_row = next(p for p in params_list if p["metric_name"] == "paxcounter_ble")
        assert ble_row["raw_value"] == 8.0

        uptime_row = next(p for p in params_list if p["metric_name"] == "paxcounter_uptime")
        assert uptime_row["raw_value"] == 3600.0

    async def test_partial_data_wifi_only(self, collector, mock_db):
        """PaxCounter with only wifi field stores one row."""
        data = {
            "from": 12345,
            "portnum": "PAXCOUNTER_APP",
            "payload": {"wifi": 42},
        }
        await collector._handle_paxcounter(mock_db, data)

        params_list = _get_all_insert_params(mock_db)
        assert len(params_list) == 1
        assert params_list[0]["metric_name"] == "paxcounter_wifi"
        assert params_list[0]["raw_value"] == 42.0

    async def test_zero_values_stored(self, collector, mock_db):
        """Zero is a valid value and should be stored."""
        data = {
            "from": 12345,
            "portnum": "PAXCOUNTER_APP",
            "payload": {"wifi": 0, "ble": 0, "uptime": 0},
        }
        await collector._handle_paxcounter(mock_db, data)

        params_list = _get_all_insert_params(mock_db)
        assert len(params_list) == 3
        for p in params_list:
            assert p["raw_value"] == 0.0

    async def test_missing_from_skips(self, collector, mock_db):
        """Missing 'from' field causes handler to skip."""
        data = {
            "portnum": "PAXCOUNTER_APP",
            "payload": {"wifi": 10},
        }
        await collector._handle_paxcounter(mock_db, data)
        mock_db.execute.assert_not_called()

    async def test_non_dict_payload_skips(self, collector, mock_db):
        """Non-dict payload causes handler to skip."""
        data = {
            "from": 12345,
            "portnum": "PAXCOUNTER_APP",
            "payload": b"raw-bytes",
        }
        await collector._handle_paxcounter(mock_db, data)
        mock_db.execute.assert_not_called()

    async def test_empty_payload_no_rows(self, collector, mock_db):
        """Empty dict payload stores no rows."""
        data = {
            "from": 12345,
            "portnum": "PAXCOUNTER_APP",
            "payload": {},
        }
        await collector._handle_paxcounter(mock_db, data)
        mock_db.execute.assert_not_called()

    async def test_hex_node_id(self, collector, mock_db):
        """Hex node ID (e.g. !a2e4ff4c) is converted to integer."""
        data = {
            "from": "!a2e4ff4c",
            "portnum": "PAXCOUNTER_APP",
            "payload": {"wifi": 5},
        }
        await collector._handle_paxcounter(mock_db, data)

        params_list = _get_all_insert_params(mock_db)
        assert len(params_list) == 1
        assert params_list[0]["node_num"] == 0xA2E4FF4C

    async def test_non_numeric_values_skipped(self, collector, mock_db):
        """Non-numeric values in payload are skipped."""
        data = {
            "from": 12345,
            "portnum": "PAXCOUNTER_APP",
            "payload": {"wifi": "not-a-number", "ble": 5},
        }
        await collector._handle_paxcounter(mock_db, data)

        params_list = _get_all_insert_params(mock_db)
        assert len(params_list) == 1
        assert params_list[0]["metric_name"] == "paxcounter_ble"


class TestPaxcounterDispatch:
    """Tests for PAXCOUNTER_APP routing in _handle_decoded_packet."""

    async def test_paxcounter_dispatched(self, collector, mock_db):
        """PAXCOUNTER_APP portnum routes to _handle_paxcounter."""
        from unittest.mock import patch

        decoded = {
            "portnum": "PAXCOUNTER_APP",
            "from": 12345,
            "to": 4294967295,
            "payload": {"wifi": 10, "ble": 3},
        }
        with patch.object(collector, "_handle_paxcounter", new_callable=AsyncMock) as mock:
            await collector._handle_decoded_packet(mock_db, decoded)
            mock.assert_called_once_with(mock_db, decoded)
