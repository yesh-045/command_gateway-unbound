from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.rules import get_ordered_rules, validate_regex
from app.core.security import enforce_rate_limit, get_current_user, require_admin
from app.db.db import get_session
from app.db.models import Rule, User
from app.db.schemas import RuleCreate, RuleRead, RuleTestRequest, RuleTestResponse, RuleUpdate

router = APIRouter(prefix="/rules", tags=["rules"], dependencies=[Depends(enforce_rate_limit)])


def _ensure_action_valid(action: str) -> None:
	allowed = {"AUTO_ACCEPT", "AUTO_REJECT", "REQUIRE_APPROVAL"}
	if action not in allowed:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=f"action must be one of {allowed}",
		)


@router.post("", response_model=RuleRead, status_code=status.HTTP_201_CREATED)
async def create_rule(
	payload: RuleCreate,
	session: AsyncSession = Depends(get_session),
	admin: User = Depends(require_admin),
) -> RuleRead:
	_ensure_action_valid(payload.action)
	validate_regex(payload.pattern)
	rule = Rule(
		pattern=payload.pattern,
		action=payload.action,
		priority=payload.priority,
		approval_threshold=payload.approval_threshold,
		user_thresholds=payload.user_thresholds or {},
		created_by=admin.id,
	)
	session.add(rule)
	await session.commit()
	await session.refresh(rule)
	return RuleRead.model_validate(rule)


@router.get("", response_model=list[RuleRead])
async def list_rules(
	session: AsyncSession = Depends(get_session),
	_: User = Depends(require_admin),
) -> list[RuleRead]:
	rules = await get_ordered_rules(session)
	return [RuleRead.model_validate(rule) for rule in rules]


@router.patch("/{rule_id}", response_model=RuleRead)
async def update_rule(
	rule_id: int,
	payload: RuleUpdate,
	session: AsyncSession = Depends(get_session),
	_: User = Depends(require_admin),
) -> RuleRead:
	rule = await session.get(Rule, rule_id)
	if not rule:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="rule not found")

	if payload.action is not None:
		_ensure_action_valid(payload.action)
		rule.action = payload.action
	if payload.pattern is not None:
		validate_regex(payload.pattern)
		rule.pattern = payload.pattern
	if payload.priority is not None:
		rule.priority = payload.priority
	if payload.approval_threshold is not None:
		rule.approval_threshold = payload.approval_threshold
	if payload.user_thresholds is not None:
		rule.user_thresholds = payload.user_thresholds

	await session.commit()
	await session.refresh(rule)
	return RuleRead.model_validate(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_rule(
	rule_id: int,
	session: AsyncSession = Depends(get_session),
	_: User = Depends(require_admin),
) -> Response:
	rule = await session.get(Rule, rule_id)
	if not rule:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="rule not found")
	await session.delete(rule)
	await session.commit()
	return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/test", response_model=RuleTestResponse)
async def test_rule(
	payload: RuleTestRequest,
	_: User = Depends(require_admin),
) -> RuleTestResponse:
	compiled = validate_regex(payload.pattern)
	match = compiled.search(payload.command)
	groups = list(match.groups()) if match else []
	return RuleTestResponse(matched=bool(match), groups=groups)
