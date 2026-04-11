import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.dependencies import get_current_user
from app.models.db import User
from app.models.schemas import Token, UserCreate, UserOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> UserOut:
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        name=payload.name,
        password_hash=get_password_hash(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("Registered user %s", user.id)
    return UserOut.model_validate(user)


@router.post("/login", response_model=Token)
async def login(payload: UserCreate, response: Response, db: AsyncSession = Depends(get_db)) -> Token:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    settings = get_settings()
    token = create_access_token(str(user.id))
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        # cross-domain (Vercel → Railway) requires samesite=none + secure=True
        samesite="none" if settings.is_production else "lax",
        secure=settings.is_production,
        max_age=10080 * 60,
    )
    logger.info("User %s logged in", user.id)
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie("access_token")
    return {"detail": "Logged out"}
