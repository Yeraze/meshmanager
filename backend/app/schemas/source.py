"""Schemas for source management."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.source import SourceType


class SourceBase(BaseModel):
    """Base schema for sources."""

    name: str = Field(..., min_length=1, max_length=255)
    enabled: bool = True


class MeshMonitorSourceCreate(SourceBase):
    """Schema for creating a MeshMonitor source."""

    url: str = Field(..., min_length=1, max_length=500)
    api_token: str | None = Field(default=None, max_length=500)
    poll_interval_seconds: int = Field(default=300, ge=60, le=86400)
    historical_days_back: int = Field(default=1, ge=1, le=30, description="Days of historical data to sync on initial collection")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL has a scheme."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v.rstrip("/")


class MeshMonitorSourceUpdate(BaseModel):
    """Schema for updating a MeshMonitor source."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = Field(default=None, min_length=1, max_length=500)
    api_token: str | None = Field(default=None, max_length=500)
    poll_interval_seconds: int | None = Field(default=None, ge=60, le=86400)
    historical_days_back: int | None = Field(default=None, ge=1, le=30, description="Days of historical data to sync on initial collection")
    enabled: bool | None = None


class MqttSourceCreate(SourceBase):
    """Schema for creating an MQTT source."""

    mqtt_host: str = Field(..., min_length=1, max_length=255)
    mqtt_port: int = Field(default=1883, ge=1, le=65535)
    mqtt_username: str | None = Field(default=None, max_length=255)
    mqtt_password: str | None = Field(default=None, max_length=500)
    mqtt_topic_pattern: str = Field(..., min_length=1, max_length=500)
    mqtt_use_tls: bool = False


class MqttSourceUpdate(BaseModel):
    """Schema for updating an MQTT source."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    mqtt_host: str | None = Field(default=None, min_length=1, max_length=255)
    mqtt_port: int | None = Field(default=None, ge=1, le=65535)
    mqtt_username: str | None = Field(default=None, max_length=255)
    mqtt_password: str | None = Field(default=None, max_length=500)
    mqtt_topic_pattern: str | None = Field(default=None, min_length=1, max_length=500)
    mqtt_use_tls: bool | None = None
    enabled: bool | None = None


# Union types for generic operations
SourceCreate = MeshMonitorSourceCreate | MqttSourceCreate
SourceUpdate = MeshMonitorSourceUpdate | MqttSourceUpdate


class SourceResponse(BaseModel):
    """Response schema for a source."""

    id: str
    name: str
    type: SourceType
    enabled: bool

    # MeshMonitor fields (optional)
    url: str | None = None
    poll_interval_seconds: int | None = None
    historical_days_back: int | None = None

    # MQTT fields (optional)
    mqtt_host: str | None = None
    mqtt_port: int | None = None
    mqtt_topic_pattern: str | None = None
    mqtt_use_tls: bool | None = None

    # Status
    last_poll_at: datetime | None = None
    last_error: str | None = None
    remote_version: str | None = None  # Version from remote MeshMonitor instance
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SourceTestResult(BaseModel):
    """Result of testing a source connection."""

    success: bool
    message: str
    nodes_found: int | None = None
