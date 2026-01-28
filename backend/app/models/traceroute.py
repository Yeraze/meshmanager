"""Traceroute model for route information."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Traceroute(Base):
    """A traceroute between two nodes."""

    __tablename__ = "traceroutes"
    __table_args__ = (
        Index(
            "idx_traceroutes_unique",
            "source_id",
            "from_node_num",
            "to_node_num",
            "received_at",
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

    from_node_num: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    to_node_num: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # Route data (arrays of node numbers)
    route: Mapped[list[int] | None] = mapped_column(ARRAY(BigInteger))
    route_back: Mapped[list[int] | None] = mapped_column(ARRAY(BigInteger))

    # SNR data (arrays of floats as integers, dB * 4)
    snr_towards: Mapped[list[int] | None] = mapped_column(ARRAY(BigInteger))
    snr_back: Mapped[list[int] | None] = mapped_column(ARRAY(BigInteger))

    # Timestamp
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )

    # Relationships
    source: Mapped["Source"] = relationship("Source", back_populates="traceroutes")  # noqa: F821
