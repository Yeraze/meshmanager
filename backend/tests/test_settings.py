"""Tests for application settings."""

from app.config import Settings


class TestSettingsDefaults:
    """Test default values for new settings."""

    def test_oidc_scopes_default(self):
        """OIDC scopes should default to openid email profile."""
        s = Settings(database_url="sqlite+aiosqlite:///test.db")
        assert s.oidc_scopes == "openid email profile"

    def test_oidc_auto_create_users_default(self):
        """OIDC auto-create users should default to True."""
        s = Settings(database_url="sqlite+aiosqlite:///test.db")
        assert s.oidc_auto_create_users is True

    def test_disable_local_auth_default(self):
        """DISABLE_LOCAL_AUTH should default to False."""
        s = Settings(database_url="sqlite+aiosqlite:///test.db")
        assert s.disable_local_auth is False

    def test_disable_local_auth_can_be_enabled(self):
        """DISABLE_LOCAL_AUTH can be set to True."""
        s = Settings(
            database_url="sqlite+aiosqlite:///test.db",
            disable_local_auth=True,
        )
        assert s.disable_local_auth is True

    def test_oidc_scopes_customizable(self):
        """OIDC scopes can be customized."""
        s = Settings(
            database_url="sqlite+aiosqlite:///test.db",
            oidc_scopes="openid email",
        )
        assert s.oidc_scopes == "openid email"

    def test_oidc_scopes_rejects_comma_separated(self):
        """OIDC scopes should reject comma-separated values."""
        import pytest

        with pytest.raises(Exception, match="space-separated"):
            Settings(
                database_url="sqlite+aiosqlite:///test.db",
                oidc_scopes="openid,email,profile",
            )

    def test_oidc_scopes_strips_whitespace(self):
        """OIDC scopes should be trimmed."""
        s = Settings(
            database_url="sqlite+aiosqlite:///test.db",
            oidc_scopes="  openid email profile  ",
        )
        assert s.oidc_scopes == "openid email profile"
