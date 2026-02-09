"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestAuthStatus:
    """Tests for /auth/status endpoint."""

    async def test_auth_status_returns_200(self, client: AsyncClient):
        """Auth status should return 200 status code."""
        response = await client.get("/auth/status")
        assert response.status_code == 200

    async def test_auth_status_unauthenticated(self, client: AsyncClient):
        """Auth status should show unauthenticated when no session."""
        response = await client.get("/auth/status")
        data = response.json()

        assert data["authenticated"] is False
        assert data["user"] is None

    async def test_auth_status_response_structure(self, client: AsyncClient):
        """Auth status should have expected response structure."""
        response = await client.get("/auth/status")
        data = response.json()

        assert "authenticated" in data
        assert "user" in data
        assert "oidc_enabled" in data
        assert "setup_required" in data


@pytest.mark.integration
class TestAuthRegister:
    """Tests for /auth/register endpoint."""

    async def test_register_first_user_success(self, client: AsyncClient):
        """First user registration should succeed and become admin."""
        response = await client.post(
            "/auth/register",
            json={
                "username": "admin",
                "password": "testpassword123",
                "password_confirm": "testpassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "admin"

    async def test_register_password_mismatch(self, client: AsyncClient):
        """Registration should fail when passwords don't match."""
        response = await client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "password": "password123",
                "password_confirm": "differentpassword",
            },
        )
        assert response.status_code == 400

    async def test_register_missing_fields(self, client: AsyncClient):
        """Registration should fail with missing fields."""
        response = await client.post(
            "/auth/register",
            json={"username": "testuser"},
        )
        assert response.status_code == 422  # Validation error

    async def test_register_empty_username(self, client: AsyncClient):
        """Registration should fail with empty username."""
        response = await client.post(
            "/auth/register",
            json={
                "username": "",
                "password": "testpassword123",
                "password_confirm": "testpassword123",
            },
        )
        assert response.status_code in [400, 422]

    async def test_register_short_password(self, client: AsyncClient):
        """Registration should fail with short password."""
        response = await client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "password": "short",
                "password_confirm": "short",
            },
        )
        assert response.status_code == 400


@pytest.mark.integration
class TestAuthLogin:
    """Tests for /auth/login endpoint."""

    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Login should fail with invalid credentials."""
        response = await client.post(
            "/auth/login",
            json={
                "username": "nonexistent",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    async def test_login_missing_fields(self, client: AsyncClient):
        """Login should fail with missing fields."""
        response = await client.post(
            "/auth/login",
            json={"username": "testuser"},
        )
        assert response.status_code == 422  # Validation error

    async def test_login_after_register(self, client: AsyncClient):
        """Login should succeed after registration."""
        # First register
        await client.post(
            "/auth/register",
            json={
                "username": "logintest",
                "password": "testpassword123",
                "password_confirm": "testpassword123",
            },
        )

        # Then login
        response = await client.post(
            "/auth/login",
            json={
                "username": "logintest",
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["username"] == "logintest"


@pytest.mark.integration
class TestAuthLogout:
    """Tests for /auth/logout endpoint."""

    async def test_logout_returns_200(self, client: AsyncClient):
        """Logout should return 200 even when not logged in."""
        response = await client.post("/auth/logout")
        assert response.status_code == 200

    async def test_logout_clears_session(self, client: AsyncClient):
        """Logout should clear the session."""
        # Register and login first
        await client.post(
            "/auth/register",
            json={
                "username": "logouttest",
                "password": "testpassword123",
                "password_confirm": "testpassword123",
            },
        )
        await client.post(
            "/auth/login",
            json={
                "username": "logouttest",
                "password": "testpassword123",
            },
        )

        # Verify logged in
        status_response = await client.get("/auth/status")
        assert status_response.json()["authenticated"] is True

        # Logout
        await client.post("/auth/logout")

        # Verify logged out
        status_response = await client.get("/auth/status")
        assert status_response.json()["authenticated"] is False
