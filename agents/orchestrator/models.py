from pydantic import BaseModel, Field
from typing import List, Dict, Any

class OrchestratorOutput(BaseModel):
    """Orchestrator execution output"""
    workflow_id: str = Field(description="Unique workflow ID")
    execution_id: str = Field(description="Execution ID")
    workflow_type: str = Field(description="Type of workflow executed")
    success: bool = Field(description="Whether workflow succeeded")
    steps_completed: List[str] = Field(default_factory=list)
    steps_failed: List[str] = Field(default_factory=list)
    guardrail_violations: List[Dict[str, Any]] = Field(default_factory=list)
    results: Dict[str, Any] = Field(description="Results from each step")
    metadata: Dict[str, Any] = Field(default_factory=dict)