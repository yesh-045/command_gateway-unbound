from datetime import datetime
from typing import List, Optional

from sqlalchemy import CheckConstraint, Column, Index, JSON, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
	__tablename__ = "users"
	__table_args__ = (
		CheckConstraint("role in ('admin','member')", name="users_role_check"),
	)

	id: Optional[int] = Field(default=None, primary_key=True)
	username: str = Field(index=True, unique=True, max_length=64)
	api_key: str = Field(index=True, unique=True, max_length=128)
	role: str = Field(default="member")
	seniority: str = Field(default="standard", max_length=32)
	credits: int = Field(default=100)
	created_at: datetime = Field(default_factory=datetime.utcnow)

	commands: List["Command"] = Relationship(back_populates="user")
	rules: List["Rule"] = Relationship(back_populates="creator")


class Rule(SQLModel, table=True):
	__tablename__ = "rules"
	__table_args__ = (
		CheckConstraint(
			"action in ('AUTO_ACCEPT','AUTO_REJECT','REQUIRE_APPROVAL')",
			name="rules_action_check",
		),
	)

	id: Optional[int] = Field(default=None, primary_key=True)
	pattern: str
	action: str = Field(default="AUTO_REJECT")
	priority: int = Field(default=100, index=True)
	created_by: int = Field(foreign_key="users.id")
	created_at: datetime = Field(default_factory=datetime.utcnow)
	approval_threshold: int = Field(default=1)
	user_thresholds: dict[str, int] = Field(
		default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict)
	)

	creator: Optional["User"] = Relationship(back_populates="rules")
	commands: List["Command"] = Relationship(back_populates="rule")


class Command(SQLModel, table=True):
	__tablename__ = "commands"
	__table_args__ = (
		CheckConstraint(
			"action_taken in ('PENDING','EXECUTED','REJECTED','FAILED','WAITING_APPROVAL')",
			name="commands_action_check",
		),
	)

	id: Optional[int] = Field(default=None, primary_key=True)
	user_id: int = Field(foreign_key="users.id")
	command_text: str
	matched_rule_id: Optional[int] = Field(default=None, foreign_key="rules.id")
	action_taken: str
	cost: int = Field(default=0)
	required_approvals: int = Field(default=0)
	result: Optional[str] = None
	created_at: datetime = Field(default_factory=datetime.utcnow)
	executed_at: Optional[datetime] = None
	tx_id: Optional[str] = Field(default=None, index=True)

	user: Optional["User"] = Relationship(back_populates="commands")
	rule: Optional["Rule"] = Relationship(back_populates="commands")
	approvals: List["Approval"] = Relationship(back_populates="command")


class Approval(SQLModel, table=True):
	__tablename__ = "approvals"
	__table_args__ = (
		UniqueConstraint("command_id", "approver_id", name="uq_approval_per_admin"),
	)

	id: Optional[int] = Field(default=None, primary_key=True)
	command_id: int = Field(foreign_key="commands.id")
	approver_id: int = Field(foreign_key="users.id")
	decision: Optional[bool] = Field(default=None)
	decided_at: Optional[datetime] = Field(default=None)

	command: Optional["Command"] = Relationship(back_populates="approvals")
	approver: Optional["User"] = Relationship()


# Explicit indexes to keep query plans predictable
Index("idx_users_api_key", User.api_key)
Index("idx_rules_priority", Rule.priority, Rule.id)
Index("idx_commands_user_id", Command.user_id)
Index("idx_commands_rule_id", Command.matched_rule_id)
Index("idx_approvals_command", Approval.command_id)
