# backend/api/middleware/initiative.py

from fastapi import Header, HTTPException
from typing import Optional

async def get_initiative_id(x_initiative_id: Optional[str] = Header(None)) -> str:
    """Extract initiative ID from headers"""
    if not x_initiative_id:
        raise HTTPException(
            status_code=400,
            detail="X-Initiative-ID header is required"
        )
    return x_initiative_id