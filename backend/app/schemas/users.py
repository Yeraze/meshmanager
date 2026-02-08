"""Schemas for user management."""

from datetime import datetime

from pydantic import BaseModel, Field


class UserListItem(BaseModel):
    """User item in admin list."""

    id: str
    username: str | None = None
    email: str | None = None
    display_name: str | None = None
    role: str = "viewer"
    auth_provider: str = "local"
    is_active: bool = True
    created_at: datetime | None = None
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    """Create a new user (admin only)."""

    username: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8)
    email: str | None = Field(default=None, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    role: str = Field(default="viewer", pattern=r"^(admin|editor|viewer)$")


class UserUpdate(BaseModel):
    """Update an existing user (admin only)."""

    email: str | None = None
    display_name: str | None = None
    role: str | None = Field(default=None, pattern=r"^(admin|editor|viewer)$")
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)
