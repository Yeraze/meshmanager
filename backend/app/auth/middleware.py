"""Authentication middleware."""

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.models.user import ANONYMOUS_USER_ID


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Get the current user from session, or None if not authenticated."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None

    # Block access if TOTP verification is still pending
    if request.session.get("totp_pending"):
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar()

    if user and not user.is_active:
        return None

    return user


async def get_current_user(
    user: User | None = Depends(get_current_user_optional),
) -> User:
    """Get the current user, or raise 401 if not authenticated."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


async def require_admin(
    user: User = Depends(get_current_user),
) -> None:
    """Require the current user to be an admin."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


def require_permission(tab: str, action: str = "read") -> Callable:
    """Factory that returns a dependency requiring a specific permission."""

    async def _check_permission(
        user: User = Depends(get_current_user),
    ) -> None:
        if not user.has_permission(tab, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {tab} {action}",
            )

    return _check_permission


async def get_effective_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get session user if authenticated, otherwise the anonymous user.

    Used by data endpoints to enforce tab-based permissions for both
    authenticated and unauthenticated visitors.
    """
    user = await get_current_user_optional(request, db)
    if user is not None:
        return user

    # Load the built-in anonymous user
    result = await db.execute(select(User).where(User.id == ANONYMOUS_USER_ID))
    anon = result.scalar()
    if not anon:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return anon


def require_tab_access(tab: str, action: str = "read") -> Callable:
    """Factory that returns a dependency checking tab permissions.

    Unlike require_permission (which requires a session), this uses
    get_effective_user so unauthenticated visitors are checked against
    the anonymous user's permissions.

    Returns 401 for anonymous users denied access (prompts login).
    Returns 403 for authenticated users denied access (forbidden).
    """

    async def _check_tab_access(
        user: User = Depends(get_effective_user),
    ) -> None:
        if user.has_permission(tab, action):
            return
        if user.is_anonymous:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {tab} {action}",
        )

    return _check_tab_access
