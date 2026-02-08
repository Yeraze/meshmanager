"""Schemas for authentication."""

from pydantic import BaseModel, Field


class UserInfo(BaseModel):
    """Current user information."""

    id: str
    username: str | None = None
    email: str | None = None
    display_name: str | None = None
    role: str = "viewer"
    auth_provider: str = "local"

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """OAuth token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int | None = None


class AuthStatus(BaseModel):
    """Authentication status response."""

    authenticated: bool
    user: UserInfo | None = None
    oidc_enabled: bool = False
    setup_required: bool = False  # True if no users exist yet


class LoginRequest(BaseModel):
    """Local login request."""

    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    """Registration request (for initial setup or admin creating users)."""

    username: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8)
    email: str | None = Field(default=None, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)


class ChangePasswordRequest(BaseModel):
    """Change password request."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)
