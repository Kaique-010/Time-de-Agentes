from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Intent(str, Enum):
    CREATE_MODULE = "create_module"
    PATCH_EXISTING = "patch_existing"
    INSPECT = "inspect"
    UNKNOWN = "unknown"


class PlanStep(BaseModel):
    id: str
    description: str
    completed: bool = False


class TaskRequest(BaseModel):
    task: str = Field(min_length=3)
    project_context: dict[str, Any] = Field(default_factory=dict)


class ToolContext(BaseModel):
    github: dict[str, Any] = Field(default_factory=dict)
    postgres: dict[str, Any] = Field(default_factory=dict)
    rag: dict[str, Any] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    intent: Intent
    plan: list[PlanStep]
    delegated_agent: str
    context: ToolContext
    output: dict[str, Any]
    valid: bool
    validation_errors: list[str] = Field(default_factory=list)
