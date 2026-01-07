"""Tests for configuration export/import endpoints."""

import json

import pytest

from app.schemas.config import (
    AnalysisConfig,
    BoundsConfig,
    ConfigExport,
    ConfigImport,
    CoverageAnalysisConfig,
    DisplaySettingsConfig,
    ExportSourceConfig,
    ImportResult,
    SolarScheduleConfig,
    UtilizationAnalysisConfig,
)


class TestConfigSchemas:
    """Test Pydantic config schemas."""

    def test_export_source_config_meshmonitor(self):
        """Test ExportSourceConfig for MeshMonitor source."""
        config = ExportSourceConfig(
            name="Test MeshMonitor",
            type="meshmonitor",
            enabled=True,
            url="https://meshmonitor.example.com",
            poll_interval_seconds=300,
            historical_days_back=7,
        )
        assert config.name == "Test MeshMonitor"
        assert config.type == "meshmonitor"
        assert config.url == "https://meshmonitor.example.com"
        assert config.mqtt_host is None

    def test_export_source_config_mqtt(self):
        """Test ExportSourceConfig for MQTT source."""
        config = ExportSourceConfig(
            name="Test MQTT",
            type="mqtt",
            enabled=True,
            mqtt_host="mqtt.example.com",
            mqtt_port=1883,
            mqtt_topic_pattern="msh/+/+/json/#",
            mqtt_use_tls=False,
        )
        assert config.name == "Test MQTT"
        assert config.type == "mqtt"
        assert config.mqtt_host == "mqtt.example.com"
        assert config.url is None

    def test_display_settings_config_defaults(self):
        """Test DisplaySettingsConfig default values."""
        config = DisplaySettingsConfig()
        assert config.active_hours == 24
        assert config.online_hours == 1

    def test_display_settings_config_validation(self):
        """Test DisplaySettingsConfig validation."""
        config = DisplaySettingsConfig(active_hours=168, online_hours=24)
        assert config.active_hours == 168
        assert config.online_hours == 24

    def test_bounds_config(self):
        """Test BoundsConfig."""
        config = BoundsConfig(
            south=39.0,
            west=-77.0,
            north=40.0,
            east=-76.0,
        )
        assert config.south == 39.0
        assert config.west == -77.0

    def test_coverage_analysis_config_defaults(self):
        """Test CoverageAnalysisConfig defaults."""
        config = CoverageAnalysisConfig()
        assert config.enabled is False
        assert config.resolution == 1.0
        assert config.unit == "miles"
        assert config.lookback_days == 7
        assert config.bounds is None

    def test_coverage_analysis_config_with_bounds(self):
        """Test CoverageAnalysisConfig with bounds."""
        config = CoverageAnalysisConfig(
            enabled=True,
            resolution=0.5,
            unit="kilometers",
            lookback_days=14,
            bounds=BoundsConfig(south=39.0, west=-77.0, north=40.0, east=-76.0),
        )
        assert config.enabled is True
        assert config.bounds is not None
        assert config.bounds.south == 39.0

    def test_utilization_analysis_config_defaults(self):
        """Test UtilizationAnalysisConfig defaults."""
        config = UtilizationAnalysisConfig()
        assert config.enabled is False
        assert config.aggregation == "avg"

    def test_solar_schedule_config_defaults(self):
        """Test SolarScheduleConfig defaults."""
        config = SolarScheduleConfig()
        assert config.enabled is False
        assert config.schedules == []
        assert config.apprise_urls == []
        assert config.lookback_days == 7

    def test_solar_schedule_config_with_data(self):
        """Test SolarScheduleConfig with data."""
        config = SolarScheduleConfig(
            enabled=True,
            schedules=["08:00", "18:00"],
            apprise_urls=["discord://webhook"],
            lookback_days=14,
        )
        assert config.enabled is True
        assert len(config.schedules) == 2

    def test_analysis_config(self):
        """Test AnalysisConfig combining all analysis types."""
        config = AnalysisConfig(
            coverage_config=CoverageAnalysisConfig(enabled=True),
            utilization_config=UtilizationAnalysisConfig(enabled=False),
            solar_schedule=SolarScheduleConfig(enabled=True, schedules=["06:00"]),
        )
        assert config.coverage_config is not None
        assert config.coverage_config.enabled is True
        assert config.solar_schedule.schedules == ["06:00"]

    def test_config_export(self):
        """Test ConfigExport structure."""
        config = ConfigExport(
            version="1.0",
            exported_at="2026-01-07T12:00:00Z",
            meshmanager_version="0.4.0",
            sources=[
                ExportSourceConfig(
                    name="Test",
                    type="meshmonitor",
                    enabled=True,
                    url="https://test.example.com",
                )
            ],
            display_settings=DisplaySettingsConfig(active_hours=48, online_hours=2),
            analysis=AnalysisConfig(
                coverage_config=CoverageAnalysisConfig(enabled=True),
            ),
        )
        assert config.version == "1.0"
        assert len(config.sources) == 1
        assert config.display_settings.active_hours == 48

    def test_config_import(self):
        """Test ConfigImport parsing."""
        config = ConfigImport(
            version="1.0",
            sources=[
                ExportSourceConfig(name="Test", type="meshmonitor", enabled=True)
            ],
        )
        assert config.version == "1.0"
        assert len(config.sources) == 1

    def test_import_result(self):
        """Test ImportResult structure."""
        result = ImportResult(
            success=True,
            sources_imported=2,
            sources_skipped=1,
            display_settings_imported=True,
            analysis_configs_imported=["coverage_config", "solar_schedule"],
            warnings=["Skipped duplicate source: Test"],
            display_settings=DisplaySettingsConfig(active_hours=24, online_hours=1),
        )
        assert result.success is True
        assert result.sources_imported == 2
        assert len(result.warnings) == 1

    def test_config_export_serialization(self):
        """Test that ConfigExport can be serialized to JSON."""
        config = ConfigExport(
            version="1.0",
            exported_at="2026-01-07T12:00:00Z",
            meshmanager_version="0.4.0",
        )
        json_str = json.dumps(config.model_dump())
        assert "version" in json_str
        assert "1.0" in json_str

    def test_config_import_from_json(self):
        """Test ConfigImport parsing from JSON."""
        json_data = {
            "version": "1.0",
            "exported_at": "2026-01-07T12:00:00Z",
            "meshmanager_version": "0.4.0",
            "sources": [
                {
                    "name": "My Source",
                    "type": "meshmonitor",
                    "enabled": True,
                    "url": "https://example.com",
                }
            ],
            "display_settings": {
                "active_hours": 72,
                "online_hours": 4,
            },
            "analysis": {
                "coverage_config": {
                    "enabled": True,
                    "resolution": 2.0,
                    "unit": "miles",
                    "lookback_days": 30,
                }
            },
        }
        config = ConfigImport(**json_data)
        assert config.version == "1.0"
        assert len(config.sources) == 1
        assert config.sources[0].name == "My Source"
        assert config.display_settings.active_hours == 72
        assert config.analysis.coverage_config.resolution == 2.0
