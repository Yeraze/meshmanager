"""OIDC authentication client."""

from datetime import UTC, datetime

from authlib.integrations.starlette_client import OAuth
from sqlalchemy import func, select

from app.config import get_settings
from app.database import async_session_maker
from app.models import User

settings = get_settings()

# OAuth client instance
_oauth: OAuth | None = None


def get_oauth_client() -> OAuth:
    """Get or create the OAuth client."""
    global _oauth
    if _oauth is None:
        _oauth = OAuth()
        if settings.oidc_enabled:
            _oauth.register(
                name="oidc",
                client_id=settings.oidc_client_id,
                client_secret=settings.oidc_client_secret,
                server_metadata_url=f"{settings.oidc_issuer}/.well-known/openid-configuration",
                client_kwargs={"scope": "openid email profile"},
            )
    return _oauth


async def process_oidc_callback(token: dict) -> User:
    """Process OIDC callback and create/update user."""
    userinfo = token.get("userinfo", {})

    # Extract user info from token
    subject = userinfo.get("sub")
    if not subject:
        raise ValueError("No subject in OIDC token")

    email = userinfo.get("email")
    display_name = userinfo.get("name") or userinfo.get("preferred_username")

    async with async_session_maker() as db:
        # Check if user exists
        result = await db.execute(
            select(User).where(User.oidc_subject == subject)
        )
        user = result.scalar()

        if user:
            # Update existing user
            user.email = email
            user.display_name = display_name
            user.last_login_at = datetime.now(UTC)
        else:
            # Check if this is the first user (make them admin)
            count_result = await db.execute(select(func.count()).select_from(User))
            user_count = count_result.scalar() or 0

            # Create new user
            user = User(
                oidc_subject=subject,
                oidc_issuer=settings.oidc_issuer or "",
                email=email,
                display_name=display_name,
                is_admin=user_count == 0,  # First user is admin
                last_login_at=datetime.now(UTC),
            )
            db.add(user)

        await db.commit()
        await db.refresh(user)

    return user
