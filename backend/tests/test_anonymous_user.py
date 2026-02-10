"""Tests for anonymous user permissions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.auth.middleware import get_effective_user, invalidate_anon_cache, require_tab_access
from app.models.user import (
    ANONYMOUS_DEFAULT_PERMISSIONS,
    ANONYMOUS_USER_ID,
    DEFAULT_PERMISSIONS,
    User,
)
from app.schemas.auth import AuthStatus, UserPermissions
from app.schemas.users import UserListItem, UserUpdate


class TestAnonymousUserModel:
    """Tests for anonymous user model constants."""

    def test_anonymous_user_id_is_well_known(self):
        """Anonymous user ID should be the well-known UUID."""
        assert ANONYMOUS_USER_ID == "00000000-0000-0000-0000-000000000000"

    def test_anonymous_default_permissions_read_all_except_settings(self):
        """Anonymous default permissions should allow read on all tabs except settings."""
        for tab in ("map", "nodes", "graphs", "analysis", "communication"):
            assert ANONYMOUS_DEFAULT_PERMISSIONS[tab]["read"] is True
            assert ANONYMOUS_DEFAULT_PERMISSIONS[tab]["write"] is False
        assert ANONYMOUS_DEFAULT_PERMISSIONS["settings"]["read"] is False
        assert ANONYMOUS_DEFAULT_PERMISSIONS["settings"]["write"] is False

    def test_user_is_anonymous_field(self):
        """User model should have is_anonymous field."""
        user = User(
            id=ANONYMOUS_USER_ID,
            username="anonymous",
            auth_provider="system",
            is_anonymous=True,
            permissions=ANONYMOUS_DEFAULT_PERMISSIONS,
        )
        assert user.is_anonymous is True

    def test_regular_user_not_anonymous(self):
        """Regular users should not be anonymous."""
        user = User(
            id="some-id",
            username="testuser",
            auth_provider="local",
            is_anonymous=False,
        )
        assert user.is_anonymous is False


class TestGetEffectiveUser:
    """Tests for get_effective_user middleware."""

    @pytest.mark.asyncio
    async def test_returns_session_user_when_authenticated(self):
        """Should return the session user when authenticated."""
        invalidate_anon_cache()
        session_user = User(id="user-1", username="testuser", is_anonymous=False)
        request = MagicMock()
        request.session = {"user_id": "user-1"}

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar.return_value = session_user
        db.execute = AsyncMock(return_value=result_mock)

        with patch(
            "app.auth.middleware.get_current_user_optional",
            return_value=session_user,
        ):
            user = await get_effective_user(request, db)

        assert user.id == "user-1"
        assert user.is_anonymous is False

    @pytest.mark.asyncio
    async def test_returns_anonymous_user_when_not_authenticated(self):
        """Should return the anonymous user when no session."""
        invalidate_anon_cache()
        anon_user = User(
            id=ANONYMOUS_USER_ID,
            username="anonymous",
            is_anonymous=True,
            permissions=ANONYMOUS_DEFAULT_PERMISSIONS,
        )
        request = MagicMock()
        request.session = {}

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar.return_value = anon_user
        db.execute = AsyncMock(return_value=result_mock)

        with patch(
            "app.auth.middleware.get_current_user_optional",
            return_value=None,
        ):
            user = await get_effective_user(request, db)

        assert user.id == ANONYMOUS_USER_ID
        assert user.is_anonymous is True

    @pytest.mark.asyncio
    async def test_raises_401_when_anonymous_user_not_found(self):
        """Should raise 401 when anonymous user is missing from DB."""
        invalidate_anon_cache()
        request = MagicMock()
        request.session = {}

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        with patch(
            "app.auth.middleware.get_current_user_optional",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_effective_user(request, db)
            assert exc_info.value.status_code == 401


class TestRequireTabAccess:
    """Tests for require_tab_access middleware factory."""

    @pytest.mark.asyncio
    async def test_allows_access_when_permitted(self):
        """Should allow access when user has the permission."""
        user = User(
            id="user-1",
            username="testuser",
            permissions=DEFAULT_PERMISSIONS,
            is_anonymous=False,
        )
        checker = require_tab_access("map", "read")
        # Should not raise
        await checker(user)

    @pytest.mark.asyncio
    async def test_returns_401_for_anonymous_denied(self):
        """Should return 401 when anonymous user lacks permission."""
        user = User(
            id=ANONYMOUS_USER_ID,
            username="anonymous",
            is_anonymous=True,
            permissions=ANONYMOUS_DEFAULT_PERMISSIONS,
        )
        checker = require_tab_access("settings", "read")
        with pytest.raises(HTTPException) as exc_info:
            await checker(user)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_403_for_authenticated_denied(self):
        """Should return 403 when authenticated user lacks permission."""
        no_settings = dict(DEFAULT_PERMISSIONS)
        no_settings["settings"] = {"read": False, "write": False}
        user = User(
            id="user-1",
            username="testuser",
            is_anonymous=False,
            permissions=no_settings,
        )
        checker = require_tab_access("settings", "read")
        with pytest.raises(HTTPException) as exc_info:
            await checker(user)
        assert exc_info.value.status_code == 403


class TestAnonymousUserSchemas:
    """Tests for schema changes."""

    def test_user_info_has_is_anonymous(self):
        """UserInfo schema should include is_anonymous."""
        from app.schemas.auth import UserInfo

        info = UserInfo(id="test", is_anonymous=True)
        assert info.is_anonymous is True

    def test_user_info_defaults_not_anonymous(self):
        """UserInfo is_anonymous should default to False."""
        from app.schemas.auth import UserInfo

        info = UserInfo(id="test")
        assert info.is_anonymous is False

    def test_user_list_item_has_is_anonymous(self):
        """UserListItem should include is_anonymous."""
        item = UserListItem(
            id="test",
            is_anonymous=True,
            auth_provider="system",
        )
        assert item.is_anonymous is True

    def test_auth_status_has_anonymous_permissions(self):
        """AuthStatus should include anonymous_permissions field."""
        perms = UserPermissions()
        status = AuthStatus(
            authenticated=False,
            anonymous_permissions=perms,
        )
        assert status.anonymous_permissions is not None
        assert status.anonymous_permissions.map.read is True

    def test_auth_status_anonymous_permissions_defaults_none(self):
        """AuthStatus anonymous_permissions should default to None."""
        status = AuthStatus(authenticated=False)
        assert status.anonymous_permissions is None


class TestAnonymousUserGuards:
    """Tests for anonymous user protection in user management."""

    def test_user_update_only_permissions_schema(self):
        """UserUpdate schema should support permissions-only updates."""
        update = UserUpdate(permissions=UserPermissions())
        data = update.model_dump(exclude_unset=True)
        assert "permissions" in data
        assert len(data) == 1
