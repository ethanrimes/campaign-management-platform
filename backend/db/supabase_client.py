# backend/db/supabase_client.py

from supabase import create_client, Client
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv

# Import serialization utilities
from backend.db.models.serialization import prepare_for_db, serialize_dict

load_dotenv()

class DatabaseClient:
    """Supabase client with initiative-based RLS support and automatic serialization"""

    def __init__(self, initiative_id: Optional[str] = None):
        self.initiative_id = initiative_id
        self.url = os.getenv("SUPABASE_URL")
        self.service_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not self.url or not self.service_key:
            raise ValueError("Supabase credentials not found in environment")
        
        self.client = create_client(self.url, self.service_key)
        
        # Set initiative context for RLS
        if self.initiative_id:
            self._set_initiative_context()

    def _ensure_initiative_id(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure initiative_id is set in data (except for initiatives table itself)"""
        # Don't add initiative_id to the initiatives table itself
        if self.initiative_id and "initiative_id" not in data:
            data["initiative_id"] = self.initiative_id
        return data

    def _set_initiative_context(self):
        """Set the initiative context for RLS policies"""
        if self.initiative_id:
            try:
                # Try to set the PostgreSQL session variable using SQL
                self.client.postgrest.session.headers.update({
                    'x-initiative-id': self.initiative_id
                })
            except Exception as e:
                # Log error but don't fail - RLS will still work through query filtering
                print(f"Warning: Could not set initiative context for RLS: {e}")

    def _prepare_data(self, data: Any) -> Any:
        """
        Prepare data for database operations using serialization utilities.
        Handles Pydantic models, complex types, and nested structures.
        """
        # If it's a Pydantic model with to_db_dict method, use it
        if hasattr(data, 'to_db_dict'):
            return data.to_db_dict()
        
        # Otherwise use the general prepare_for_db utility
        return prepare_for_db(data)

    async def insert(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert data with initiative_id automatically added and serialization"""
        # Serialize the data first
        serialized_data = self._prepare_data(data)
        
        # Only add initiative_id for tables other than initiatives
        if table_name != "initiatives":
            serialized_data = self._ensure_initiative_id(serialized_data)

        try:
            result = self.client.table(table_name).insert(serialized_data).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            else:
                raise Exception(f"Insert operation returned no data")
        except Exception as e:
            # Add more context to the error
            import json
            print(f"Failed to insert into {table_name}")
            print(f"Serialized data: {json.dumps(serialized_data, default=str)[:500]}...")
            raise Exception(f"Database insert failed for table '{table_name}': {str(e)}")

    async def insert_many(self, table_name: str, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Insert multiple records with serialization"""
        # Serialize each record
        serialized_list = []
        for data in data_list:
            serialized_data = self._prepare_data(data)
            
            # Only add initiative_id for tables other than initiatives
            if table_name != "initiatives":
                serialized_data = self._ensure_initiative_id(serialized_data)
            
            serialized_list.append(serialized_data)

        try:
            result = self.client.table(table_name).insert(serialized_list).execute()
            return result.data if result.data else []
        except Exception as e:
            raise Exception(f"Database bulk insert failed for table '{table_name}': {str(e)}")

    async def select(
        self, 
        table_name: str, 
        filters: Optional[Dict[str, Any]] = None,
        columns: str = "*",
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Select data with automatic initiative filtering"""
        query = self.client.table(table_name).select(columns)
        
        # Special handling for initiatives table vs other tables
        if self.initiative_id:
            if table_name == "initiatives":
                # For initiatives table, filter by 'id' not 'initiative_id'
                query = query.eq("id", self.initiative_id)
            else:
                # For all other tables, filter by 'initiative_id'
                query = query.eq("initiative_id", self.initiative_id)
        
        # Apply additional filters (serialize filter values if needed)
        if filters:
            for key, value in filters.items():
                # Serialize complex filter values
                serialized_value = self._prepare_data(value)
                query = query.eq(key, serialized_value)

        # Apply limit
        if limit:
            query = query.limit(limit)

        # Execute query
        result = query.execute()
        return result.data if result.data else []

    async def update(
        self,
        table_name: str,
        data: Dict[str, Any],
        filters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update data with initiative filtering and serialization"""
        # Serialize the update data
        serialized_data = self._prepare_data(data)
        
        # Start with update operation
        query = self.client.table(table_name).update(serialized_data)
        
        # Apply initiative filter
        if self.initiative_id:
            if table_name == "initiatives":
                query = query.eq("id", self.initiative_id)
            else:
                query = query.eq("initiative_id", self.initiative_id)
        
        # Apply additional filters (serialize filter values if needed)
        for key, value in filters.items():
            serialized_value = self._prepare_data(value)
            query = query.eq(key, serialized_value)

        # Execute update
        try:
            result = query.execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            raise Exception(f"Database update failed for table '{table_name}': {str(e)}")

    async def upsert(
        self,
        table_name: str,
        data: Dict[str, Any],
        on_conflict: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Upsert (insert or update) data with serialization"""
        # Serialize the data
        serialized_data = self._prepare_data(data)
        
        # Only add initiative_id for tables other than initiatives
        if table_name != "initiatives":
            serialized_data = self._ensure_initiative_id(serialized_data)

        try:
            # Build the upsert query
            query = self.client.table(table_name).upsert(
                serialized_data,
                on_conflict=on_conflict or 'id'
            )
            
            result = query.execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            raise Exception(f"Database upsert failed for table '{table_name}': {str(e)}")

    async def delete(
        self,
        table_name: str,
        filters: Dict[str, Any]
    ) -> bool:
        """Delete data with initiative filtering"""
        # Start with delete operation
        query = self.client.table(table_name).delete()
        
        # Apply initiative filter
        if self.initiative_id:
            if table_name == "initiatives":
                query = query.eq("id", self.initiative_id)
            else:
                query = query.eq("initiative_id", self.initiative_id)
        
        # Apply additional filters (serialize filter values if needed)
        for key, value in filters.items():
            serialized_value = self._prepare_data(value)
            query = query.eq(key, serialized_value)

        # Execute delete
        result = query.execute()
        return len(result.data) > 0 if result.data else False

    async def get_by_id(self, table_name: str, id: str) -> Optional[Dict[str, Any]]:
        """Get a single record by ID with initiative filtering"""
        # Ensure ID is properly serialized (in case it's a UUID object)
        serialized_id = self._prepare_data(id)
        filters = {"id": serialized_id}
        results = await self.select(table_name, filters=filters)
        return results[0] if results else None

    def raw_client(self) -> Client:
        """Get the raw Supabase client for advanced operations"""
        return self.client

# Factory function for backward compatibility
def get_database_client(initiative_id: Optional[str] = None) -> DatabaseClient:
    """Create a database client instance"""
    return DatabaseClient(initiative_id=initiative_id)