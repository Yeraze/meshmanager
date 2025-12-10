"""Coverage grid model for storing generated heatmap data."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CoverageCell(Base):
    """A single cell in the coverage grid heatmap."""

    __tablename__ = "coverage_cells"

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
    # Count of position reports in this cell
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    # Color for rendering (precomputed)
    color: Mapped[str] = mapped_column(String(50), nullable=False)
    # Timestamps
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )
