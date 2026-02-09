"""Schemas for authentication."""

from pydantic import BaseModel, Field


class TabPermission(BaseModel):
    """Permission for a single tab."""

    read: bool = True
    write: bool = False


class UserPermissions(BaseModel):
    """Granular per-tab permissions."""

    map: TabPermission = TabPermission()
    nodes: TabPermission = TabPermission()
    graphs: TabPermission = TabPermission()
    analysis: TabPermission = TabPermission()
    communication: TabPermission = TabPermission()
    settings: TabPermission = TabPermission()


class UserInfo(BaseModel):
    """Current user information."""

    id: str
    username: str | None = None
    email: str | None = None
    display_name: str | None = None
    role: str = "user"
    is_admin: bool = False
    auth_provider: str = "local"
    permissions: UserPermissions = UserPermissions()
    totp_enabled: bool = False

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
    setup_required: bool = False
    totp_required: bool = False
    local_auth_disabled: bool = False


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


class TotpSetupResponse(BaseModel):
    """Response for TOTP setup initiation."""

    secret: str
    qr_code_svg: str
    provisioning_uri: str


class TotpEnableRequest(BaseModel):
    """Request to enable TOTP after setup."""

    code: str = Field(..., pattern=r"^\d{6}$")


class TotpDisableRequest(BaseModel):
    """Request to disable TOTP."""

    code: str = Field(..., pattern=r"^\d{6}$")


class TotpVerifyRequest(BaseModel):
    """Request to verify TOTP during login."""

    code: str = Field(..., pattern=r"^\d{6}$")
