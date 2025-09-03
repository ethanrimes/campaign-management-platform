# backend/api/middleware/tenant.py

from fastapi import Header, HTTPException
from typing import Optional

async def get_tenant_id(x_tenant_id: Optional[str] = Header(None)) -> str:
    """Extract tenant ID from headers"""
    if not x_tenant_id:
        raise HTTPException(
            status_code=400,
            detail="X-Tenant-ID header is required"
        )
    return x_tenant_id