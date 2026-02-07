"""Utilization grid model for storing channel utilization heatmap data."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, utc_now


class UtilizationCell(Base):
    """A single cell in the utilization grid heatmap."""

    __tablename__ = "utilization_cells"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    # Grid bounds
    south: Mapped[float] = mapped_column(Float, nullable=False)
    west: Mapped[float] = mapped_column(Float, nullable=False)
    north: Mapped[float] = mapped_column(Float, nullable=False)
    east: Mapped[float] = mapped_column(Float, nullable=False)
    # Utilization value (min, max, or avg depending on config)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    # Color for rendering (precomputed)
    color: Mapped[str] = mapped_column(String(50), nullable=False)
    # Timestamps
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
