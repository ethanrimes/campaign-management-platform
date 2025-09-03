# backend/api/middleware/auth.py

from fastapi import Header, HTTPException
from typing import Optional

async def verify_token(authorization: Optional[str] = Header(None)):
    """Verify authentication token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    # In production, verify the token properly
    # For now, just check if it exists
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization.replace("Bearer ", "")
    
    # Validate token (implement proper validation)
    if len(token) < 10:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return token
