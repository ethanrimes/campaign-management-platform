# backend/db/models/execution_log.py

from pydantic import Field, UUID4
from typing import Optional, Dict, Any, List
import datetime
from uuid import uuid4
from backend.db.models.base import CustomModel, CustomModelInsert, CustomModelUpdate


class ExecutionLogsBaseSchema(CustomModel):
    """ExecutionLogs Base Schema."""

    # Primary Keys
    id: UUID4

    # Columns
    execution_id: UUID4 = Field(description="Unique execution identifier")
    initiative_id: UUID4 = Field(description="Initiative this execution belongs to")
    workflow_type: str = Field(description="Type of workflow executed")
    status: Optional[str] = Field(default="running", description="Execution status")
    started_at: Optional[datetime.datetime] = Field(default=None)
    completed_at: Optional[datetime.datetime] = Field(default=None)
    steps_completed: Optional[List[str]] = Field(default_factory=list)
    steps_failed: Optional[List[str]] = Field(default_factory=list)
    error_messages: Optional[Dict[str, Any]] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    updated_at: Optional[datetime.datetime] = Field(default=None)


class ExecutionLogsInsert(CustomModelInsert):
    """ExecutionLogs Insert Schema."""

    # Primary Keys (optional for insert)
    id: Optional[UUID4] = Field(default_factory=uuid4)

    # Required fields
    execution_id: UUID4 = Field(description="Unique execution identifier")
    initiative_id: UUID4 = Field(description="Initiative this execution belongs to")
    workflow_type: str = Field(description="Type of workflow executed")

    # Optional fields
    status: Optional[str] = Field(default="running", description="Execution status")
    started_at: Optional[datetime.datetime] = Field(default=None)
    completed_at: Optional[datetime.datetime] = Field(default=None)
    steps_completed: Optional[List[str]] = Field(default_factory=list)
    steps_failed: Optional[List[str]] = Field(default_factory=list)
    error_messages: Optional[Dict[str, Any]] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    updated_at: Optional[datetime.datetime] = Field(default=None)


class ExecutionLogsUpdate(CustomModelUpdate):
    """ExecutionLogs Update Schema."""

    # All fields optional for update
    id: Optional[UUID4] = Field(default=None)
    execution_id: Optional[UUID4] = Field(default=None)
    initiative_id: Optional[UUID4] = Field(default=None)
    workflow_type: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    started_at: Optional[datetime.datetime] = Field(default=None)
    completed_at: Optional[datetime.datetime] = Field(default=None)
    steps_completed: Optional[List[str]] = Field(default=None)
    steps_failed: Optional[List[str]] = Field(default=None)
    error_messages: Optional[Dict[str, Any]] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    updated_at: Optional[datetime.datetime] = Field(default=None)


class ExecutionLogs(ExecutionLogsBaseSchema):
    """ExecutionLogs Schema for Pydantic."""
    pass