# backend/db/supabase_client.py

from supabase import create_client, Client
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv

load_dotenv()

class DatabaseClient:
    """Enhanced Supabase client with tenant support and proper query building"""

    def __init__(self, tenant_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.url = os.getenv("SUPABASE_URL")
        self.service_key = os.getenv("SUPABASE_SERVICE_KEY")

        if not self.url or not self.service_key:
            raise ValueError("Supabase credentials not found in environment")

        # Create the Supabase client
        self.client = create_client(self.url, self.service_key)

    def _apply_tenant_filter(self, query, table_name: str):
        """Apply tenant filter to query if tenant_id is set"""
        if self.tenant_id and table_name != "initiatives":
            return query.eq("tenant_id", self.tenant_id)
        return query

    async def insert(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert data with tenant_id automatically added"""
        if self.tenant_id and "tenant_id" not in data:
            data["tenant_id"] = self.tenant_id

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
        """Select data with automatic tenant filtering"""
        # Start with base query
        query = self.client.table(table_name).select(columns)

        # Apply tenant filter first if needed
        query = self._apply_tenant_filter(query, table_name)

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
        """Update data with tenant filtering"""
        # Start with base query
        query = self.client.table(table_name)

        # Apply tenant filter first if needed
        query = self._apply_tenant_filter(query, table_name)

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
        """Delete data with tenant filtering"""
        # Start with base query
        query = self.client.table(table_name)

        # Apply tenant filter first if needed
        query = self._apply_tenant_filter(query, table_name)

        # Apply filters
        for key, value in filters.items():
            query = query.eq(key, value)

        # Execute delete
        result = query.delete().execute()
        return len(result.data) > 0 if result.data else False

    async def get_by_id(self, table_name: str, id: str) -> Optional[Dict[str, Any]]:
        """Get a single record by ID with tenant filtering"""
        results = await self.select(table_name, filters={"id": id})
        return results[0] if results else None

    def raw_client(self) -> Client:
        """Get the raw Supabase client for advanced operations"""
        return self.client

# Factory function for backward compatibility
def get_database_client(tenant_id: Optional[str] = None) -> DatabaseClient:
    """Create a database client instance"""
    return DatabaseClient(tenant_id=tenant_id)