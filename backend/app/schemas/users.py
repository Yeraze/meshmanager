"""Schemas for user management."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.auth import UserPermissions


class UserListItem(BaseModel):
    """User item in admin list."""

    id: str
    username: str | None = None
    email: str | None = None
    display_name: str | None = None
    role: str = "user"
    is_admin: bool = False
    auth_provider: str = "local"
    is_active: bool = True
    permissions: UserPermissions = UserPermissions()
    totp_enabled: bool = False
    created_at: datetime | None = None
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    """Create a new user (admin only)."""

    username: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8)
    email: str | None = Field(default=None, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    is_admin: bool = False
    permissions: UserPermissions | None = None


class UserUpdate(BaseModel):
    """Update an existing user (admin only)."""

    email: str | None = None
    display_name: str | None = None
    is_admin: bool | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)
    permissions: UserPermissions | None = None
    reset_totp: bool | None = None
