"""Solar production data model for storing hourly watt-hours data."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SolarProduction(Base):
    """Hourly solar production data from MeshMonitor sources."""

    __tablename__ = "solar_production"
    __table_args__ = (
        # Unique constraint to prevent duplicate entries for same source/timestamp
        Index(
            "ix_solar_production_unique",
            "source_id",
            "timestamp",
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

    # The timestamp of the solar production data (hourly buckets)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Watt-hours produced in this hour
    watt_hours: Mapped[float] = mapped_column(Float, nullable=False)

    # When this data was fetched from the solar system (may differ from timestamp)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # When we received/stored this record
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )

    # Relationships
    source: Mapped["Source"] = relationship("Source", back_populates="solar_production")  # noqa: F821
