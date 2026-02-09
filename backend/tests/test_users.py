"""Tests for user management endpoints."""

import pytest

from app.models.user import DEFAULT_PERMISSIONS, User
from app.schemas.auth import TabPermission, UserPermissions
from app.schemas.users import UserCreate, UserListItem, UserUpdate


class TestUserSchemas:
    """Tests for user schemas."""

    def test_user_list_item_from_model(self):
        """UserListItem should validate from User model attributes."""
        item = UserListItem(
            id="test-id",
            username="testuser",
            role="user",
            auth_provider="local",
            is_active=True,
        )
        assert item.id == "test-id"
        assert item.role == "user"
        assert item.is_admin is False

    def test_user_list_item_admin(self):
        """UserListItem should support is_admin field."""
        item = UserListItem(
            id="test-id",
            username="admin",
            role="admin",
            is_admin=True,
            auth_provider="local",
            is_active=True,
        )
        assert item.is_admin is True

    def test_user_create_valid(self):
        """UserCreate should accept valid data."""
        user = UserCreate(
            username="newuser",
            password="password123",
            is_admin=False,
        )
        assert user.username == "newuser"
        assert user.is_admin is False

    def test_user_create_default_permissions(self):
        """UserCreate should default to non-admin with no permissions."""
        user = UserCreate(
            username="newuser",
            password="password123",
        )
        assert user.is_admin is False
        assert user.permissions is None

    def test_user_create_with_permissions(self):
        """UserCreate should accept custom permissions."""
        perms = UserPermissions(
            settings=TabPermission(read=True, write=True),
        )
        user = UserCreate(
            username="newuser",
            password="password123",
            permissions=perms,
        )
        assert user.permissions is not None
        assert user.permissions.settings.write is True

    def test_user_create_short_username(self):
        """UserCreate should reject short usernames."""
        with pytest.raises(Exception):
            UserCreate(
                username="ab",
                password="password123",
            )

    def test_user_create_short_password(self):
        """UserCreate should reject short passwords."""
        with pytest.raises(Exception):
            UserCreate(
                username="newuser",
                password="short",
            )

    def test_user_update_partial(self):
        """UserUpdate should allow partial updates."""
        update = UserUpdate(is_admin=True)
        data = update.model_dump(exclude_unset=True)
        assert data == {"is_admin": True}

    def test_user_update_permissions(self):
        """UserUpdate should allow permissions updates."""
        perms = UserPermissions(
            map=TabPermission(read=True, write=True),
        )
        update = UserUpdate(permissions=perms)
        data = update.model_dump(exclude_unset=True)
        assert "permissions" in data

    def test_user_update_reset_totp(self):
        """UserUpdate should support reset_totp field."""
        update = UserUpdate(reset_totp=True)
        data = update.model_dump(exclude_unset=True)
        assert data == {"reset_totp": True}


class TestUserModel:
    """Tests for User model role behavior."""

    def test_is_admin_property_true(self):
        """is_admin property should return True for admin role."""
        user = User(role="admin")
        assert user.is_admin is True

    def test_is_admin_property_false_user(self):
        """is_admin property should return False for user role."""
        user = User(role="user")
        assert user.is_admin is False

    def test_has_permission_admin_always_true(self):
        """Admin should always have permission."""
        user = User(role="admin")
        assert user.has_permission("settings", "write") is True
        assert user.has_permission("map", "read") is True

    def test_has_permission_user_default(self):
        """User with default permissions should have read but not write."""
        user = User(role="user", permissions=dict(DEFAULT_PERMISSIONS))
        assert user.has_permission("map", "read") is True
        assert user.has_permission("map", "write") is False
        assert user.has_permission("settings", "read") is True
        assert user.has_permission("settings", "write") is False

    def test_has_permission_custom(self):
        """User with custom permissions should reflect those permissions."""
        perms = dict(DEFAULT_PERMISSIONS)
        perms["settings"] = {"read": True, "write": True}
        user = User(role="user", permissions=perms)
        assert user.has_permission("settings", "write") is True
        assert user.has_permission("map", "write") is False

    def test_has_permission_invalid_tab(self):
        """User should not have permission for invalid tab."""
        user = User(role="user", permissions=dict(DEFAULT_PERMISSIONS))
        assert user.has_permission("nonexistent", "read") is False

    def test_default_permissions_constant(self):
        """DEFAULT_PERMISSIONS should have all tabs with read=True, write=False."""
        for tab in ("map", "nodes", "graphs", "analysis", "communication", "settings"):
            assert tab in DEFAULT_PERMISSIONS
            assert DEFAULT_PERMISSIONS[tab]["read"] is True
            assert DEFAULT_PERMISSIONS[tab]["write"] is False
