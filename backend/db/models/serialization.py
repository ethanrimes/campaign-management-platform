# backend/db/models/serialization.py

"""
Custom serialization utilities for database models.
Handles conversion of complex types to JSON-serializable formats.
"""

from typing import Any, Dict, List, Union
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from enum import Enum
import json


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for complex types"""
    
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, Enum):
            return obj.value
        elif hasattr(obj, 'dict'):  # Pydantic models
            return obj.dict()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)


def serialize_value(value: Any) -> Any:
    """
    Recursively serialize a value to be JSON-compatible.
    Handles nested structures, Pydantic models, and special types.
    """
    if value is None:
        return None
    
    # Handle datetime
    if isinstance(value, datetime):
        return value.isoformat()
    
    # Handle date
    if isinstance(value, date):
        return value.isoformat()
    
    # Handle UUID
    if isinstance(value, UUID):
        return str(value)
    
    # Handle Decimal
    if isinstance(value, Decimal):
        return float(value)
    
    # Handle Enum
    if isinstance(value, Enum):
        return value.value
    
    # Handle Pydantic models
    if hasattr(value, 'dict'):
        return serialize_dict(value.dict())
    
    # Handle dictionaries
    if isinstance(value, dict):
        return serialize_dict(value)
    
    # Handle lists
    if isinstance(value, list):
        return [serialize_value(item) for item in value]
    
    # Handle tuples
    if isinstance(value, tuple):
        return [serialize_value(item) for item in value]
    
    # Handle sets
    if isinstance(value, set):
        return [serialize_value(item) for item in value]
    
    # Return as-is for basic types (str, int, float, bool)
    return value


def serialize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize a dictionary, handling nested structures and special types.
    """
    if not isinstance(data, dict):
        return data
    
    result = {}
    for key, value in data.items():
        result[key] = serialize_value(value)
    
    return result


def deserialize_datetime(value: Union[str, datetime, None]) -> Union[datetime, None]:
    """
    Deserialize a datetime value from various formats.
    """
    if value is None:
        return None
    
    if isinstance(value, datetime):
        return value
    
    if isinstance(value, str):
        try:
            # Handle ISO format with timezone
            if 'T' in value:
                if value.endswith('Z'):
                    value = value[:-1] + '+00:00'
                return datetime.fromisoformat(value)
            # Handle date-only format
            else:
                return datetime.strptime(value, '%Y-%m-%d')
        except (ValueError, AttributeError):
            return None
    
    return None


def deserialize_uuid(value: Union[str, UUID, None]) -> Union[UUID, None]:
    """
    Deserialize a UUID value from various formats.
    """
    if value is None:
        return None
    
    if isinstance(value, UUID):
        return value
    
    if isinstance(value, str):
        try:
            return UUID(value)
        except (ValueError, AttributeError):
            return None
    
    return None


def deserialize_decimal(value: Union[str, int, float, Decimal, None]) -> Union[Decimal, None]:
    """
    Deserialize a Decimal value from various formats.
    """
    if value is None:
        return None
    
    if isinstance(value, Decimal):
        return value
    
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return None


class SerializableBaseModel:
    """
    Mixin class for Pydantic models to add serialization capabilities.
    """
    
    def to_db_dict(self) -> Dict[str, Any]:
        """
        Convert model to dictionary suitable for database insertion.
        Handles all complex types and nested models.
        """
        if hasattr(self, 'dict'):
            data = self.dict(exclude_unset=True)
        else:
            data = self.__dict__.copy()
        
        return serialize_dict(data)
    
    def to_json(self) -> str:
        """
        Convert model to JSON string.
        """
        return json.dumps(self.to_db_dict(), cls=CustomJSONEncoder)
    
    @classmethod
    def from_db_dict(cls, data: Dict[str, Any]):
        """
        Create model instance from database dictionary.
        Override this method in subclasses for custom deserialization.
        """
        return cls(**data)


def prepare_for_db(data: Any) -> Any:
    """
    Prepare any data structure for database insertion.
    This is the main entry point for serialization.
    """
    if hasattr(data, 'to_db_dict'):
        return data.to_db_dict()
    elif hasattr(data, 'dict'):
        return serialize_dict(data.dict())
    elif isinstance(data, dict):
        return serialize_dict(data)
    else:
        return serialize_value(data)