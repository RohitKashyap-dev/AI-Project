from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.security import create_access_token, get_current_claims, get_password_hash, verify_password
from backend.db.session import get_db
from backend.models.user import User
from backend.schemas.auth import TokenRequest, TokenResponse, UserCreate

router = APIRouter(tags=["auth"])


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(payload: TokenRequest, db: AsyncSession = Depends(get_db)):
    if payload.username == settings.ADMIN_USERNAME and payload.password == settings.ADMIN_PASSWORD:
        existing_admin = await db.scalar(select(User).where(User.username == settings.ADMIN_USERNAME))
        if not existing_admin:
            admin_user = User(
                username=settings.ADMIN_USERNAME,
                email=None,
                password_hash=get_password_hash(settings.ADMIN_PASSWORD),
                role="admin",
            )
            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)

        token = create_access_token(subject=settings.ADMIN_USERNAME, role="admin")
        return TokenResponse(access_token=token)

    user = await db.scalar(select(User).where(User.username == payload.username))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    token = create_access_token(subject=user.username, role=user.role)
    return TokenResponse(access_token=token)


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.username == payload.username))
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "username": user.username, "role": user.role}


@router.get("/me")
async def me(claims: dict = Depends(get_current_claims)):
    return {"username": claims.get("sub"), "role": claims.get("role")}
