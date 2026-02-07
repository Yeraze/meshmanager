"""Node model for Meshtastic nodes."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Double,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utc_now


class Node(Base):
    """A Meshtastic node as seen from a specific source."""

    __tablename__ = "nodes"

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

    # Node identification
    node_num: Mapped[int] = mapped_column(BigInteger, nullable=False)
    node_id: Mapped[str | None] = mapped_column(String(20))  # e.g., "!abcd1234"
    short_name: Mapped[str | None] = mapped_column(String(10))
    long_name: Mapped[str | None] = mapped_column(String(40), index=True)
    hw_model: Mapped[str | None] = mapped_column(String(50))
    role: Mapped[str | None] = mapped_column(String(30))

    # Position
    latitude: Mapped[float | None] = mapped_column(Double)
    longitude: Mapped[float | None] = mapped_column(Double)
    altitude: Mapped[int | None] = mapped_column(Integer)
    position_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    position_precision_bits: Mapped[int | None] = mapped_column(Integer)

    # Signal info
    snr: Mapped[float | None] = mapped_column(Double)
    rssi: Mapped[int | None] = mapped_column(Integer)
    hops_away: Mapped[int | None] = mapped_column(Integer)

    # Status
    last_heard: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    is_licensed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    source: Mapped["Source"] = relationship("Source", back_populates="nodes")  # noqa: F821

    __table_args__ = (UniqueConstraint("source_id", "node_num", name="uq_nodes_source_node"),)
