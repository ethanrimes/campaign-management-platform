# backend/api/routes/campaigns.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional
from backend.db.models.campaign import Campaign
from backend.db.supabase_client import DatabaseClient, get_database_client
from backend.api.middleware.initiative import get_tenant_id
from agents.orchestrator.agent import OrchestratorAgent, AgentConfig

router = APIRouter()

@router.get("/", response_model=List[Campaign])
async def list_campaigns(
    initiative_id: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    db: DatabaseClient = Depends(lambda: get_database_client(tenant_id))
):
    """List campaigns"""
    filters = {}
    if initiative_id:
        filters["initiative_id"] = initiative_id
    
    campaigns = await db.select("campaigns", filters=filters)
    return campaigns


@router.post("/orchestrate")
async def orchestrate_campaigns(
    initiative_id: str,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_tenant_id)
):
    """Trigger campaign orchestration"""
    
    # Create orchestrator agent
    config = AgentConfig(
        name="Campaign Orchestrator",
        description="Plans and manages campaigns",
        initiative_id=initiative_id
    )
    
    agent = OrchestratorAgent(config)
    
    # Run orchestration in background
    background_tasks.add_task(
        run_orchestration,
        agent,
        {"initiative_id": initiative_id}
    )
    
    return {
        "status": "orchestration_started",
        "initiative_id": initiative_id
    }

async def run_orchestration(agent: OrchestratorAgent, input_data: dict):
    """Run orchestration task"""
    result = await agent.execute(input_data)
    
    if result.success:
        # Save the hierarchy
        await agent.save_hierarchy(result.data)