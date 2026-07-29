"""认证路由 —— 注册与登录。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.config.settings import settings
from packages.core.models.user import User
from ..dependencies.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from ..dependencies.database import get_db

router = APIRouter(tags=["auth"])


# ─── Schemas ───


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    display_name: str | None
    is_active: bool

    model_config = {"from_attributes": True}


# ─── Routes ───


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """注册新用户。"""
    # 检查邮箱重复
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    # 检查用户名重复
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    user = User(
        email=req.email,
        username=req.username,
        hashed_password=hash_password(req.password),
        display_name=req.username,
    )
    db.add(user)
    await db.flush()

    token = create_access_token(user_id=str(user.id))
    return AuthResponse(
        access_token=token,
        expires_in=settings.jwt_expiration_hours * 3600,
        user={
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
        },
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """用户登录。"""
    result = await db.execute(
        select(User).where(User.username == req.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    token = create_access_token(user_id=str(user.id))
    return AuthResponse(
        access_token=token,
        expires_in=settings.jwt_expiration_hours * 3600,
        user={
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
        },
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前用户信息。"""
    return current_user
