"""Message model for text messages."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Message(Base):
    """A text message from the mesh network."""

    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_messages_source_packet", "source_id", "packet_id", unique=True),
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

    # Message identification
    packet_id: Mapped[str | None] = mapped_column(String(64))  # Source-specific ID (composite for MeshMonitor)
    meshtastic_id: Mapped[int | None] = mapped_column(BigInteger, index=True)  # Raw Meshtastic packet ID
    from_node_num: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    to_node_num: Mapped[int | None] = mapped_column(BigInteger)
    channel: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str | None] = mapped_column(Text)

    # Reply/reaction
    reply_id: Mapped[int | None] = mapped_column(BigInteger)
    emoji: Mapped[str | None] = mapped_column(String(10))

    # Metadata
    hop_limit: Mapped[int | None] = mapped_column(Integer)
    hop_start: Mapped[int | None] = mapped_column(Integer)
    rx_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rx_snr: Mapped[float | None] = mapped_column(Integer)  # Stored as int, represents dB * 4
    rx_rssi: Mapped[int | None] = mapped_column(Integer)

    # Timestamp
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        index=True,
    )

    # Relationships
    source: Mapped["Source"] = relationship("Source", back_populates="messages")  # noqa: F821
