"""Authentication endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import get_current_user, get_current_user_optional
from app.auth.password import hash_password, verify_password
from app.config import get_settings
from app.database import get_db
from app.models import User
from app.schemas.auth import (
    AuthStatus,
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TotpDisableRequest,
    TotpEnableRequest,
    TotpSetupResponse,
    TotpVerifyRequest,
    UserInfo,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


async def _get_user_count(db: AsyncSession) -> int:
    """Get total user count."""
    result = await db.execute(select(func.count()).select_from(User))
    return result.scalar() or 0


@router.get("/status")
async def auth_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> AuthStatus:
    """Get current authentication status."""
    user_count = await _get_user_count(db)

    return AuthStatus(
        authenticated=user is not None,
        user=UserInfo.model_validate(user) if user else None,
        oidc_enabled=settings.oidc_enabled,
        setup_required=user_count == 0,
        totp_required=bool(request.session.get("totp_pending")),
    )


@router.post("/login")
async def login(
    request: Request,
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Log in with username and password."""
    # Find user by username
    result = await db.execute(
        select(User).where(
            User.username == credentials.username,
            User.auth_provider == "local",
        )
    )
    user = result.scalar()

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled",
        )

    # If TOTP is enabled, set pending state
    if user.totp_enabled:
        request.session["user_id"] = user.id
        request.session["totp_pending"] = True
        return {"message": "TOTP verification required", "totp_required": True}

    # Update last login
    user.last_login_at = datetime.now(UTC)
    await db.commit()

    # Store user ID in session
    request.session["user_id"] = user.id

    return {"message": "Login successful", "user": UserInfo.model_validate(user)}


@router.post("/totp/verify")
async def verify_totp(
    request: Request,
    body: TotpVerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Verify TOTP code during login (second factor)."""
    user_id = request.session.get("user_id")
    if not user_id or not request.session.get("totp_pending"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No TOTP verification pending",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar()
    if not user or not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP not configured for this user",
        )

    from app.auth.totp import verify_totp_code

    if not verify_totp_code(user.totp_secret, body.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code",
        )

    # Clear pending state and complete login
    request.session.pop("totp_pending", None)
    user.last_login_at = datetime.now(UTC)
    await db.commit()

    return {"message": "Login successful", "user": UserInfo.model_validate(user)}


@router.post("/totp/setup", response_model=TotpSetupResponse)
async def setup_totp(
    request: Request,
    user: User = Depends(get_current_user),
) -> TotpSetupResponse:
    """Generate TOTP secret and QR code for setup."""
    if user.auth_provider != "local":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP is not available for OIDC users",
        )

    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP is already enabled",
        )

    from app.auth.totp import generate_qr_code_svg, generate_totp_secret, get_provisioning_uri

    secret = generate_totp_secret()
    uri = get_provisioning_uri(secret, user.username or user.email or user.id)
    qr_svg = generate_qr_code_svg(uri)

    # Store secret in session until confirmed
    request.session["totp_setup_secret"] = secret

    return TotpSetupResponse(
        secret=secret,
        qr_code_svg=qr_svg,
        provisioning_uri=uri,
    )


@router.post("/totp/enable")
async def enable_totp(
    request: Request,
    body: TotpEnableRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Enable TOTP after verifying the setup code."""
    secret = request.session.get("totp_setup_secret")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No TOTP setup in progress. Call /auth/totp/setup first.",
        )

    from app.auth.totp import verify_totp_code

    if not verify_totp_code(secret, body.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code. Please try again.",
        )

    user.totp_secret = secret
    user.totp_enabled = True
    await db.commit()

    request.session.pop("totp_setup_secret", None)

    return {"message": "TOTP enabled successfully"}


@router.post("/totp/disable")
async def disable_totp(
    request: Request,
    body: TotpDisableRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Disable TOTP by verifying current code."""
    if not user.totp_enabled or not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP is not enabled",
        )

    from app.auth.totp import verify_totp_code

    if not verify_totp_code(user.totp_secret, body.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code",
        )

    user.totp_secret = None
    user.totp_enabled = False
    await db.commit()

    return {"message": "TOTP disabled successfully"}


@router.post("/register")
async def register(
    request: Request,
    registration: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Register a new user.

    The first user registered becomes an admin.
    After that, only admins can create new users.
    """
    user_count = await _get_user_count(db)

    # If users exist, require admin authentication
    if user_count > 0:
        user_id = request.session.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        result = await db.execute(select(User).where(User.id == user_id))
        current_user = result.scalar()
        if not current_user or not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can create new users",
            )

    # Check if username is taken
    result = await db.execute(
        select(User).where(User.username == registration.username)
    )
    if result.scalar():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    # Create user
    user = User(
        auth_provider="local",
        username=registration.username,
        password_hash=hash_password(registration.password),
        email=registration.email,
        display_name=registration.display_name or registration.username,
        role="admin" if user_count == 0 else "user",
        last_login_at=datetime.now(UTC),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Auto-login after registration
    request.session["user_id"] = user.id

    return {
        "message": "Registration successful",
        "user": UserInfo.model_validate(user),
    }


@router.post("/logout")
async def logout(request: Request) -> dict:
    """Log out the current user."""
    request.session.clear()
    return {"message": "Logged out"}


@router.post("/change-password")
async def change_password(
    password_change: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Change the current user's password."""
    if user.auth_provider != "local":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change password for OIDC users",
        )

    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No password set for this account",
        )

    if not verify_password(password_change.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    user.password_hash = hash_password(password_change.new_password)
    await db.commit()

    return {"message": "Password changed successfully"}


# OIDC routes (only if configured)
@router.get("/oidc/login")
async def oidc_login(request: Request) -> RedirectResponse:
    """Initiate OIDC login flow."""
    if not settings.oidc_enabled:
        raise HTTPException(status_code=400, detail="OIDC is not configured")

    from app.auth.oidc import get_oauth_client

    oauth = get_oauth_client()
    redirect_uri = settings.oidc_redirect_uri or str(request.url_for("oidc_callback"))
    return await oauth.oidc.authorize_redirect(request, redirect_uri)


@router.get("/oidc/callback")
async def oidc_callback(request: Request) -> RedirectResponse:
    """Handle OIDC callback."""
    if not settings.oidc_enabled:
        raise HTTPException(status_code=400, detail="OIDC is not configured")

    from app.auth.oidc import get_oauth_client, process_oidc_callback

    oauth = get_oauth_client()
    token = await oauth.oidc.authorize_access_token(request)

    # Process the callback and create/update user
    user = await process_oidc_callback(token)

    # Store user ID in session
    request.session["user_id"] = user.id

    # Redirect to frontend
    return RedirectResponse(url="/", status_code=302)
