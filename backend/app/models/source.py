"""Source model for MeshMonitor and MQTT data sources."""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utc_now


class SourceType(enum.StrEnum):
    """Type of data source."""

    MESHMONITOR = "meshmonitor"
    MQTT = "mqtt"


class Source(Base):
    """Configuration for a data source (MeshMonitor instance or MQTT broker)."""

    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)

    # MeshMonitor specific
    url: Mapped[str | None] = mapped_column(String(500))
    api_token: Mapped[str | None] = mapped_column(String(500))
    poll_interval_seconds: Mapped[int] = mapped_column(Integer, default=300, server_default=text("300"))
    historical_days_back: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1")
    )  # Days of historical data to sync

    # MQTT specific
    mqtt_host: Mapped[str | None] = mapped_column(String(255))
    mqtt_port: Mapped[int | None] = mapped_column(Integer, default=1883, server_default=text("1883"))
    mqtt_username: Mapped[str | None] = mapped_column(String(255))
    mqtt_password: Mapped[str | None] = mapped_column(String(500))
    mqtt_topic_pattern: Mapped[str | None] = mapped_column(String(500))
    mqtt_use_tls: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))

    # Common
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    last_poll_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    remote_version: Mapped[str | None] = mapped_column(String(50))  # Version from remote source
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    nodes: Mapped[list["Node"]] = relationship(  # noqa: F821
        "Node",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list["Message"]] = relationship(  # noqa: F821
        "Message",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    telemetry: Mapped[list["Telemetry"]] = relationship(  # noqa: F821
        "Telemetry",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    traceroutes: Mapped[list["Traceroute"]] = relationship(  # noqa: F821
        "Traceroute",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    packet_records: Mapped[list["PacketRecord"]] = relationship(  # noqa: F821
        "PacketRecord",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    channels: Mapped[list["Channel"]] = relationship(  # noqa: F821
        "Channel",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    solar_production: Mapped[list["SolarProduction"]] = relationship(  # noqa: F821
        "SolarProduction",
        back_populates="source",
        cascade="all, delete-orphan",
    )
