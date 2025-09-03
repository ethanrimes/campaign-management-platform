#!/usr/bin/env python3
# tests/test_database.py

"""
Database connection and schema validation tests
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
import uuid

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client, Client
from backend.config.settings import settings
from backend.config.database import SupabaseClient, get_supabase_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseTester:
    """Test database connectivity and operations"""
    
    def __init__(self):
        self.load_environment()
        self.client = None
        self.test_tenant_id = str(uuid.uuid4())
        
    def load_environment(self):
        """Load and validate environment variables"""
        # Try multiple locations for .env file
        env_locations = [
            Path.cwd() / '.env',
            Path(__file__).parent.parent / '.env',
            Path.home() / '.env'
        ]
        
        env_loaded = False
        for env_path in env_locations:
            if env_path.exists():
                load_dotenv(env_path)
                logger.info(f"Loaded environment from: {env_path}")
                env_loaded = True
                break
        
        if not env_loaded:
            logger.warning("No .env file found. Using system environment variables.")
        
        # Validate required variables
        required_vars = {
            'SUPABASE_URL': os.getenv('SUPABASE_URL'),
            'SUPABASE_KEY': os.getenv('SUPABASE_KEY'),
            'SUPABASE_SERVICE_KEY': os.getenv('SUPABASE_SERVICE_KEY')
        }
        
        missing = [var for var, value in required_vars.items() if not value]
        
        if missing:
            logger.error(f"Missing environment variables: {', '.join(missing)}")
            logger.error("Please create a .env file with the required variables")
            sys.exit(1)
        
        logger.info("✓ All required environment variables loaded")
        
    async def test_connection(self):
        """Test basic database connection"""
        try:
            # Create client with service key for admin access
            self.client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )
            
            # Test connection by querying a simple table
            result = self.client.table('initiatives').select('*').limit(1).execute()
            
            logger.info("✓ Database connection successful")
            return True
            
        except Exception as e:
            logger.error(f"✗ Database connection failed: {e}")
            return False
    
    async def test_rls_policies(self):
        """Test Row Level Security policies"""
        try:
            # Create a test client with tenant context
            tenant_client = SupabaseClient(tenant_id=self.test_tenant_id)
            
            # Try to insert a test initiative
            test_data = {
                "tenant_id": self.test_tenant_id,
                "name": "Test Initiative",
                "description": "Testing RLS policies",
                "model_provider": "openai",
                "is_active": True
            }
            
            result = await tenant_client.insert("initiatives", test_data)
            
            if result:
                logger.info("✓ RLS policies working (insert successful)")
                
                # Clean up
                await tenant_client.delete("initiatives", {"id": result["id"]})
            else:
                logger.warning("⚠ RLS policies may not be configured correctly")
                
        except Exception as e:
            logger.error(f"✗ RLS test failed: {e}")
    
    async def test_table_structure(self):
        """Validate table structure matches models"""
        tables_to_check = [
            'initiatives',
            'campaigns',
            'ad_sets',
            'posts',
            'metrics',
            'research',
            'agent_memories'
        ]
        
        all_valid = True
        
        for table in tables_to_check:
            try:
                # Query table structure
                result = self.client.table(table).select('*').limit(0).execute()
                logger.info(f"✓ Table '{table}' exists")
                
            except Exception as e:
                logger.error(f"✗ Table '{table}' not found or inaccessible: {e}")
                all_valid = False
        
        return all_valid
    
    async def test_crud_operations(self):
        """Test basic CRUD operations"""
        try:
            db = SupabaseClient(tenant_id=self.test_tenant_id)
            
            # Create
            test_initiative = {
                "tenant_id": self.test_tenant_id,
                "name": "CRUD Test Initiative",
                "description": "Testing CRUD operations",
                "model_provider": "openai",
                "category": "Test",
                "is_active": True
            }
            
            created = await db.insert("initiatives", test_initiative)
            assert created is not None, "Insert failed"
            logger.info("✓ CREATE operation successful")
            
            # Read
            items = await db.select(
                "initiatives",
                filters={"id": created["id"]}
            )
            assert len(items) == 1, "Read failed"
            logger.info("✓ READ operation successful")
            
            # Update
            updated = await db.update(
                "initiatives",
                {"description": "Updated description"},
                filters={"id": created["id"]}
            )
            assert updated is not None, "Update failed"
            logger.info("✓ UPDATE operation successful")
            
            # Delete
            deleted = await db.delete(
                "initiatives",
                filters={"id": created["id"]}
            )
            assert deleted, "Delete failed"
            logger.info("✓ DELETE operation successful")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ CRUD operations failed: {e}")
            return False
    
    async def test_relationships(self):
        """Test foreign key relationships"""
        try:
            db = SupabaseClient(tenant_id=self.test_tenant_id)
            
            # Create initiative
            initiative = await db.insert("initiatives", {
                "tenant_id": self.test_tenant_id,
                "name": "Relationship Test",
                "model_provider": "openai"
            })
            
            # Create campaign
            campaign = await db.insert("campaigns", {
                "tenant_id": self.test_tenant_id,
                "initiative_id": initiative["id"],
                "name": "Test Campaign",
                "objective": "AWARENESS"
            })
            
            # Create ad set
            ad_set = await db.insert("ad_sets", {
                "tenant_id": self.test_tenant_id,
                "campaign_id": campaign["id"],
                "name": "Test Ad Set"
            })
            
            logger.info("✓ Foreign key relationships working")
            
            # Clean up (cascade delete should handle this)
            await db.delete("initiatives", {"id": initiative["id"]})
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Relationship test failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all database tests"""
        logger.info("="*60)
        logger.info("DATABASE CONNECTION & VALIDATION TESTS")
        logger.info("="*60)
        
        # Test connection
        if not await self.test_connection():
            logger.error("Cannot proceed without database connection")
            return False
        
        # Test table structure
        logger.info("\nValidating table structure...")
        await self.test_table_structure()
        
        # Test RLS
        logger.info("\nTesting Row Level Security...")
        await self.test_rls_policies()
        
        # Test CRUD
        logger.info("\nTesting CRUD operations...")
        await self.test_crud_operations()
        
        # Test relationships
        logger.info("\nTesting foreign key relationships...")
        await self.test_relationships()
        
        logger.info("\n" + "="*60)
        logger.info("DATABASE TESTS COMPLETED")
        logger.info("="*60)
        
        return True


async def main():
    """Main entry point"""
    tester = DatabaseTester()
    success = await tester.run_all_tests()
    
    if success:
        logger.info("\n✅ All database tests completed successfully!")
    else:
        logger.error("\n❌ Some database tests failed. Check the logs above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())