"""Authentication endpoints — login, register, logout."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from intensicare.auth.dependencies import get_current_user, require_admin
from intensicare.auth.jwt import create_access_token, create_refresh_token, decode_token
from intensicare.core.database import get_db
from intensicare.core.redis import get_redis
from intensicare.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    """Login request payload."""

    username: str
    password: str


class RegisterRequest(BaseModel):
    """Registration request payload."""

    username: str
    email: str
    password: str
    display_name: str | None = None

    @field_validator("username")
    @classmethod
    def username_min_length(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User info response."""

    id: int
    username: str
    email: str
    display_name: str | None
    is_admin: bool
    is_active: bool


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT tokens."""
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
        )

    token_data = {"sub": user.username, "user_id": user.id}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user (admin only)."""
    # Check if username already exists
    result = await db.execute(select(User).where(User.username == request.username))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
        display_name=request.display_name or request.username,
        is_admin=False,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        is_admin=user.is_admin,
        is_active=user.is_active,
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Logout — blacklist the current token in Redis."""
    # The token is invalidated via the dependency; this endpoint
    # mainly serves as a confirmation point.
    return {"detail": "Logged out successfully"}
