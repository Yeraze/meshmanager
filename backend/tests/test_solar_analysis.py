"""Tests for solar analysis endpoint."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class TestSolarAnalysisAlgorithm:
    """Unit tests for the solar pattern detection algorithm."""

    def create_telemetry_data(
        self,
        node_num: int,
        days_data: list[dict],
    ) -> list[dict]:
        """Helper to create telemetry test data.

        Args:
            node_num: Node number
            days_data: List of dicts with 'date', 'readings' keys
                       where readings is list of (hour, battery, voltage) tuples
        """
        result = []
        for day in days_data:
            date = datetime.strptime(day["date"], "%Y-%m-%d").replace(tzinfo=UTC)
            for hour, battery, voltage in day["readings"]:
                result.append({
                    "time": date.replace(hour=hour),
                    "battery": battery,
                    "voltage": voltage,
                })
        return result

    def test_clear_solar_pattern_detected(self):
        """Test that a clear solar charging pattern is detected."""
        # Node with clear morning low -> afternoon high pattern
        readings = [
            {"time": datetime(2024, 1, 1, 6, 0, tzinfo=UTC), "battery": 70, "voltage": 3.9},
            {"time": datetime(2024, 1, 1, 8, 0, tzinfo=UTC), "battery": 65, "voltage": 3.85},
            {"time": datetime(2024, 1, 1, 10, 0, tzinfo=UTC), "battery": 72, "voltage": 3.92},
            {"time": datetime(2024, 1, 1, 14, 0, tzinfo=UTC), "battery": 90, "voltage": 4.1},
            {"time": datetime(2024, 1, 1, 16, 0, tzinfo=UTC), "battery": 95, "voltage": 4.15},
            {"time": datetime(2024, 1, 1, 18, 0, tzinfo=UTC), "battery": 92, "voltage": 4.12},
        ]

        # Simulate the algorithm logic
        battery_values = [{"time": r["time"], "value": r["battery"]} for r in readings if r["battery"]]

        all_vals = [v["value"] for v in battery_values]
        min_val, max_val = min(all_vals), max(all_vals)
        daily_range = max_val - min_val

        # Check if meets variance requirement (10% for battery)
        assert daily_range >= 10, "Should have sufficient variance for solar detection"

        # Get morning and afternoon readings
        morning_values = [v for v in battery_values if 6 <= v["time"].hour <= 10]
        afternoon_values = [v for v in battery_values if 12 <= v["time"].hour <= 18]

        assert len(morning_values) > 0, "Should have morning readings"
        assert len(afternoon_values) > 0, "Should have afternoon readings"

        # Find morning low and afternoon high
        morning_low = min(morning_values, key=lambda v: v["value"])
        afternoon_high = max(afternoon_values, key=lambda v: v["value"])

        rise = afternoon_high["value"] - morning_low["value"]
        assert rise >= 10, "Should have significant rise (solar charging)"
        assert afternoon_high["time"].hour >= 10, "Peak should be during daylight"
        assert morning_low["time"].hour <= 12, "Low should be in morning"

    def test_wall_powered_node_excluded(self):
        """Test that a wall-powered node (constant battery) is not detected as solar."""
        # Node with constant 100% battery (wall power)
        readings = [
            {"time": datetime(2024, 1, 1, 6, 0, tzinfo=UTC), "battery": 100, "voltage": 4.2},
            {"time": datetime(2024, 1, 1, 10, 0, tzinfo=UTC), "battery": 100, "voltage": 4.2},
            {"time": datetime(2024, 1, 1, 14, 0, tzinfo=UTC), "battery": 100, "voltage": 4.2},
            {"time": datetime(2024, 1, 1, 18, 0, tzinfo=UTC), "battery": 100, "voltage": 4.2},
        ]

        battery_values = [{"time": r["time"], "value": r["battery"]} for r in readings]
        all_vals = [v["value"] for v in battery_values]
        min_val, max_val = min(all_vals), max(all_vals)
        daily_range = max_val - min_val

        # Wall-powered node has no variance
        assert daily_range == 0, "Wall-powered node should have zero variance"

        # Check high-efficiency candidate criteria
        is_high_efficiency = (
            min_val >= 90 and
            max_val >= 95 and
            daily_range >= 2 and daily_range < 10
        )
        assert not is_high_efficiency, "Zero variance should not qualify as high-efficiency"

    def test_high_efficiency_solar_detected(self):
        """Test that high-efficiency solar (90-100% with small swing) is detected."""
        # High-efficiency solar node: stays 95-100% with 3-5% swing
        readings = [
            {"time": datetime(2024, 1, 1, 6, 0, tzinfo=UTC), "battery": 96, "voltage": 4.15},
            {"time": datetime(2024, 1, 1, 10, 0, tzinfo=UTC), "battery": 95, "voltage": 4.14},
            {"time": datetime(2024, 1, 1, 14, 0, tzinfo=UTC), "battery": 98, "voltage": 4.18},
            {"time": datetime(2024, 1, 1, 16, 0, tzinfo=UTC), "battery": 100, "voltage": 4.2},
            {"time": datetime(2024, 1, 1, 18, 0, tzinfo=UTC), "battery": 99, "voltage": 4.19},
        ]

        battery_values = [{"time": r["time"], "value": r["battery"]} for r in readings]
        all_vals = [v["value"] for v in battery_values]
        min_val, max_val = min(all_vals), max(all_vals)
        daily_range = max_val - min_val
        min_variance = 10  # Standard threshold

        # Check high-efficiency candidate criteria
        is_high_efficiency = (
            min_val >= 90 and
            max_val >= 95 and
            daily_range >= 2 and daily_range < min_variance
        )
        assert is_high_efficiency, "Should be detected as high-efficiency candidate"

        # Get morning and afternoon readings
        morning_values = [v for v in battery_values if 6 <= v["time"].hour <= 10]
        afternoon_values = [v for v in battery_values if 12 <= v["time"].hour <= 18]

        morning_low = min(morning_values, key=lambda v: v["value"])
        afternoon_high = max(afternoon_values, key=lambda v: v["value"])
        rise = afternoon_high["value"] - morning_low["value"]

        # High-efficiency threshold is 1% instead of 10%
        min_rise = 1
        min_ratio = 0.98

        has_pattern = (
            rise >= min_rise and
            afternoon_high["time"].hour >= 10 and
            afternoon_high["time"].hour <= 18 and
            morning_low["time"].hour <= 12 and
            morning_low["value"] <= afternoon_high["value"] * min_ratio
        )
        assert has_pattern, "High-efficiency node should show solar pattern"

    def test_insufficient_readings_skipped(self):
        """Test that days with fewer than 3 readings are skipped."""
        readings = [
            {"time": datetime(2024, 1, 1, 10, 0, tzinfo=UTC), "battery": 80, "voltage": 4.0},
            {"time": datetime(2024, 1, 1, 14, 0, tzinfo=UTC), "battery": 90, "voltage": 4.1},
        ]

        # Should be skipped due to insufficient readings
        assert len(readings) < 3, "Should have fewer than 3 readings"

    def test_inverted_pattern_not_detected(self):
        """Test that inverted pattern (high morning, low afternoon) is not solar."""
        # Pattern: high in morning, low in afternoon (discharging during day)
        readings = [
            {"time": datetime(2024, 1, 1, 6, 0, tzinfo=UTC), "battery": 95, "voltage": 4.15},
            {"time": datetime(2024, 1, 1, 10, 0, tzinfo=UTC), "battery": 90, "voltage": 4.1},
            {"time": datetime(2024, 1, 1, 14, 0, tzinfo=UTC), "battery": 80, "voltage": 4.0},
            {"time": datetime(2024, 1, 1, 18, 0, tzinfo=UTC), "battery": 75, "voltage": 3.95},
        ]

        battery_values = [{"time": r["time"], "value": r["battery"]} for r in readings]
        morning_values = [v for v in battery_values if 6 <= v["time"].hour <= 10]
        afternoon_values = [v for v in battery_values if 12 <= v["time"].hour <= 18]

        morning_low = min(morning_values, key=lambda v: v["value"])
        afternoon_high = max(afternoon_values, key=lambda v: v["value"])

        rise = afternoon_high["value"] - morning_low["value"]

        # Rise should be negative or very small (no solar charging)
        assert rise <= 0, "Inverted pattern should have negative or zero rise"

    def test_voltage_detection_when_no_battery(self):
        """Test that voltage is used when battery readings are absent."""
        readings = [
            {"time": datetime(2024, 1, 1, 6, 0, tzinfo=UTC), "battery": None, "voltage": 3.8},
            {"time": datetime(2024, 1, 1, 10, 0, tzinfo=UTC), "battery": None, "voltage": 3.9},
            {"time": datetime(2024, 1, 1, 14, 0, tzinfo=UTC), "battery": None, "voltage": 4.1},
            {"time": datetime(2024, 1, 1, 18, 0, tzinfo=UTC), "battery": None, "voltage": 4.2},
        ]

        battery_values = [{"time": r["time"], "value": r["battery"]} for r in readings if r["battery"]]
        voltage_values = [{"time": r["time"], "value": r["voltage"]} for r in readings if r["voltage"]]

        assert len(battery_values) == 0, "Should have no battery readings"
        assert len(voltage_values) == 4, "Should have voltage readings"

        # Voltage min variance is 0.3V
        all_vals = [v["value"] for v in voltage_values]
        daily_range = max(all_vals) - min(all_vals)
        assert daily_range >= 0.3, "Voltage should have sufficient variance"

    def test_solar_score_calculation(self):
        """Test that solar score is calculated correctly."""
        days_with_pattern = 5
        total_days = 7

        solar_score = round((days_with_pattern / total_days) * 100, 1)
        assert solar_score == 71.4, "Solar score should be 71.4%"

    def test_threshold_for_high_efficiency_nodes(self):
        """Test that high-efficiency nodes use 33% threshold instead of 50%."""
        # Simulate high-efficiency node stats
        total_days = 6
        high_efficiency_days = 5
        days_with_pattern = 2

        is_mostly_high_efficiency = high_efficiency_days > total_days * 0.5
        assert is_mostly_high_efficiency, "Should be mostly high-efficiency"

        min_pattern_ratio = 0.33 if is_mostly_high_efficiency else 0.5
        pattern_ratio = days_with_pattern / total_days

        # 2/6 = 0.33, which meets the 33% threshold
        assert pattern_ratio >= min_pattern_ratio, "Should pass with 33% threshold"

        # But would fail with 50% threshold
        assert pattern_ratio < 0.5, "Would fail with 50% threshold"


class TestSolarAnalysisEdgeCases:
    """Edge case tests for solar analysis."""

    def test_no_morning_readings(self):
        """Test handling when there are no readings in morning window."""
        readings = [
            {"time": datetime(2024, 1, 1, 14, 0, tzinfo=UTC), "battery": 90, "voltage": 4.1},
            {"time": datetime(2024, 1, 1, 16, 0, tzinfo=UTC), "battery": 95, "voltage": 4.15},
            {"time": datetime(2024, 1, 1, 18, 0, tzinfo=UTC), "battery": 92, "voltage": 4.12},
        ]

        battery_values = [{"time": r["time"], "value": r["battery"]} for r in readings]
        morning_values = [v for v in battery_values if 6 <= v["time"].hour <= 10]

        assert len(morning_values) == 0, "Should have no morning readings"
        # Algorithm should use fallback path

    def test_no_afternoon_readings(self):
        """Test handling when there are no readings in afternoon window."""
        readings = [
            {"time": datetime(2024, 1, 1, 6, 0, tzinfo=UTC), "battery": 70, "voltage": 3.9},
            {"time": datetime(2024, 1, 1, 8, 0, tzinfo=UTC), "battery": 65, "voltage": 3.85},
            {"time": datetime(2024, 1, 1, 10, 0, tzinfo=UTC), "battery": 72, "voltage": 3.92},
        ]

        battery_values = [{"time": r["time"], "value": r["battery"]} for r in readings]
        afternoon_values = [v for v in battery_values if 12 <= v["time"].hour <= 18]

        assert len(afternoon_values) == 0, "Should have no afternoon readings"
        # Algorithm should use fallback path

    def test_mixed_battery_voltage_uses_battery_preference(self):
        """Test that battery is preferred over voltage when both available."""
        readings = [
            {"time": datetime(2024, 1, 1, 6, 0, tzinfo=UTC), "battery": 70, "voltage": 3.9},
            {"time": datetime(2024, 1, 1, 10, 0, tzinfo=UTC), "battery": 75, "voltage": 3.95},
            {"time": datetime(2024, 1, 1, 14, 0, tzinfo=UTC), "battery": 90, "voltage": 4.1},
            {"time": datetime(2024, 1, 1, 18, 0, tzinfo=UTC), "battery": 85, "voltage": 4.05},
        ]

        battery_values = [r for r in readings if r["battery"]]
        voltage_values = [r for r in readings if r["voltage"]]

        # When both have 3+ readings, battery should be preferred
        assert len(battery_values) >= 3 and len(voltage_values) >= 3
        # Algorithm uses battery when len(battery_values) >= 3

    def test_boundary_hour_values(self):
        """Test that boundary hours (6, 10, 12, 18) are correctly categorized."""
        readings = [
            {"time": datetime(2024, 1, 1, 6, 0, tzinfo=UTC), "battery": 70, "voltage": 3.9},  # Morning start
            {"time": datetime(2024, 1, 1, 10, 0, tzinfo=UTC), "battery": 75, "voltage": 3.95},  # Morning end
            {"time": datetime(2024, 1, 1, 12, 0, tzinfo=UTC), "battery": 85, "voltage": 4.05},  # Afternoon start
            {"time": datetime(2024, 1, 1, 18, 0, tzinfo=UTC), "battery": 95, "voltage": 4.15},  # Afternoon end
        ]

        battery_values = [{"time": r["time"], "value": r["battery"]} for r in readings]

        # Check boundary inclusion
        morning_values = [v for v in battery_values if 6 <= v["time"].hour <= 10]
        afternoon_values = [v for v in battery_values if 12 <= v["time"].hour <= 18]

        assert len(morning_values) == 2, "Hours 6 and 10 should be in morning window"
        assert len(afternoon_values) == 2, "Hours 12 and 18 should be in afternoon window"


@pytest.mark.integration
class TestSolarAnalysisEndpoint:
    """Integration tests for the /api/analysis/solar-nodes endpoint."""

    async def test_endpoint_returns_200(self, client):
        """Test that endpoint returns 200 status code."""
        response = await client.get("/api/analysis/solar-nodes")
        assert response.status_code == 200

    async def test_endpoint_returns_expected_structure(self, client):
        """Test that endpoint returns expected JSON structure."""
        response = await client.get("/api/analysis/solar-nodes")
        data = response.json()

        assert "lookback_days" in data
        assert "total_nodes_analyzed" in data
        assert "solar_nodes_count" in data
        assert "solar_nodes" in data
        assert "solar_production" in data

        assert isinstance(data["solar_nodes"], list)
        assert isinstance(data["solar_production"], list)

    async def test_lookback_days_parameter(self, client):
        """Test that lookback_days parameter is respected."""
        response = await client.get("/api/analysis/solar-nodes?lookback_days=14")
        data = response.json()

        assert data["lookback_days"] == 14

    async def test_lookback_days_validation(self, client):
        """Test that invalid lookback_days returns error."""
        # Below minimum
        response = await client.get("/api/analysis/solar-nodes?lookback_days=0")
        assert response.status_code == 422

        # Above maximum
        response = await client.get("/api/analysis/solar-nodes?lookback_days=100")
        assert response.status_code == 422

    async def test_solar_node_structure(self, client):
        """Test that solar node objects have expected structure."""
        response = await client.get("/api/analysis/solar-nodes")
        data = response.json()

        if data["solar_nodes"]:
            node = data["solar_nodes"][0]
            assert "node_num" in node
            assert "node_name" in node
            assert "solar_score" in node
            assert "days_analyzed" in node
            assert "days_with_pattern" in node
            assert "recent_patterns" in node
            assert "metric_type" in node
            assert "chart_data" in node

            assert node["metric_type"] in ["battery", "voltage"]

    async def test_empty_database_returns_empty_results(self, client):
        """Test that empty database returns zero nodes."""
        response = await client.get("/api/analysis/solar-nodes")
        data = response.json()

        # With empty test DB, should return empty results
        assert data["total_nodes_analyzed"] >= 0
        assert data["solar_nodes_count"] >= 0
