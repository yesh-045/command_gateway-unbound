from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import ConfigDict, Field
from sqlmodel import Field, SQLModel


class ORMModel(SQLModel):
    model_config = ConfigDict(from_attributes=True)


class UserBase(ORMModel):
    username: str
    role: str = "member"
    credits: int = 100
    seniority: str = "standard"


class UserCreate(UserBase):
    pass


class UserUpdate(ORMModel):
    role: Optional[str] = None
    credits: Optional[int] = None


class UserRead(UserBase):
    id: int
    created_at: datetime


class UserWithKey(UserRead):
    api_key: str


class RuleBase(ORMModel):
    pattern: str
    action: str
    priority: int = 100
    approval_threshold: int = 1
    user_thresholds: dict[str, int] = Field(default_factory=dict)


class RuleCreate(RuleBase):
    pass


class RuleUpdate(ORMModel):
    pattern: Optional[str] = None
    action: Optional[str] = None
    priority: Optional[int] = None


class RuleRead(RuleBase):
    id: int
    created_by: int
    created_at: datetime


class CommandCreate(ORMModel):
    command_text: str


class CommandRead(ORMModel):
    id: int
    user_id: int
    command_text: str
    matched_rule_id: Optional[int]
    action_taken: str
    cost: int
    required_approvals: int
    result: Optional[str]
    created_at: datetime
    executed_at: Optional[datetime]
    tx_id: Optional[str]


class CommandListItem(ORMModel):
    id: int
    command_text: str
    action_taken: str
    created_at: datetime
    matched_rule_id: Optional[int]
    cost: int


class ApprovalDecision(ORMModel):
    approved: bool


class RuleTestRequest(ORMModel):
    pattern: str
    command: str


class RuleTestResponse(ORMModel):
    matched: bool
    groups: list[str]


class AuditFilters(ORMModel):
    user_id: Optional[int] = None
    rule_id: Optional[int] = None
    action_taken: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
