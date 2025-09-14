# backend/db/models/base.py

from pydantic import BaseModel
from uuid import UUID, uuid4
from typing import Optional
import datetime


class CustomModel(BaseModel):
    """Base model class with common features."""
    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime.datetime: lambda v: v.isoformat() if v else None,
        }


class CustomModelInsert(CustomModel):
    """Base model for insert operations with common features."""
    pass


class CustomModelUpdate(CustomModel):
    """Base model for update operations with common features."""
    pass