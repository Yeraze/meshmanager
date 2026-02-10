"""Tests for telemetry API metric discovery and registry integration."""

import os

os.environ["TESTING"] = "true"

from app.telemetry_registry import CAMEL_TO_METRIC, METRIC_REGISTRY


class TestMetricDiscoveryLogic:
    """Test the metric resolution logic used by API endpoints."""

    def test_known_metric_resolved(self):
        """Known snake_case metric should be found in registry."""
        assert "battery_level" in METRIC_REGISTRY
        assert METRIC_REGISTRY["battery_level"].label == "Battery Level"

    def test_camel_case_resolved(self):
        """camelCase metric should be resolved via CAMEL_TO_METRIC."""
        resolved = CAMEL_TO_METRIC.get("batteryLevel")
        assert resolved == "battery_level"
        assert resolved in METRIC_REGISTRY

    def test_unknown_metric_not_found(self):
        """Unknown metric should not be in registry."""
        assert "nonexistent_metric" not in METRIC_REGISTRY
        assert CAMEL_TO_METRIC.get("nonexistentMetric") is None

    def test_new_metric_types_in_registry(self):
        """New metric types (local_stats, air_quality, etc.) should be in registry."""
        assert "num_online_nodes" in METRIC_REGISTRY
        assert "pm25_standard" in METRIC_REGISTRY
        assert "heart_bpm" in METRIC_REGISTRY
        assert "host_uptime_seconds" in METRIC_REGISTRY

    def test_dedicated_column_for_legacy_metrics(self):
        """Legacy metrics should have dedicated columns."""
        assert METRIC_REGISTRY["battery_level"].dedicated_column == "battery_level"
        assert METRIC_REGISTRY["voltage"].dedicated_column == "voltage"

    def test_no_dedicated_column_for_new_metrics(self):
        """New metrics should NOT have dedicated columns."""
        assert METRIC_REGISTRY["num_online_nodes"].dedicated_column is None
        assert METRIC_REGISTRY["pm25_standard"].dedicated_column is None

    def test_all_camel_keys_resolve_to_registry(self):
        """Every camelCase key should map to a valid registry entry."""
        for camel, snake in CAMEL_TO_METRIC.items():
            assert snake in METRIC_REGISTRY, f"{camel} -> {snake} not in METRIC_REGISTRY"

    def test_metric_def_fields(self):
        """MetricDef should have all expected fields."""
        m = METRIC_REGISTRY["temperature"]
        assert m.name == "temperature"
        assert m.label == "Temperature"
        assert m.unit == "°C"
        assert m.dedicated_column == "temperature"

    def test_environment_metrics_present(self):
        """Environment metrics should be in registry."""
        env_metrics = ["temperature", "relative_humidity", "barometric_pressure", "gas_resistance"]
        for name in env_metrics:
            assert name in METRIC_REGISTRY, f"{name} not in METRIC_REGISTRY"

    def test_power_metrics_present(self):
        """Power channel metrics should be in registry."""
        for ch in range(1, 9):
            assert f"ch{ch}_voltage" in METRIC_REGISTRY
            assert f"ch{ch}_current" in METRIC_REGISTRY
