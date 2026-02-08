"""Tests for user management endpoints."""

import pytest

from app.models.user import User
from app.schemas.users import UserCreate, UserListItem, UserUpdate


class TestUserSchemas:
    """Tests for user schemas."""

    def test_user_list_item_from_model(self):
        """UserListItem should validate from User model attributes."""
        item = UserListItem(
            id="test-id",
            username="testuser",
            role="viewer",
            auth_provider="local",
            is_active=True,
        )
        assert item.id == "test-id"
        assert item.role == "viewer"

    def test_user_create_valid(self):
        """UserCreate should accept valid data."""
        user = UserCreate(
            username="newuser",
            password="password123",
            role="editor",
        )
        assert user.username == "newuser"
        assert user.role == "editor"

    def test_user_create_default_role(self):
        """UserCreate should default to viewer role."""
        user = UserCreate(
            username="newuser",
            password="password123",
        )
        assert user.role == "viewer"

    def test_user_create_invalid_role(self):
        """UserCreate should reject invalid roles."""
        with pytest.raises(Exception):
            UserCreate(
                username="newuser",
                password="password123",
                role="superadmin",
            )

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
        update = UserUpdate(role="admin")
        data = update.model_dump(exclude_unset=True)
        assert data == {"role": "admin"}

    def test_user_update_invalid_role(self):
        """UserUpdate should reject invalid roles."""
        with pytest.raises(Exception):
            UserUpdate(role="superadmin")


class TestUserModel:
    """Tests for User model role behavior."""

    def test_is_admin_property_true(self):
        """is_admin property should return True for admin role."""
        user = User(role="admin")
        assert user.is_admin is True

    def test_is_admin_property_false_editor(self):
        """is_admin property should return False for editor role."""
        user = User(role="editor")
        assert user.is_admin is False

    def test_is_admin_property_false_viewer(self):
        """is_admin property should return False for viewer role."""
        user = User(role="viewer")
        assert user.is_admin is False
