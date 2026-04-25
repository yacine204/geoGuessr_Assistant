from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from datetime import timedelta
from models.user import User, UserCreate, UserRead, RegisterResponse
from database.db import get_async_session

from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

from core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags = ["auth"])


async def ensure_avatar_url(user: User, session: AsyncSession | None = None) -> None:
    if not user.avatar_url:
        user.avatar_url = user.generate_avatar_url()
        if session is not None:
            session.add(user)
            await session.commit()
            await session.refresh(user)

@router.post(
    "/register",
    response_model=RegisterResponse,
    summary="Register a new user",
    description="Creates a new user account and returns an access token.",
)
async def register(user_data: UserCreate, session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Email already in use"
        )

    if user_data.pseudo:
        pseudo_result = await session.execute(select(User).where(User.pseudo == user_data.pseudo))
        existing_pseudo = pseudo_result.scalars().first()
        if existing_pseudo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pseudo already in use"
            )

    hashed_password = hash_password(user_data.password)
    new_user = User(
        pseudo=user_data.pseudo,
        email = user_data.email,
        hashed_password= hashed_password
    )
    new_user.avatar_url = new_user.generate_avatar_url()

    session.add(new_user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or pseudo already in use"
        )
    await session.refresh(new_user)

    access_token_expires = timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    access_token = create_access_token(
        data = {"sub": new_user.email},
        expires_delta=access_token_expires
    )

    return {"user": new_user, "access_token": access_token, "token_type": "bearer"}


@router.post(
    "/login",
    response_model=RegisterResponse,
    summary="Authenticate user",
    description="Validates user credentials and returns an access token.",
)
async def login(user_data: UserCreate, session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(User).where(User.email == user_data.email))
    user = result.scalars().first()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    await ensure_avatar_url(user, session)
    
    access_token_expires = timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    access_token = create_access_token(
        data = {"sub": user.email},
        expires_delta=access_token_expires
    )

    return {"user": user, "access_token": access_token, "token_type": "bearer"}

@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current user profile",
    description="Returns the authenticated user based on Bearer token.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    await ensure_avatar_url(current_user, session)
    return current_user