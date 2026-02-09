"""User model for local and OIDC authentication."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, utc_now

VALID_TABS = ("map", "nodes", "graphs", "analysis", "communication", "settings")

DEFAULT_PERMISSIONS: dict = {
    tab: {"read": True, "write": False} for tab in VALID_TABS
}


class User(Base):
    """A user authenticated via local credentials or OIDC."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Authentication provider: 'local' or 'oidc'
    auth_provider: Mapped[str] = mapped_column(String(20), default="local")

    # Local authentication
    username: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))

    # OIDC authentication (optional)
    oidc_subject: Mapped[str | None] = mapped_column(String(255), unique=True)
    oidc_issuer: Mapped[str | None] = mapped_column(String(500))

    # User info
    email: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255))

    # Permissions
    role: Mapped[str] = mapped_column(String(20), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    permissions: Mapped[dict] = mapped_column(JSON, default=lambda: dict(DEFAULT_PERMISSIONS))

    # TOTP/MFA
    totp_secret: Mapped[str | None] = mapped_column(String(255))
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role == "admin"

    def has_permission(self, tab: str, action: str = "read") -> bool:
        """Check if user has a specific permission.

        Admins always have full access. Other users check the permissions dict.
        """
        if self.is_admin:
            return True
        if tab not in VALID_TABS:
            return False
        perms = self.permissions or DEFAULT_PERMISSIONS
        tab_perms = perms.get(tab, {})
        return bool(tab_perms.get(action, False))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
