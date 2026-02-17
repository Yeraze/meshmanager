"""PacketRecord model for encrypted, unknown, and nodeinfo packets."""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utc_now


class PacketRecordType(enum.StrEnum):
    """Type of packet record."""

    ENCRYPTED = "encrypted"
    UNKNOWN = "unknown"
    NODEINFO = "nodeinfo"


class PacketRecord(Base):
    """A record of an encrypted, unknown, or nodeinfo packet."""

    __tablename__ = "packet_records"
    __table_args__ = (
        Index(
            "idx_packet_records_unique",
            "source_id",
            "from_node_num",
            "packet_type",
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
    to_node_num: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    meshtastic_id: Mapped[int | None] = mapped_column(BigInteger, index=True)

    packet_type: Mapped[PacketRecordType] = mapped_column(
        Enum(PacketRecordType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    portnum: Mapped[str | None] = mapped_column(String(100), nullable=True)

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )

    # Relationships
    source: Mapped["Source"] = relationship("Source", back_populates="packet_records")  # noqa: F821
