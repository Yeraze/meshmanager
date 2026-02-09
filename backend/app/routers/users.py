"""User management endpoints (admin only)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import get_current_user, require_admin
from app.auth.password import hash_password
from app.database import get_db
from app.models import User
from app.models.user import DEFAULT_PERMISSIONS, VALID_TABS
from app.schemas.users import UserCreate, UserListItem, UserUpdate

router = APIRouter(prefix="/api/admin/users", tags=["users"])

VALID_ACTIONS = {"read", "write"}


def _validate_permissions(permissions: dict) -> None:
    """Validate that a permissions dict only contains valid tabs and actions."""
    for key, value in permissions.items():
        if key not in VALID_TABS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid permission tab: {key}",
            )
        if not isinstance(value, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Permission for '{key}' must be an object",
            )
        for action, enabled in value.items():
            if action not in VALID_ACTIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid permission action: {action}",
                )
            if not isinstance(enabled, bool):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Permission value for '{key}.{action}' must be a boolean",
                )


@router.get("", response_model=list[UserListItem])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
) -> list[UserListItem]:
    """List all users."""
    result = await db.execute(select(User).order_by(User.created_at))
    users = result.scalars().all()
    return [UserListItem.model_validate(u) for u in users]


@router.post("", response_model=UserListItem, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
) -> UserListItem:
    """Create a new user."""
    # Check username uniqueness
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    permissions = (
        user_data.permissions.model_dump() if user_data.permissions else dict(DEFAULT_PERMISSIONS)
    )
    _validate_permissions(permissions)

    user = User(
        auth_provider="local",
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        email=user_data.email,
        display_name=user_data.display_name or user_data.username,
        role="admin" if user_data.is_admin else "user",
        permissions=permissions,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserListItem.model_validate(user)


@router.put("/{user_id}", response_model=UserListItem)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _admin: None = Depends(require_admin),
) -> UserListItem:
    """Update a user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Prevent self-demotion or self-deactivation
    if user.id == current_user.id:
        if user_data.is_admin is not None and not user_data.is_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove your own admin status",
            )
        if user_data.is_active is not None and not user_data.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account",
            )

    update_data = user_data.model_dump(exclude_unset=True)

    # Handle is_admin -> role mapping
    if "is_admin" in update_data:
        is_admin = update_data.pop("is_admin")
        if is_admin is not None:
            if not is_admin and user.role == "admin":
                # Prevent demoting the last admin
                admin_count = await db.scalar(
                    select(func.count()).select_from(User).where(User.role == "admin")
                )
                if admin_count <= 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot remove the last admin",
                    )
            user.role = "admin" if is_admin else "user"

    # Handle permissions
    if "permissions" in update_data:
        permissions = update_data.pop("permissions")
        if permissions is not None:
            _validate_permissions(permissions)
            user.permissions = permissions

    # Handle TOTP reset
    if "reset_totp" in update_data:
        reset_totp = update_data.pop("reset_totp")
        if reset_totp:
            user.totp_secret = None
            user.totp_enabled = False

    # Hash password if provided
    if "password" in update_data:
        password = update_data.pop("password")
        if password:
            user.password_hash = hash_password(password)

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return UserListItem.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _admin: None = Depends(require_admin),
) -> None:
    """Delete a user."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Prevent deleting the last admin
    if user.role == "admin":
        admin_count = await db.scalar(
            select(func.count()).select_from(User).where(User.role == "admin")
        )
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last admin",
            )

    await db.delete(user)
    await db.commit()
