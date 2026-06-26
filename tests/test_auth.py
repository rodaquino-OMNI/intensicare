"""Tests for JWT authentication endpoints."""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from intensicare.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_admin_user(db: AsyncSession) -> User:
    """Helper to create an admin user for tests."""
    user = User(
        username="admin",
        email="admin@intensicare.io",
        hashed_password=pwd_context.hash("admin123"),
        display_name="Admin User",
        is_admin=True,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def create_regular_user(db: AsyncSession) -> User:
    """Helper to create a regular user for tests."""
    user = User(
        username="nurse1",
        email="nurse1@intensicare.io",
        hashed_password=pwd_context.hash("nurse1234"),
        display_name="Nurse One",
        is_admin=False,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


class TestAuthLogin:
    """Tests for POST /auth/login."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, db_session: AsyncSession):
        """Should return tokens on valid credentials."""
        await create_admin_user(db_session)

        response = await client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123",
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient, db_session: AsyncSession):
        """Should return 401 on invalid password."""
        await create_admin_user(db_session)

        response = await client.post("/auth/login", json={
            "username": "admin",
            "password": "wrongpassword",
        })

        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Should return 401 for non-existent user."""
        response = await client.post("/auth/login", json={
            "username": "ghost",
            "password": "whatever123",
        })

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client: AsyncClient, db_session: AsyncSession):
        """Should return 401 for inactive user."""
        user = await create_admin_user(db_session)
        user.is_active = False
        await db_session.flush()

        response = await client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123",
        })

        assert response.status_code == 401


class TestAuthRegister:
    """Tests for POST /auth/register (admin only)."""

    @pytest.mark.asyncio
    async def test_register_requires_admin(self, client: AsyncClient, db_session: AsyncSession):
        """Should return 401 when no token provided."""
        response = await client.post("/auth/register", json={
            "username": "newuser",
            "email": "new@test.com",
            "password": "newuser1234",
        })

        assert response.status_code == 401  # Unauthorized (no token)

    @pytest.mark.asyncio
    async def test_register_as_admin_success(self, client: AsyncClient, db_session: AsyncSession):
        """Admin should be able to register new users."""
        admin = await create_admin_user(db_session)

        # Login as admin
        login_resp = await client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123",
        })
        token = login_resp.json()["access_token"]

        # Register new user
        response = await client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "new@test.com",
                "password": "newuser1234",
                "display_name": "New User",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@test.com"
        assert data["is_admin"] is False

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient, db_session: AsyncSession):
        """Should return 409 for duplicate username."""
        admin = await create_admin_user(db_session)

        login_resp = await client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123",
        })
        token = login_resp.json()["access_token"]

        # First registration
        await client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "first@test.com",
                "password": "newuser1234",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # Duplicate
        response = await client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "second@test.com",
                "password": "another1234",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409


class TestAuthProtected:
    """Tests that protected endpoints require auth."""

    @pytest.mark.asyncio
    async def test_acknowledge_requires_auth(self, client: AsyncClient):
        """Should return 401 when acknowledging without token."""
        response = await client.post("/api/v1/alerts/1/acknowledge")

        assert response.status_code == 401


class TestAuthLogout:
    """Tests for POST /auth/logout."""

    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient, db_session: AsyncSession):
        """Should return success on logout."""
        await create_admin_user(db_session)

        login_resp = await client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123",
        })
        token = login_resp.json()["access_token"]

        response = await client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
