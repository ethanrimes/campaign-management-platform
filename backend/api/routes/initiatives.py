# backend/api/routes/initiatives.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from backend.db.models.initiative import Initiative
from backend.db.supabase_client import DatabaseClient, get_database_client
from backend.api.middleware.auth import verify_token
from backend.api.middleware.initiative import get_tenant_id

router = APIRouter()

@router.get("/", response_model=List[Initiative])
async def list_initiatives(
    tenant_id: str = Depends(get_tenant_id),
    db: DatabaseClient = Depends(lambda: get_database_client(tenant_id))
):
    """List all initiatives for a tenant"""
    initiatives = await db.select("initiatives")
    return initiatives

@router.get("/{initiative_id}", response_model=Initiative)
async def get_initiative(
    initiative_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: DatabaseClient = Depends(lambda: get_database_client(tenant_id))
):
    """Get a specific initiative"""
    initiatives = await db.select(
        "initiatives",
        filters={"id": initiative_id}
    )
    
    if not initiatives:
        raise HTTPException(status_code=404, detail="Initiative not found")
    
    return initiatives[0]

@router.post("/", response_model=Initiative)
async def create_initiative(
    initiative: Initiative,
    tenant_id: str = Depends(get_tenant_id),
    db: DatabaseClient = Depends(lambda: get_database_client(tenant_id))
):
    """Create a new initiative"""
    initiative.tenant_id = tenant_id
    result = await db.insert("initiatives", initiative.dict())
    return result

@router.put("/{initiative_id}", response_model=Initiative)
async def update_initiative(
    initiative_id: str,
    initiative: Initiative,
    tenant_id: str = Depends(get_tenant_id),
    db: DatabaseClient = Depends(lambda: get_database_client(tenant_id))
):
    """Update an initiative"""
    result = await db.update(
        "initiatives",
        initiative.dict(exclude={"id", "tenant_id"}),
        filters={"id": initiative_id}
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Initiative not found")
    
    return result