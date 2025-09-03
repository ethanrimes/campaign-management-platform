# backend/config/database.py

from supabase import create_client, Client
from typing import Optional, Dict, Any, List
from .settings import settings
import os


class SupabaseClient:
    """Wrapper for Supabase client with RLS support"""
    
    def __init__(self, tenant_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.client = self._create_client()
    
    def _create_client(self) -> Client:
        """Create Supabase client"""
        # Use service key for admin operations if no tenant_id
        if not self.tenant_id:
            return create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )
        
        # Use regular key with RLS for tenant-specific operations
        client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
        
        # Set RLS context for tenant
        if self.tenant_id:
            client.auth.set_session({
                "access_token": self._generate_tenant_token(),
                "refresh_token": ""
            })
        
        return client
    
    def _generate_tenant_token(self) -> str:
        """Generate JWT token for tenant RLS"""
        # In production, this would generate a proper JWT with tenant claims
        # For now, we'll use the tenant_id in headers
        return f"tenant_{self.tenant_id}"
    
    def get_table(self, table_name: str):
        """Get table reference with automatic tenant filtering"""
        table = self.client.table(table_name)
        
        # Automatically add tenant filter if tenant_id is set
        if self.tenant_id and table_name != "initiatives":
            table = table.eq("tenant_id", self.tenant_id)
        
        return table
    
    async def insert(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert data with tenant_id automatically added"""
        if self.tenant_id:
            data["tenant_id"] = self.tenant_id
        
        result = self.client.table(table_name).insert(data).execute()
        return result.data[0] if result.data else None
    
    async def select(
        self, 
        table_name: str, 
        filters: Optional[Dict[str, Any]] = None,
        columns: str = "*",
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Select data with automatic tenant filtering"""
        query = self.get_table(table_name).select(columns)
        
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        return result.data
    
    async def update(
        self,
        table_name: str,
        data: Dict[str, Any],
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update data with tenant filtering"""
        query = self.get_table(table_name)
        
        for key, value in filters.items():
            query = query.eq(key, value)
        
        result = query.update(data).execute()
        return result.data[0] if result.data else None
    
    async def delete(
        self,
        table_name: str,
        filters: Dict[str, Any]
    ) -> bool:
        """Delete data with tenant filtering"""
        query = self.get_table(table_name)
        
        for key, value in filters.items():
            query = query.eq(key, value)
        
        result = query.delete().execute()
        return len(result.data) > 0


def get_supabase_client(tenant_id: Optional[str] = None) -> SupabaseClient:
    """Factory function to get Supabase client"""
    return SupabaseClient(tenant_id=tenant_id)


async def init_database():
    """Initialize database tables using SQL migration"""
    # This would run the SQL migration file
    # For Supabase, tables are typically created via the dashboard or migration files
    pass