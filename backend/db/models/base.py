# backend/db/models/base.py

from pydantic import BaseModel
from uuid import UUID, uuid4
from typing import Optional, Dict, Any
import datetime
from backend.db.models.serialization import serialize_dict, prepare_for_db


class CustomModel(BaseModel):
    """Base model class with common features and serialization support."""
    
    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime.datetime: lambda v: v.isoformat() if v else None,
        }
    
    def to_db_dict(self) -> Dict[str, Any]:
        """
        Convert model to dictionary suitable for database insertion.
        Handles all complex types and nested models.
        """
        data = self.dict(exclude_unset=True)
        return serialize_dict(data)
    
    def to_json_dict(self) -> Dict[str, Any]:
        """
        Convert model to JSON-serializable dictionary.
        """
        return serialize_dict(self.dict())
    
    @classmethod
    def from_db_dict(cls, data: Dict[str, Any]):
        """
        Create model instance from database dictionary.
        """
        return cls(**data)


class CustomModelInsert(CustomModel):
    """Base model for insert operations with common features and serialization."""
    
    def to_db_dict(self) -> Dict[str, Any]:
        """
        Convert model to dictionary for database insertion.
        Excludes None values for insert operations.
        """
        data = self.dict(exclude_none=True, exclude_unset=True)
        return serialize_dict(data)


class CustomModelUpdate(CustomModel):
    """Base model for update operations with common features and serialization."""
    
    def to_db_dict(self) -> Dict[str, Any]:
        """
        Convert model to dictionary for database update.
        Only includes set fields for update operations.
        """
        data = self.dict(exclude_unset=True, exclude_none=True)
        return serialize_dict(data)