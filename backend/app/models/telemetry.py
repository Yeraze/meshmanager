"""Telemetry model for device metrics."""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, Enum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utc_now


class TelemetryType(enum.StrEnum):
    """Type of telemetry data."""

    DEVICE = "device"
    ENVIRONMENT = "environment"
    POWER = "power"
    AIR_QUALITY = "air_quality"
    POSITION = "position"
    LOCAL_STATS = "local_stats"
    HEALTH = "health"
    HOST = "host"


class Telemetry(Base):
    """Telemetry data from a node."""

    __tablename__ = "telemetry"
    __table_args__ = (
        Index(
            "ix_telemetry_unique_metric",
            "source_id",
            "node_num",
            "received_at",
            "metric_name",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    source_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_num: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # Metric identifier for deduplication (e.g., "battery_level", "voltage", etc.)
    metric_name: Mapped[str | None] = mapped_column(String(50), index=True)

    telemetry_type: Mapped[TelemetryType] = mapped_column(
        Enum(TelemetryType),
        nullable=False,
        index=True,
    )

    # Device metrics
    battery_level: Mapped[int | None] = mapped_column(Integer)  # 0-100
    voltage: Mapped[float | None] = mapped_column(Float)
    channel_utilization: Mapped[float | None] = mapped_column(Float)  # 0-100
    air_util_tx: Mapped[float | None] = mapped_column(Float)  # 0-100
    uptime_seconds: Mapped[int | None] = mapped_column(BigInteger)

    # Environment metrics
    temperature: Mapped[float | None] = mapped_column(Float)  # Celsius
    relative_humidity: Mapped[float | None] = mapped_column(Float)  # 0-100
    barometric_pressure: Mapped[float | None] = mapped_column(Float)  # hPa

    # Power metrics
    current: Mapped[float | None] = mapped_column(Float)  # mA

    # Signal metrics
    snr_local: Mapped[float | None] = mapped_column(Float)  # dB - local SNR
    snr_remote: Mapped[float | None] = mapped_column(Float)  # dB - remote SNR
    rssi: Mapped[float | None] = mapped_column(Float)  # dBm - RSSI

    # Position metrics (for coverage analysis)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    altitude: Mapped[int | None] = mapped_column(Integer)

    # Generic value for any telemetry type (stores the raw value when no specific column exists)
    raw_value: Mapped[float | None] = mapped_column(Float)

    # Timestamp
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )

    # Relationships
    source: Mapped["Source"] = relationship("Source", back_populates="telemetry")  # noqa: F821
