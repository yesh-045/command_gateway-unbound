from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import get_settings
from app.core.security import (
	enforce_rate_limit,
	generate_api_key,
	get_current_user,
	require_admin,
	require_admin_or_bootstrap,
)
from app.db.db import get_session
from app.db.models import User
from app.db.schemas import UserCreate, UserRead, UserUpdate, UserWithKey

settings = get_settings()

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(enforce_rate_limit)])
ALLOWED_SENIORITY = {"junior", "standard", "senior", "lead"}


@router.get("/me", response_model=UserRead)
async def read_me(current_user: User = Depends(get_current_user)) -> UserRead:
	return UserRead.model_validate(current_user)


@router.post("", response_model=UserWithKey, status_code=status.HTTP_201_CREATED)
async def create_user(
	payload: UserCreate,
	session: AsyncSession = Depends(get_session),
	_: User | None = Depends(require_admin_or_bootstrap),
) -> UserWithKey:
	api_key = generate_api_key()
	if payload.seniority not in ALLOWED_SENIORITY:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=f"seniority must be one of {sorted(ALLOWED_SENIORITY)}",
		)
	user = User(
		username=payload.username,
		api_key=api_key,
		role=payload.role,
		credits=payload.credits or settings.DEFAULT_CREDITS,
		seniority=payload.seniority,
	)
	session.add(user)
	try:
		await session.commit()
	except IntegrityError as exc:
		await session.rollback()
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="username or api_key already exists",
		) from exc
	await session.refresh(user)
	return UserWithKey.model_validate(user)


@router.get("", response_model=list[UserRead])
async def list_users(
	session: AsyncSession = Depends(get_session),
	_: User = Depends(require_admin),
) -> list[UserRead]:
	result = await session.execute(select(User))
	users = result.scalars().all()
	return [UserRead.model_validate(u) for u in users]


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
	user_id: int,
	payload: UserUpdate,
	session: AsyncSession = Depends(get_session),
	_: User = Depends(require_admin),
) -> UserRead:
	user = await session.get(User, user_id)
	if not user:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

	if payload.role is not None:
		if payload.role not in {"admin", "member"}:
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail="role must be admin or member",
			)
		user.role = payload.role
	if payload.credits is not None:
		user.credits = payload.credits
	if payload.seniority is not None:
		if payload.seniority not in ALLOWED_SENIORITY:
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail=f"seniority must be one of {sorted(ALLOWED_SENIORITY)}",
			)
		user.seniority = payload.seniority

	await session.commit()
	await session.refresh(user)
	return UserRead.model_validate(user)
