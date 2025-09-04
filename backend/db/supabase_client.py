# backend/db/supabase_client.py

from supabase import create_client, Client
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv

load_dotenv()

class DatabaseClient:
    """Supabase client with initiative-based RLS support"""

    def __init__(self, initiative_id: Optional[str] = None):
        self.initiative_id = initiative_id
        # Remove the tenant_id confusion
        self.url = os.getenv("SUPABASE_URL")
        self.service_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not self.url or not self.service_key:
            raise ValueError("Supabase credentials not found in environment")
        
        self.client = create_client(self.url, self.service_key)

    def _ensure_initiative_id(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure initiative_id is set in data"""
        if self.initiative_id and "initiative_id" not in data:
            data["initiative_id"] = self.initiative_id
        return data

    def _set_initiative_context(self):
        """Set the initiative context for RLS policies"""
        if self.initiative_id:
            # This sets the context that RLS policies will use
            # Note: This requires postgrest to pass through the header
            # or you may need to use a different approach with Supabase
            pass

    async def insert(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert data with initiative_id automatically added"""
        data = self._ensure_initiative_id(data)

        try:
            result = self.client.table(table_name).insert(data).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            else:
                raise Exception(f"Insert operation returned no data")
        except Exception as e:
            raise Exception(f"Database insert failed for table '{table_name}': {str(e)}")

    async def select(
        self, 
        table_name: str, 
        filters: Optional[Dict[str, Any]] = None,
        columns: str = "*",
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Select data with automatic initiative filtering"""
        query = self.client.table(table_name).select(columns)
        
        # Always filter by initiative_id if set
        if self.initiative_id:
            query = query.eq("initiative_id", self.initiative_id)
        
        # Apply additional filters
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)

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
        """Update data with initiative filtering"""
        query = self.client.table(table_name)
        
        # Always filter by initiative_id if set
        if self.initiative_id:
            query = query.eq("initiative_id", self.initiative_id)
        
        # Apply filters
        for key, value in filters.items():
            query = query.eq(key, value)

        # Execute update
        try:
            result = query.update(data).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            raise Exception(f"Database update failed for table '{table_name}': {str(e)}")

    async def delete(
        self,
        table_name: str,
        filters: Dict[str, Any]
    ) -> bool:
        """Delete data with initiative filtering"""
        query = self.client.table(table_name)
        
        # Always filter by initiative_id if set
        if self.initiative_id:
            query = query.eq("initiative_id", self.initiative_id)
        
        # Apply filters
        for key, value in filters.items():
            query = query.eq(key, value)

        # Execute delete
        result = query.delete().execute()
        return len(result.data) > 0 if result.data else False

    async def get_by_id(self, table_name: str, id: str) -> Optional[Dict[str, Any]]:
        """Get a single record by ID with initiative filtering"""
        filters = {"id": id}
        results = await self.select(table_name, filters=filters)
        return results[0] if results else None

    def raw_client(self) -> Client:
        """Get the raw Supabase client for advanced operations"""
        return self.client

# Factory function for backward compatibility
def get_database_client(initiative_id: Optional[str] = None) -> DatabaseClient:
    """Create a database client instance"""
    return DatabaseClient(initiative_id=initiative_id)