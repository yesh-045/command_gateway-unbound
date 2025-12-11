from __future__ import annotations

import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import get_settings
from app.core.notifications import notify_approval_request
from app.core.rules import get_ordered_rules, match_rule
from app.core.security import enforce_rate_limit, get_current_user, require_admin
from app.db.db import get_session
from app.db.models import Approval, Command, Rule, User
from app.db.schemas import (
	ApprovalDecision,
	AuditFilters,
	CommandCreate,
	CommandListItem,
	CommandRead,
)
from app.worker import schedule_command_execution

settings = get_settings()

router = APIRouter(prefix="/commands", tags=["commands"], dependencies=[Depends(enforce_rate_limit)])


async def _load_user(session: AsyncSession, user_id: int) -> User:
	user = await session.get(User, user_id)
	if not user:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
	return user


def _determine_required_approvals(rule: Rule | None, user: User) -> int:
	baseline = settings.DEFAULT_APPROVAL_THRESHOLD
	if rule:
		baseline = rule.approval_threshold or baseline
		if rule.user_thresholds and user.seniority in rule.user_thresholds:
			baseline = rule.user_thresholds[user.seniority]
	return max(1, baseline)


async def _count_approved(session: AsyncSession, command_id: int) -> int:
	result = await session.execute(
		select(Approval).where(
			Approval.command_id == command_id,
			Approval.decision.is_(True),
		)
	)
	return len(result.scalars().all())


@router.post("", response_model=CommandRead, status_code=status.HTTP_201_CREATED)
async def create_command(
	payload: CommandCreate,
	session: AsyncSession = Depends(get_session),
	current_user: User = Depends(get_current_user),
) -> CommandRead:
	rules = await get_ordered_rules(session)
	matched_rule = match_rule(payload.command_text, rules)
	chosen_action = matched_rule.action if matched_rule else settings.DEFAULT_RULE_ACTION
	cost = settings.DEFAULT_COMMAND_COST if chosen_action == "AUTO_ACCEPT" else 0

	user = await _load_user(session, current_user.id)

	command: Optional[Command] = None
	insufficient_credits = False

	if user.credits <= 0 and chosen_action == "AUTO_ACCEPT":
		command = Command(
			user_id=user.id,
			command_text=payload.command_text,
			matched_rule_id=matched_rule.id if matched_rule else None,
			action_taken="REJECTED",
			cost=0,
			required_approvals=0,
			tx_id=secrets.token_hex(8),
			result="insufficient credits",
		)
		session.add(command)
		insufficient_credits = True
	elif chosen_action == "AUTO_REJECT":
		command = Command(
			user_id=user.id,
			command_text=payload.command_text,
			matched_rule_id=matched_rule.id if matched_rule else None,
			action_taken="REJECTED",
			cost=0,
			required_approvals=0,
			tx_id=secrets.token_hex(8),
		)
		session.add(command)
	elif chosen_action == "REQUIRE_APPROVAL":
		required = _determine_required_approvals(matched_rule, user)
		command = Command(
			user_id=user.id,
			command_text=payload.command_text,
			matched_rule_id=matched_rule.id if matched_rule else None,
			action_taken="WAITING_APPROVAL",
			cost=0,
			required_approvals=required,
			tx_id=secrets.token_hex(8),
		)
		session.add(command)
	else:
		# AUTO_ACCEPT path
		if user.credits < cost:
			command = Command(
				user_id=user.id,
				command_text=payload.command_text,
				matched_rule_id=matched_rule.id if matched_rule else None,
				action_taken="REJECTED",
				cost=0,
				required_approvals=0,
				tx_id=secrets.token_hex(8),
				result="insufficient credits",
			)
			session.add(command)
			insufficient_credits = True
		else:
			user.credits -= cost
			command = Command(
				user_id=user.id,
				command_text=payload.command_text,
				matched_rule_id=matched_rule.id if matched_rule else None,
				action_taken="PENDING",
				cost=cost,
				required_approvals=0,
				tx_id=secrets.token_hex(8),
			)
			session.add(command)

	await session.commit()
	await session.refresh(command)

	if command.action_taken == "WAITING_APPROVAL":
		admin_rows = await session.execute(select(User).where(User.role == "admin"))
		admins = admin_rows.scalars().all()
		await notify_approval_request(command, matched_rule, user, admins)
	if command.action_taken == "PENDING":
		await schedule_command_execution(command.id, command.command_text)
	if insufficient_credits:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail={"message": "insufficient credits", "command_id": command.id},
		)
	return CommandRead.model_validate(command)


@router.get("", response_model=list[CommandListItem])
async def list_my_commands(
	session: AsyncSession = Depends(get_session),
	current_user: User = Depends(get_current_user),
) -> list[CommandListItem]:
	result = await session.execute(
		select(Command)
		.where(Command.user_id == current_user.id)
		.order_by(Command.created_at.desc())
	)
	commands = result.scalars().all()
	return [CommandListItem.model_validate(cmd) for cmd in commands]


@router.get("/audit", response_model=list[CommandRead])
async def audit_commands(
	user_id: Optional[int] = Query(default=None),
	rule_id: Optional[int] = Query(default=None),
	action_taken: Optional[str] = Query(default=None),
	start: Optional[datetime] = Query(default=None),
	end: Optional[datetime] = Query(default=None),
	session: AsyncSession = Depends(get_session),
	_: User = Depends(require_admin),
) -> list[CommandRead]:
	stmt = select(Command)
	if user_id is not None:
		stmt = stmt.where(Command.user_id == user_id)
	if rule_id is not None:
		stmt = stmt.where(Command.matched_rule_id == rule_id)
	if action_taken is not None:
		stmt = stmt.where(Command.action_taken == action_taken)
	if start is not None:
		stmt = stmt.where(Command.created_at >= start)
	if end is not None:
		stmt = stmt.where(Command.created_at <= end)

	stmt = stmt.order_by(Command.created_at.desc())
	result = await session.execute(stmt)
	commands = result.scalars().all()
	return [CommandRead.model_validate(cmd) for cmd in commands]


@router.get("/{command_id}", response_model=CommandRead)
async def get_command(
	command_id: int,
	session: AsyncSession = Depends(get_session),
	current_user: User = Depends(get_current_user),
) -> CommandRead:
	command = await session.get(Command, command_id)
	if not command:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="command not found")
	if current_user.role != "admin" and command.user_id != current_user.id:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
	return CommandRead.model_validate(command)


@router.post("/{command_id}/approve", response_model=CommandRead)
async def approve_command(
	command_id: int,
	payload: ApprovalDecision,
	session: AsyncSession = Depends(get_session),
	admin: User = Depends(require_admin),
) -> CommandRead:
	command = await session.get(Command, command_id)
	if not command:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="command not found")
	if command.action_taken != "WAITING_APPROVAL":
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="command is not awaiting approval",
		)
	existing = await session.execute(
		select(Approval).where(
			Approval.command_id == command.id,
			Approval.approver_id == admin.id,
		)
	)
	if existing.scalars().first():
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="already voted")

	user = await _load_user(session, command.user_id)

	approval = Approval(
		command_id=command.id,
		approver_id=admin.id,
		decision=payload.approved,
		decided_at=datetime.utcnow(),
	)
	session.add(approval)
	await session.flush()

	if not payload.approved:
		command.action_taken = "REJECTED"
		command.result = "rejected by admin"
		await session.commit()
		await session.refresh(command)
		return CommandRead.model_validate(command)

	approved_total = await _count_approved(session, command.id)
	required = command.required_approvals or _determine_required_approvals(command.rule, user)

	if approved_total < required:
		await session.commit()
		await session.refresh(command)
		return CommandRead.model_validate(command)

	cost = settings.DEFAULT_COMMAND_COST
	if user.credits < cost:
		command.action_taken = "REJECTED"
		command.result = "insufficient credits"
		await session.commit()
		await session.refresh(command)
		return CommandRead.model_validate(command)

	user.credits -= cost
	command.cost = cost
	command.action_taken = "PENDING"
	await session.commit()
	await session.refresh(command)
	await schedule_command_execution(command.id, command.command_text)
	return CommandRead.model_validate(command)
