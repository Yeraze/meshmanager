"""Tests for MeshMonitorCollector._insert_telemetry using the telemetry registry."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.collectors.meshmonitor import MeshMonitorCollector
from app.models.telemetry import TelemetryType


@pytest.fixture()
def collector():
    """Create a MeshMonitorCollector with a fake source."""
    source = SimpleNamespace(
        id="source-1",
        name="test-source",
        url="http://localhost",
        api_token="test-token",
        poll_interval_seconds=60,
        historical_days_back=7,
    )
    return MeshMonitorCollector(source)


@pytest.fixture()
def mock_db():
    """Create a mock async db session that records executed statements."""
    db = AsyncMock()
    # Default: rowcount=1 (inserted)
    result = MagicMock()
    result.rowcount = 1
    db.execute = AsyncMock(return_value=result)
    return db


def _extract_values(db_mock) -> dict:
    """Extract the values dict from the first pg_insert call."""
    call_args = db_mock.execute.call_args
    stmt = call_args[0][0]
    # SQLAlchemy pg_insert compiles values into the statement's parameters
    compile = stmt.compile()
    return compile.params


def _extract_all_values(db_mock) -> list[dict]:
    """Extract values dicts from all pg_insert calls."""
    results = []
    for call in db_mock.execute.call_args_list:
        stmt = call[0][0]
        compile = stmt.compile()
        results.append(compile.params)
    return results


# -----------------------------------------------------------------------
# Flat format tests
# -----------------------------------------------------------------------


class TestFlatFormat:
    """Tests for MeshMonitor flat format (telemetryType + value)."""

    @pytest.mark.asyncio
    async def test_battery_level(self, collector, mock_db):
        """batteryLevel should map to DEVICE type and populate dedicated column."""
        telem = {
            "nodeNum": 12345,
            "telemetryType": "batteryLevel",
            "value": 86,
            "timestamp": 1700000000000,
        }
        result = await collector._insert_telemetry(mock_db, telem)

        assert result is True
        vals = _extract_values(mock_db)
        assert vals["node_num"] == 12345
        assert vals["metric_name"] == "battery_level"
        assert vals["telemetry_type"] == TelemetryType.DEVICE
        assert vals["raw_value"] == 86.0
        assert vals["battery_level"] == 86

    @pytest.mark.asyncio
    async def test_temperature(self, collector, mock_db):
        """temperature should map to ENVIRONMENT type and populate dedicated column."""
        telem = {
            "nodeNum": 12345,
            "telemetryType": "temperature",
            "value": 22.5,
            "timestamp": 1700000000000,
        }
        result = await collector._insert_telemetry(mock_db, telem)

        assert result is True
        vals = _extract_values(mock_db)
        assert vals["telemetry_type"] == TelemetryType.ENVIRONMENT
        assert vals["raw_value"] == 22.5
        assert vals["temperature"] == 22.5

    @pytest.mark.asyncio
    async def test_voltage_dedicated_column(self, collector, mock_db):
        """voltage should populate the voltage dedicated column."""
        telem = {
            "nodeNum": 12345,
            "telemetryType": "voltage",
            "value": 3.85,
            "timestamp": 1700000000000,
        }
        result = await collector._insert_telemetry(mock_db, telem)

        assert result is True
        vals = _extract_values(mock_db)
        assert vals["telemetry_type"] == TelemetryType.DEVICE
        assert vals["raw_value"] == 3.85
        assert vals["voltage"] == 3.85

    @pytest.mark.asyncio
    async def test_new_metric_num_online_nodes(self, collector, mock_db):
        """numOnlineNodes (new metric) should use LOCAL_STATS type via registry."""
        telem = {
            "nodeNum": 12345,
            "telemetryType": "numOnlineNodes",
            "value": 42,
            "timestamp": 1700000000000,
        }
        result = await collector._insert_telemetry(mock_db, telem)

        assert result is True
        vals = _extract_values(mock_db)
        assert vals["telemetry_type"] == TelemetryType.LOCAL_STATS
        assert vals["raw_value"] == 42.0
        # numOnlineNodes has no dedicated column
        assert "battery_level" not in vals

    @pytest.mark.asyncio
    async def test_new_metric_pm25_standard(self, collector, mock_db):
        """pm25Standard (new metric) should use AIR_QUALITY type via registry."""
        telem = {
            "nodeNum": 12345,
            "telemetryType": "pm25Standard",
            "value": 12.3,
            "timestamp": 1700000000000,
        }
        result = await collector._insert_telemetry(mock_db, telem)

        assert result is True
        vals = _extract_values(mock_db)
        assert vals["telemetry_type"] == TelemetryType.AIR_QUALITY
        assert vals["raw_value"] == 12.3

    @pytest.mark.asyncio
    async def test_unknown_metric_falls_back_to_device(self, collector, mock_db):
        """An unknown telemetryType should fall back to DEVICE type."""
        telem = {
            "nodeNum": 12345,
            "telemetryType": "unknownMetricXyz",
            "value": 99,
            "timestamp": 1700000000000,
        }
        result = await collector._insert_telemetry(mock_db, telem)

        assert result is True
        vals = _extract_values(mock_db)
        assert vals["telemetry_type"] == TelemetryType.DEVICE
        assert vals["raw_value"] == 99.0
        assert vals["metric_name"] == "unknownMetricXyz"
        # No dedicated column for unknown metrics
        assert "battery_level" not in vals

    @pytest.mark.asyncio
    async def test_raw_value_always_populated(self, collector, mock_db):
        """raw_value should always be populated for flat format."""
        telem = {
            "nodeNum": 12345,
            "telemetryType": "channelUtilization",
            "value": 0,  # zero is a valid value
            "timestamp": 1700000000000,
        }
        result = await collector._insert_telemetry(mock_db, telem)

        assert result is True
        vals = _extract_values(mock_db)
        assert vals["raw_value"] == 0.0
        assert vals["channel_utilization"] == 0

    @pytest.mark.asyncio
    async def test_no_node_num_returns_false(self, collector, mock_db):
        """Missing nodeNum should return False."""
        telem = {
            "telemetryType": "batteryLevel",
            "value": 86,
        }
        result = await collector._insert_telemetry(mock_db, telem)
        assert result is False
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_returns_false(self, collector, mock_db):
        """When ON CONFLICT DO NOTHING hits a duplicate, rowcount=0 → returns False."""
        dup_result = MagicMock()
        dup_result.rowcount = 0
        mock_db.execute = AsyncMock(return_value=dup_result)

        telem = {
            "nodeNum": 12345,
            "telemetryType": "batteryLevel",
            "value": 86,
            "timestamp": 1700000000000,
        }
        result = await collector._insert_telemetry(mock_db, telem)
        assert result is False

    @pytest.mark.asyncio
    async def test_timestamp_from_created_at(self, collector, mock_db):
        """Should use createdAt when timestamp is missing."""
        ts = 1700000000000
        telem = {
            "nodeNum": 12345,
            "telemetryType": "voltage",
            "value": 3.8,
            "createdAt": ts,
        }
        await collector._insert_telemetry(mock_db, telem)

        vals = _extract_values(mock_db)
        expected = datetime.fromtimestamp(ts / 1000, tz=UTC)
        assert vals["received_at"] == expected


# -----------------------------------------------------------------------
# Nested format tests
# -----------------------------------------------------------------------


class TestNestedFormat:
    """Tests for nested format (deviceMetrics, environmentMetrics, etc.)."""

    @pytest.mark.asyncio
    async def test_device_metrics(self, collector, mock_db):
        """deviceMetrics sub-message should insert individual metric rows."""
        telem = {
            "nodeNum": 12345,
            "deviceMetrics": {
                "batteryLevel": 80,
                "voltage": 3.9,
            },
        }
        result = await collector._insert_telemetry(mock_db, telem)

        assert result is True
        all_vals = _extract_all_values(mock_db)
        assert len(all_vals) == 2

        metric_names = {v["metric_name"] for v in all_vals}
        assert metric_names == {"battery_level", "voltage"}

        for v in all_vals:
            assert v["telemetry_type"] == TelemetryType.DEVICE
            assert v["raw_value"] is not None

        # Check dedicated columns
        battery_row = next(v for v in all_vals if v["metric_name"] == "battery_level")
        assert battery_row["battery_level"] == 80
        assert battery_row["raw_value"] == 80.0

        voltage_row = next(v for v in all_vals if v["metric_name"] == "voltage")
        assert voltage_row["voltage"] == 3.9
        assert voltage_row["raw_value"] == 3.9

    @pytest.mark.asyncio
    async def test_environment_metrics(self, collector, mock_db):
        """environmentMetrics sub-message should use ENVIRONMENT type."""
        telem = {
            "nodeNum": 12345,
            "environmentMetrics": {
                "temperature": 23.5,
                "relativeHumidity": 55.2,
                "barometricPressure": 1013.25,
            },
        }
        result = await collector._insert_telemetry(mock_db, telem)

        assert result is True
        all_vals = _extract_all_values(mock_db)
        assert len(all_vals) == 3

        for v in all_vals:
            assert v["telemetry_type"] == TelemetryType.ENVIRONMENT

        temp_row = next(v for v in all_vals if v["metric_name"] == "temperature")
        assert temp_row["temperature"] == 23.5
        assert temp_row["raw_value"] == 23.5

    @pytest.mark.asyncio
    async def test_local_stats(self, collector, mock_db):
        """localStats sub-message should use LOCAL_STATS type."""
        telem = {
            "nodeNum": 12345,
            "localStats": {
                "numOnlineNodes": 15,
                "numTotalNodes": 42,
                "numPacketsTx": 1000,
            },
        }
        result = await collector._insert_telemetry(mock_db, telem)

        assert result is True
        all_vals = _extract_all_values(mock_db)
        assert len(all_vals) == 3

        for v in all_vals:
            assert v["telemetry_type"] == TelemetryType.LOCAL_STATS

        online_row = next(v for v in all_vals if v["metric_name"] == "num_online_nodes")
        assert online_row["raw_value"] == 15.0
        # numOnlineNodes has no dedicated column
        assert "battery_level" not in online_row

    @pytest.mark.asyncio
    async def test_air_quality_metrics(self, collector, mock_db):
        """airQualityMetrics sub-message should use AIR_QUALITY type."""
        telem = {
            "nodeNum": 12345,
            "airQualityMetrics": {
                "pm25Standard": 12.3,
                "co2": 450,
            },
        }
        result = await collector._insert_telemetry(mock_db, telem)

        assert result is True
        all_vals = _extract_all_values(mock_db)
        assert len(all_vals) == 2

        for v in all_vals:
            assert v["telemetry_type"] == TelemetryType.AIR_QUALITY

    @pytest.mark.asyncio
    async def test_host_metrics(self, collector, mock_db):
        """hostMetrics sub-message should use HOST type."""
        telem = {
            "nodeNum": 12345,
            "hostMetrics": {
                "load1": 0.75,
                "freememBytes": 4096000,
            },
        }
        result = await collector._insert_telemetry(mock_db, telem)

        assert result is True
        all_vals = _extract_all_values(mock_db)
        assert len(all_vals) == 2

        for v in all_vals:
            assert v["telemetry_type"] == TelemetryType.HOST

    @pytest.mark.asyncio
    async def test_empty_nested_returns_false(self, collector, mock_db):
        """No known sub-messages → returns False."""
        telem = {
            "nodeNum": 12345,
        }
        result = await collector._insert_telemetry(mock_db, telem)
        assert result is False

    @pytest.mark.asyncio
    async def test_null_metric_values_skipped(self, collector, mock_db):
        """Null metric values inside sub-messages should be skipped."""
        telem = {
            "nodeNum": 12345,
            "deviceMetrics": {
                "batteryLevel": None,
                "voltage": 3.9,
            },
        }
        result = await collector._insert_telemetry(mock_db, telem)

        assert result is True
        all_vals = _extract_all_values(mock_db)
        assert len(all_vals) == 1
        assert all_vals[0]["metric_name"] == "voltage"

    @pytest.mark.asyncio
    async def test_string_metric_values_skipped(self, collector, mock_db):
        """String values in sub-messages should be skipped (not int/float)."""
        telem = {
            "nodeNum": 12345,
            "deviceMetrics": {
                "batteryLevel": 80,
                "firmwareVersion": "2.0.0",  # string, should be skipped
            },
        }
        result = await collector._insert_telemetry(mock_db, telem)

        assert result is True
        all_vals = _extract_all_values(mock_db)
        assert len(all_vals) == 1
        assert all_vals[0]["metric_name"] == "battery_level"

    @pytest.mark.asyncio
    async def test_mixed_submessages(self, collector, mock_db):
        """Multiple sub-message types in one payload should all be handled."""
        telem = {
            "nodeNum": 12345,
            "deviceMetrics": {"batteryLevel": 80},
            "environmentMetrics": {"temperature": 22.0},
        }
        result = await collector._insert_telemetry(mock_db, telem)

        assert result is True
        all_vals = _extract_all_values(mock_db)
        assert len(all_vals) == 2

        types = {v["telemetry_type"] for v in all_vals}
        assert types == {TelemetryType.DEVICE, TelemetryType.ENVIRONMENT}

    @pytest.mark.asyncio
    async def test_nested_raw_value_always_populated(self, collector, mock_db):
        """raw_value should always be a float for nested format metrics."""
        telem = {
            "nodeNum": 12345,
            "deviceMetrics": {
                "uptimeSeconds": 3600,
            },
        }
        result = await collector._insert_telemetry(mock_db, telem)

        assert result is True
        vals = _extract_values(mock_db)
        assert vals["raw_value"] == 3600.0
        assert isinstance(vals["raw_value"], float)
