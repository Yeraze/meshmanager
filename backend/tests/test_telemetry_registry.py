"""Tests for the telemetry metric registry."""

import os

os.environ["TESTING"] = "true"

from app.models.telemetry import TelemetryType
from app.telemetry_registry import (
    CAMEL_TO_METRIC,
    METRIC_REGISTRY,
    SUBMESSAGE_TYPE_MAP,
    get_metrics_by_type,
)


class TestMetricRegistry:
    """Tests for METRIC_REGISTRY integrity."""

    def test_all_names_unique(self):
        """All metric names must be unique."""
        names = [m.name for m in METRIC_REGISTRY.values()]
        assert len(names) == len(set(names))

    def test_all_names_within_column_limit(self):
        """metric_name column is VARCHAR(50)."""
        for name, metric in METRIC_REGISTRY.items():
            assert len(name) <= 50, f"Metric name too long: {name} ({len(name)} chars)"

    def test_registry_is_not_empty(self):
        """Registry should contain a meaningful number of metrics."""
        assert len(METRIC_REGISTRY) >= 50

    def test_all_metrics_have_required_fields(self):
        """Every MetricDef must have name, label, unit, and telemetry_type."""
        for name, m in METRIC_REGISTRY.items():
            assert m.name, f"Missing name for {name}"
            assert m.label, f"Missing label for {name}"
            assert m.unit is not None, f"Missing unit for {name}"
            assert isinstance(m.telemetry_type, TelemetryType), (
                f"Bad telemetry_type for {name}"
            )


class TestCamelToMetric:
    """Tests for CAMEL_TO_METRIC mapping."""

    def test_all_values_exist_in_registry(self):
        """Every value in CAMEL_TO_METRIC must point to a key in METRIC_REGISTRY."""
        for camel, snake in CAMEL_TO_METRIC.items():
            assert snake in METRIC_REGISTRY, (
                f"CAMEL_TO_METRIC[{camel!r}] = {snake!r} not in METRIC_REGISTRY"
            )

    def test_core_device_metrics_mapped(self):
        """Core device metrics should be mapped."""
        expected = {
            "batteryLevel": "battery_level",
            "voltage": "voltage",
            "channelUtilization": "channel_utilization",
            "airUtilTx": "air_util_tx",
            "uptimeSeconds": "uptime_seconds",
        }
        for camel, snake in expected.items():
            assert CAMEL_TO_METRIC.get(camel) == snake

    def test_core_environment_metrics_mapped(self):
        """Core environment metrics should be mapped."""
        expected = {
            "temperature": "temperature",
            "relativeHumidity": "relative_humidity",
            "barometricPressure": "barometric_pressure",
        }
        for camel, snake in expected.items():
            assert CAMEL_TO_METRIC.get(camel) == snake

    def test_power_channel_metrics_mapped(self):
        """Power channel metrics should be mapped."""
        for ch in range(1, 9):
            assert f"ch{ch}Voltage" in CAMEL_TO_METRIC
            assert f"ch{ch}Current" in CAMEL_TO_METRIC

    def test_local_stats_metrics_mapped(self):
        """Local stats metrics should be mapped."""
        assert CAMEL_TO_METRIC["numOnlineNodes"] == "num_online_nodes"
        assert CAMEL_TO_METRIC["numTotalNodes"] == "num_total_nodes"
        assert CAMEL_TO_METRIC["numPacketsTx"] == "num_packets_tx"

    def test_air_quality_metrics_mapped(self):
        """Air quality metrics should be mapped."""
        assert CAMEL_TO_METRIC["pm25Standard"] == "pm25_standard"
        assert CAMEL_TO_METRIC["co2"] == "co2"


class TestDedicatedColumns:
    """Tests for dedicated_column mappings."""

    def test_dedicated_columns_match_model(self):
        """All dedicated_column values must be actual columns on the Telemetry model."""
        from app.models.telemetry import Telemetry

        model_columns = {c.key for c in Telemetry.__table__.columns}
        for name, metric in METRIC_REGISTRY.items():
            if metric.dedicated_column:
                assert metric.dedicated_column in model_columns, (
                    f"Metric {name} has dedicated_column={metric.dedicated_column!r} "
                    f"but that column doesn't exist on Telemetry"
                )

    def test_legacy_columns_have_dedicated(self):
        """Known legacy columns should have dedicated_column set."""
        legacy = [
            "battery_level", "voltage", "channel_utilization", "air_util_tx",
            "uptime_seconds", "temperature", "relative_humidity",
            "barometric_pressure", "current", "snr_local", "snr_remote", "rssi",
        ]
        for name in legacy:
            metric = METRIC_REGISTRY.get(name)
            assert metric is not None, f"Legacy metric {name} missing from registry"
            assert metric.dedicated_column is not None, (
                f"Legacy metric {name} should have dedicated_column"
            )


class TestSubmessageTypeMap:
    """Tests for SUBMESSAGE_TYPE_MAP."""

    def test_covers_expected_keys(self):
        """Map should cover all standard protobuf sub-message keys."""
        expected_keys = {
            "deviceMetrics", "environmentMetrics", "powerMetrics",
            "airQualityMetrics", "localStats", "healthMetrics", "hostMetrics",
        }
        assert set(SUBMESSAGE_TYPE_MAP.keys()) == expected_keys

    def test_values_are_valid_telemetry_types(self):
        """All values must be valid TelemetryType members."""
        for key, ttype in SUBMESSAGE_TYPE_MAP.items():
            assert isinstance(ttype, TelemetryType), (
                f"SUBMESSAGE_TYPE_MAP[{key!r}] is not a TelemetryType"
            )

    def test_does_not_include_position(self):
        """Position is handled separately, not via sub-messages."""
        for ttype in SUBMESSAGE_TYPE_MAP.values():
            assert ttype != TelemetryType.POSITION


class TestGetMetricsByType:
    """Tests for get_metrics_by_type helper."""

    def test_returns_dict(self):
        grouped = get_metrics_by_type()
        assert isinstance(grouped, dict)

    def test_contains_all_non_position_types(self):
        grouped = get_metrics_by_type()
        expected_types = {"device", "environment", "power", "air_quality",
                         "local_stats", "health", "host"}
        assert expected_types.issubset(set(grouped.keys()))

    def test_all_metrics_accounted_for(self):
        grouped = get_metrics_by_type()
        total = sum(len(v) for v in grouped.values())
        assert total == len(METRIC_REGISTRY)

    def test_device_metrics_grouped(self):
        grouped = get_metrics_by_type()
        device_names = {m.name for m in grouped["device"]}
        assert "battery_level" in device_names
        assert "voltage" in device_names
