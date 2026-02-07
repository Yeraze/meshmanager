"""Channel model for channel configurations."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utc_now


class Channel(Base):
    """A channel configuration from a source."""

    __tablename__ = "channels"

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

    channel_index: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(String(12))
    role: Mapped[str | None] = mapped_column(String(20))  # primary, secondary, disabled

    uplink_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    downlink_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    position_precision: Mapped[int | None] = mapped_column(Integer)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    source: Mapped["Source"] = relationship("Source", back_populates="channels")  # noqa: F821
