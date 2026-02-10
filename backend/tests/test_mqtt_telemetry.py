"""Tests for MQTT telemetry handling with the telemetry registry."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.collectors.mqtt import MqttCollector
from app.models import Source
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
    """Create a mock DB session that tracks pg_insert executions."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    # Each execute call returns a result with rowcount=1 (inserted)
    result = MagicMock()
    result.rowcount = 1
    db.execute = AsyncMock(return_value=result)
    return db


def _extract_insert_calls(mock_db):
    """Extract the values dicts from all pg_insert execute calls."""
    rows = []
    for call in mock_db.execute.call_args_list:
        stmt = call.args[0]
        # The pg_insert statement stores compiled params; extract from the
        # statement's compile_state or parameters.
        if hasattr(stmt, "compile"):
            # Access the inserted values from the Insert statement
            params = stmt._values
            if params:
                rows.append({k.key: v for k, v in params})
    return rows


class TestHandleTelemetryDeviceMetrics:
    """Tests for deviceMetrics extraction."""

    @pytest.mark.asyncio
    async def test_device_metrics_individual_rows(self, collector, mock_db):
        """Each device metric produces an individual Telemetry row."""
        data = {
            "from": 12345678,
            "telemetry": {
                "deviceMetrics": {
                    "batteryLevel": 85,
                    "voltage": 4.1,
                    "channelUtilization": 25.5,
                    "airUtilTx": 5.2,
                }
            },
        }

        await collector._handle_telemetry(mock_db, data)

        # 4 metrics = 4 execute calls
        assert mock_db.execute.call_count == 4

    @pytest.mark.asyncio
    async def test_device_metrics_raw_value_always_set(self, collector, mock_db):
        """raw_value is always populated for every metric."""
        data = {
            "from": 12345678,
            "telemetry": {
                "deviceMetrics": {
                    "batteryLevel": 85,
                    "voltage": 4.1,
                }
            },
        }

        await collector._handle_telemetry(mock_db, data)

        # Inspect all statements passed to execute
        for call in mock_db.execute.call_args_list:
            stmt = call.args[0]
            # The Insert statement should have raw_value in its parameters
            params = stmt.compile().params
            assert "raw_value" in params, "raw_value must always be set"
            assert params["raw_value"] is not None

    @pytest.mark.asyncio
    async def test_device_metrics_dedicated_columns(self, collector, mock_db):
        """Dedicated columns (battery_level, voltage, etc.) are populated."""
        data = {
            "from": 12345678,
            "telemetry": {
                "deviceMetrics": {
                    "batteryLevel": 85,
                    "voltage": 4.1,
                }
            },
        }

        await collector._handle_telemetry(mock_db, data)

        # Verify that battery_level and voltage dedicated columns are set
        found_battery = False
        found_voltage = False
        for call in mock_db.execute.call_args_list:
            stmt = call.args[0]
            params = stmt.compile().params
            if params.get("metric_name") == "battery_level":
                assert params.get("battery_level") == 85
                assert params["raw_value"] == 85.0
                found_battery = True
            elif params.get("metric_name") == "voltage":
                assert params.get("voltage") == 4.1
                assert params["raw_value"] == pytest.approx(4.1)
                found_voltage = True

        assert found_battery, "battery_level metric not found"
        assert found_voltage, "voltage metric not found"

    @pytest.mark.asyncio
    async def test_device_metrics_telemetry_type(self, collector, mock_db):
        """All device metrics get telemetry_type=DEVICE."""
        data = {
            "from": 12345678,
            "telemetry": {
                "deviceMetrics": {
                    "batteryLevel": 85,
                    "voltage": 4.1,
                }
            },
        }

        await collector._handle_telemetry(mock_db, data)

        for call in mock_db.execute.call_args_list:
            stmt = call.args[0]
            params = stmt.compile().params
            assert params["telemetry_type"] == TelemetryType.DEVICE


class TestHandleTelemetryLocalStats:
    """Tests for localStats extraction."""

    @pytest.mark.asyncio
    async def test_local_stats_extraction(self, collector, mock_db):
        """localStats metrics are extracted correctly."""
        data = {
            "from": 12345678,
            "telemetry": {
                "localStats": {
                    "numOnlineNodes": 15,
                    "numTotalNodes": 42,
                    "numPacketsTx": 100,
                    "numPacketsRx": 200,
                }
            },
        }

        await collector._handle_telemetry(mock_db, data)

        assert mock_db.execute.call_count == 4

        metric_names = set()
        for call in mock_db.execute.call_args_list:
            stmt = call.args[0]
            params = stmt.compile().params
            metric_names.add(params["metric_name"])
            assert params["telemetry_type"] == TelemetryType.LOCAL_STATS

        assert "num_online_nodes" in metric_names
        assert "num_total_nodes" in metric_names
        assert "num_packets_tx" in metric_names
        assert "num_packets_rx" in metric_names


class TestHandleTelemetryAirQuality:
    """Tests for airQualityMetrics extraction."""

    @pytest.mark.asyncio
    async def test_air_quality_extraction(self, collector, mock_db):
        """airQualityMetrics are extracted with correct type."""
        data = {
            "from": 12345678,
            "telemetry": {
                "airQualityMetrics": {
                    "pm25Standard": 12,
                    "co2": 400,
                }
            },
        }

        await collector._handle_telemetry(mock_db, data)

        assert mock_db.execute.call_count == 2

        metric_names = set()
        for call in mock_db.execute.call_args_list:
            stmt = call.args[0]
            params = stmt.compile().params
            metric_names.add(params["metric_name"])
            assert params["telemetry_type"] == TelemetryType.AIR_QUALITY

        assert "pm25_standard" in metric_names
        assert "co2" in metric_names


class TestHandleTelemetryPowerMetrics:
    """Tests for powerMetrics extraction."""

    @pytest.mark.asyncio
    async def test_power_metrics_extraction(self, collector, mock_db):
        """powerMetrics channels are extracted as individual rows."""
        data = {
            "from": 12345678,
            "telemetry": {
                "powerMetrics": {
                    "ch1Voltage": 3.3,
                    "ch1Current": 150.0,
                    "ch2Voltage": 5.0,
                }
            },
        }

        await collector._handle_telemetry(mock_db, data)

        assert mock_db.execute.call_count == 3

        metric_names = set()
        for call in mock_db.execute.call_args_list:
            stmt = call.args[0]
            params = stmt.compile().params
            metric_names.add(params["metric_name"])
            assert params["telemetry_type"] == TelemetryType.POWER

        assert "ch1_voltage" in metric_names
        assert "ch1_current" in metric_names
        assert "ch2_voltage" in metric_names


class TestHandleTelemetryNonNumericSkipped:
    """Tests that non-numeric values are skipped."""

    @pytest.mark.asyncio
    async def test_string_values_skipped(self, collector, mock_db):
        """String values in metrics dict are ignored."""
        data = {
            "from": 12345678,
            "telemetry": {
                "deviceMetrics": {
                    "batteryLevel": 85,
                    "someStringField": "not a number",
                }
            },
        }

        await collector._handle_telemetry(mock_db, data)

        # Only 1 numeric metric => 1 execute call
        assert mock_db.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_none_values_skipped(self, collector, mock_db):
        """None values in metrics dict are ignored."""
        data = {
            "from": 12345678,
            "telemetry": {
                "deviceMetrics": {
                    "batteryLevel": None,
                    "voltage": 4.1,
                }
            },
        }

        await collector._handle_telemetry(mock_db, data)

        assert mock_db.execute.call_count == 1
        stmt = mock_db.execute.call_args_list[0].args[0]
        params = stmt.compile().params
        assert params["metric_name"] == "voltage"

    @pytest.mark.asyncio
    async def test_zero_is_valid(self, collector, mock_db):
        """Zero is a valid numeric value and should NOT be skipped."""
        data = {
            "from": 12345678,
            "telemetry": {
                "deviceMetrics": {
                    "batteryLevel": 0,
                }
            },
        }

        await collector._handle_telemetry(mock_db, data)

        assert mock_db.execute.call_count == 1
        stmt = mock_db.execute.call_args_list[0].args[0]
        params = stmt.compile().params
        assert params["raw_value"] == 0.0


class TestHandleTelemetryFlatFallback:
    """Tests for flat payload fallback."""

    @pytest.mark.asyncio
    async def test_flat_fallback_triggers_when_no_submessages(self, collector, mock_db):
        """Flat fallback is used when no sub-message keys are found."""
        # No deviceMetrics/environmentMetrics etc. — metrics at top level of payload
        data = {
            "from": 12345678,
            "payload": {
                "batteryLevel": 75,
                "voltage": 3.9,
            },
        }

        await collector._handle_telemetry(mock_db, data)

        # Should produce 2 rows via flat fallback
        assert mock_db.execute.call_count == 2

        metric_names = set()
        for call in mock_db.execute.call_args_list:
            stmt = call.args[0]
            params = stmt.compile().params
            metric_names.add(params["metric_name"])
            assert params["raw_value"] is not None

        assert "battery_level" in metric_names
        assert "voltage" in metric_names

    @pytest.mark.asyncio
    async def test_flat_fallback_skips_unknown_keys(self, collector, mock_db):
        """Unknown keys in flat payload are skipped."""
        data = {
            "from": 12345678,
            "payload": {
                "unknownMetric": 42,
                "voltage": 3.9,
            },
        }

        await collector._handle_telemetry(mock_db, data)

        # Only voltage should be inserted
        assert mock_db.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_flat_fallback_not_triggered_when_submessages_found(
        self, collector, mock_db
    ):
        """Flat fallback is NOT used when sub-messages are present and inserted."""
        data = {
            "from": 12345678,
            "telemetry": {
                "deviceMetrics": {
                    "batteryLevel": 85,
                }
            },
            "payload": {
                "voltage": 3.9,  # This should NOT be inserted via fallback
            },
        }

        await collector._handle_telemetry(mock_db, data)

        # Only 1 row from deviceMetrics, no fallback
        assert mock_db.execute.call_count == 1


class TestHandleTelemetryEdgeCases:
    """Edge case tests."""

    @pytest.mark.asyncio
    async def test_hex_from_node_id(self, collector, mock_db):
        """Hex node IDs (e.g. '!aabbccdd') are converted to int."""
        data = {
            "from": "!aabbccdd",
            "telemetry": {
                "deviceMetrics": {
                    "batteryLevel": 50,
                }
            },
        }

        await collector._handle_telemetry(mock_db, data)

        stmt = mock_db.execute.call_args_list[0].args[0]
        params = stmt.compile().params
        assert params["node_num"] == 0xAABBCCDD

    @pytest.mark.asyncio
    async def test_no_from_node_returns_early(self, collector, mock_db):
        """If no from/fromId, _handle_telemetry returns without inserting."""
        data = {
            "telemetry": {
                "deviceMetrics": {
                    "batteryLevel": 85,
                }
            },
        }

        await collector._handle_telemetry(mock_db, data)

        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_submessage_types(self, collector, mock_db):
        """Multiple sub-message types in one telemetry are all extracted."""
        data = {
            "from": 12345678,
            "telemetry": {
                "deviceMetrics": {
                    "batteryLevel": 85,
                },
                "environmentMetrics": {
                    "temperature": 22.5,
                },
            },
        }

        await collector._handle_telemetry(mock_db, data)

        assert mock_db.execute.call_count == 2

        types_seen = set()
        for call in mock_db.execute.call_args_list:
            stmt = call.args[0]
            params = stmt.compile().params
            types_seen.add(params["telemetry_type"])

        assert TelemetryType.DEVICE in types_seen
        assert TelemetryType.ENVIRONMENT in types_seen

    @pytest.mark.asyncio
    async def test_metrics_from_payload_submessage(self, collector, mock_db):
        """Metrics nested in payload sub-messages are also found."""
        data = {
            "from": 12345678,
            "payload": {
                "deviceMetrics": {
                    "batteryLevel": 60,
                }
            },
        }

        await collector._handle_telemetry(mock_db, data)

        assert mock_db.execute.call_count == 1
        stmt = mock_db.execute.call_args_list[0].args[0]
        params = stmt.compile().params
        assert params["metric_name"] == "battery_level"
        assert params["raw_value"] == 60.0

    @pytest.mark.asyncio
    async def test_environment_dedicated_columns(self, collector, mock_db):
        """Environment metrics with dedicated columns populate them."""
        data = {
            "from": 12345678,
            "telemetry": {
                "environmentMetrics": {
                    "temperature": 22.5,
                    "relativeHumidity": 65.0,
                    "barometricPressure": 1013.25,
                }
            },
        }

        await collector._handle_telemetry(mock_db, data)

        assert mock_db.execute.call_count == 3

        for call in mock_db.execute.call_args_list:
            stmt = call.args[0]
            params = stmt.compile().params
            if params["metric_name"] == "temperature":
                assert params.get("temperature") == 22.5
                assert params["raw_value"] == 22.5
            elif params["metric_name"] == "relative_humidity":
                assert params.get("relative_humidity") == 65.0
                assert params["raw_value"] == 65.0
            elif params["metric_name"] == "barometric_pressure":
                assert params.get("barometric_pressure") == 1013.25
                assert params["raw_value"] == pytest.approx(1013.25)
