"""
Pi Orchestrator Pydantic models.

All request/response models for the API. No database models here —
those are managed by the database.py facade.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════


class PiAgentStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    IDLE = "idle"
    BUSY = "busy"
    STOPPED = "stopped"
    ERROR = "error"


class SessionStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    ERROR = "error"


class ExecutionStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


# ═══════════════════════════════════════════════════════════════════
# Agent Models
# ═══════════════════════════════════════════════════════════════════


class PiAgentConfig(BaseModel):
    """Configuration for creating a managed pi agent."""
    name: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    persona: Optional[str] = None         # Reference to .pi/agents/<persona>.md
    model: str = ''  # Empty string = use pi default model
    tools: list[str] = Field(default_factory=lambda: ["read", "bash", "web_search"])
    skills: list[str] = Field(default_factory=list)
    extensions: list[str] = Field(default_factory=list)
    system_prompt: Optional[str] = None
    git_repo: Optional[str] = None
    schedule: Optional[str] = None        # Cron expression


class PiAgentSummary(BaseModel):
    """Lightweight agent info for the dashboard grid."""
    id: str
    name: str
    persona: Optional[str] = None
    status: PiAgentStatus
    model: str
    tokens_used: int = 0
    session_count: int = 0
    last_active: Optional[datetime] = None
    created_at: datetime


class PiAgentDetail(PiAgentSummary):
    """Full agent detail including config."""
    tools: list[str]
    skills: list[str]
    extensions: list[str]
    system_prompt: Optional[str] = None
    git_repo: Optional[str] = None
    schedule: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
# Session Models
# ═══════════════════════════════════════════════════════════════════


class PiSessionSummary(BaseModel):
    """A single session in the history."""
    id: str
    agent_id: str
    agent_name: str
    session_file: str
    status: SessionStatus
    turns: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    model: str
    started_at: datetime
    ended_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════
# Chat Models
# ═══════════════════════════════════════════════════════════════════


class ChatRequest(BaseModel):
    """Send a message to an agent."""
    message: str = Field(..., min_length=1)
    model: Optional[str] = None
    timeout_seconds: Optional[int] = None


class ChatChunk(BaseModel):
    """A single chunk of a streaming response."""
    type: str  # "text_delta", "tool_call", "tool_result", "turn_end", "error"
    content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    tool_result: Optional[str] = None
    tokens_used: Optional[int] = None


# ═══════════════════════════════════════════════════════════════════
# Schedule Models
# ═══════════════════════════════════════════════════════════════════


class ScheduleConfig(BaseModel):
    """Create or update a schedule."""
    agent_id: str
    cron_expression: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    enabled: bool = True
    model: Optional[str] = None
    max_turns: Optional[int] = None
    timeout_seconds: Optional[int] = None


class ScheduleSummary(BaseModel):
    """Schedule info for the list view."""
    id: str
    agent_id: str
    agent_name: Optional[str] = None
    cron_expression: str
    message: str
    enabled: bool
    model: Optional[str] = None
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime


class ScheduleExecutionSummary(BaseModel):
    """A single execution of a schedule."""
    id: str
    schedule_id: str
    session_id: Optional[str] = None
    status: ExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
# Activity Models
# ═══════════════════════════════════════════════════════════════════


class ActivityEntry(BaseModel):
    """A single activity event."""
    id: int
    agent_id: str
    agent_name: Optional[str] = None
    event_type: str
    event_data: Optional[dict] = None
    created_at: datetime


# ═══════════════════════════════════════════════════════════════════
# Skills & Extensions
# ═══════════════════════════════════════════════════════════════════


class SkillSummary(BaseModel):
    """A pi skill with its frontmatter metadata."""
    name: str
    description: str
    location: str


class SkillParameter(BaseModel):
    """A parameter for a slice play skill."""
    type: str = "string"
    required: bool = False
    default: Any = None
    description: str = ""


class SkillSchema(BaseModel):
    """Full skill schema including typed inputs/outputs."""
    name: str
    description: str = ""
    location: str = ""
    inputs: dict[str, SkillParameter] = Field(default_factory=dict)
    outputs: dict[str, SkillParameter] = Field(default_factory=dict)
    triggers: list[str] = Field(default_factory=list)


class ExtensionSummary(BaseModel):
    """A pi extension entry."""
    name: str
    path: str
    source: str  # "global", "project", or package name


# ═══════════════════════════════════════════════════════════════════
# Template / Persona Models
# ═══════════════════════════════════════════════════════════════════


class PersonaSummary(BaseModel):
    """An agent persona from .pi/agents/<name>.md."""
    name: str
    description: Optional[str] = None
    tools: list[str] = Field(default_factory=list)
    model: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    extensions: list[str] = Field(default_factory=list)
    schedule: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
# MCP Key Models
# ═══════════════════════════════════════════════════════════════════


class McpKeyCreate(BaseModel):
    """Create a new MCP API key."""
    name: str = Field(..., min_length=1)


class McpKeySummary(BaseModel):
    """MCP API key info (no secret)."""
    id: str
    name: str
    created_at: datetime
    last_used_at: Optional[datetime] = None


class McpKeyCreated(BaseModel):
    """Returned once when a key is created — secret is NOT stored plaintext."""
    id: str
    name: str
    key: str  # Only returned once
    created_at: datetime


# ═══════════════════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════════════════


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    agent_count: int = 0
    active_session_count: int = 0
