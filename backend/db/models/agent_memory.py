# backend/db/models/agent_memory.py

from pydantic import Field
from pydantic import UUID4
from typing import Optional
import datetime
from uuid import uuid4
from backend.db.models.base import CustomModel, CustomModelInsert, CustomModelUpdate


class AgentMemoriesBaseSchema(CustomModel):
    """AgentMemories Base Schema."""

    # Primary Keys
    id: UUID4

    # Columns
    agent_id: UUID4
    content: str
    created_at: Optional[datetime.datetime] = Field(default=None)
    initiative_id: UUID4
    role: str
    timestamp: datetime.datetime
    execution_id: Optional[UUID4] = Field(default=None, description="UUID linking to the orchestrator execution")


class AgentMemoriesInsert(CustomModelInsert):
    """AgentMemories Insert Schema."""

    # Primary Keys (optional for insert)
    id: Optional[UUID4] = Field(default_factory=uuid4)

    # Required fields
    agent_id: UUID4
    content: str
    initiative_id: UUID4
    role: str
    timestamp: datetime.datetime

    # Optional fields
    created_at: Optional[datetime.datetime] = Field(default=None)
    execution_id: Optional[UUID4] = Field(default=None, description="UUID linking to the orchestrator execution")


class AgentMemoriesUpdate(CustomModelUpdate):
    """AgentMemories Update Schema."""

    # All fields optional for update
    id: Optional[UUID4] = Field(default=None)
    agent_id: Optional[UUID4] = Field(default=None)
    content: Optional[str] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    initiative_id: Optional[UUID4] = Field(default=None)
    role: Optional[str] = Field(default=None)
    timestamp: Optional[datetime.datetime] = Field(default=None)
    execution_id: Optional[UUID4] = Field(default=None, description="UUID linking to the orchestrator execution")


class AgentMemories(AgentMemoriesBaseSchema):
    """AgentMemories Schema for Pydantic."""
    pass