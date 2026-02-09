"""Tests for OIDC authentication."""

import pytest

from app.auth.oidc import process_oidc_callback


@pytest.mark.integration
class TestOidcAutoCreate:
    """Tests for OIDC auto-create users setting."""

    async def test_oidc_auto_create_disabled_rejects_new_user(self):
        """process_oidc_callback should raise when auto-create is disabled."""
        from app.auth.oidc import settings

        original = settings.oidc_auto_create_users
        settings.oidc_auto_create_users = False
        try:
            token = {
                "userinfo": {
                    "sub": "new-oidc-user-12345",
                    "email": "newuser@example.com",
                    "name": "New User",
                }
            }
            with pytest.raises(ValueError, match="Auto-creation of OIDC users is disabled"):
                await process_oidc_callback(token)
        finally:
            settings.oidc_auto_create_users = original
