"""Schemas for configuration export/import."""

from pydantic import BaseModel, Field


class ExportSourceConfig(BaseModel):
    """Source configuration for export (excludes sensitive data)."""

    name: str
    type: str  # "meshmonitor" or "mqtt"
    enabled: bool = True
    # MeshMonitor fields
    url: str | None = None
    poll_interval_seconds: int | None = None
    historical_days_back: int | None = None
    # MQTT fields
    mqtt_host: str | None = None
    mqtt_port: int | None = None
    mqtt_topic_pattern: str | None = None
    mqtt_use_tls: bool | None = None


class DisplaySettingsConfig(BaseModel):
    """Display settings configuration."""

    active_hours: int = Field(default=24, ge=1, le=8760)
    online_hours: int = Field(default=1, ge=1, le=168)


class BoundsConfig(BaseModel):
    """Geographic bounds configuration."""

    south: float | None = None
    west: float | None = None
    north: float | None = None
    east: float | None = None


class CoverageAnalysisConfig(BaseModel):
    """Coverage analysis configuration."""

    enabled: bool = False
    resolution: float = 1.0
    unit: str = "miles"
    lookback_days: int = 7
    bounds: BoundsConfig | None = None


class UtilizationAnalysisConfig(BaseModel):
    """Utilization analysis configuration."""

    enabled: bool = False
    resolution: float = 1.0
    unit: str = "miles"
    lookback_days: int = 7
    aggregation: str = "avg"
    bounds: BoundsConfig | None = None


class SolarScheduleConfig(BaseModel):
    """Solar analysis schedule configuration."""

    enabled: bool = False
    schedules: list[str] = Field(default_factory=list)
    apprise_urls: list[str] = Field(default_factory=list)
    lookback_days: int = 7


class AnalysisConfig(BaseModel):
    """Combined analysis configurations."""

    coverage_config: CoverageAnalysisConfig | None = None
    utilization_config: UtilizationAnalysisConfig | None = None
    solar_schedule: SolarScheduleConfig | None = None


class ConfigExport(BaseModel):
    """Full configuration export structure."""

    version: str = "1.0"
    exported_at: str
    meshmanager_version: str
    sources: list[ExportSourceConfig] = Field(default_factory=list)
    display_settings: DisplaySettingsConfig | None = None
    analysis: AnalysisConfig | None = None


class ConfigImport(BaseModel):
    """Configuration import request."""

    version: str
    exported_at: str | None = None
    meshmanager_version: str | None = None
    sources: list[ExportSourceConfig] = Field(default_factory=list)
    display_settings: DisplaySettingsConfig | None = None
    analysis: AnalysisConfig | None = None


class ImportResult(BaseModel):
    """Result of configuration import."""

    success: bool
    sources_imported: int = 0
    sources_skipped: int = 0
    display_settings_imported: bool = False
    analysis_configs_imported: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    # Return display settings for frontend to apply
    display_settings: DisplaySettingsConfig | None = None
