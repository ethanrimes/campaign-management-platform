# scripts/setup/create_initiative.py

import asyncio
import yaml
from pathlib import Path
from backend.db.supabase_client import DatabaseClient
from backend.db.models.initiative import Initiative
import logging
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_initiative_from_config(config_path: str):
    """Create an initiative from a YAML configuration file"""
    try:
        # Load configuration
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Generate tenant ID
        tenant_id = str(uuid.uuid4())
        
        # Create initiative data directly as dict to ensure all fields are included
        initiative_data = {
            "tenant_id": tenant_id,
            "name": config["name"],
            "description": config.get("description", ""),
            "facebook_page_id": config.get("social_accounts", {}).get("facebook", {}).get("page_id"),
            "facebook_page_name": config.get("social_accounts", {}).get("facebook", {}).get("page_name"),
            "facebook_page_url": config.get("social_accounts", {}).get("facebook", {}).get("page_url"),
            "instagram_username": config.get("social_accounts", {}).get("instagram", {}).get("username"),
            "instagram_account_id": config.get("social_accounts", {}).get("instagram", {}).get("account_id"),
            "instagram_url": config.get("social_accounts", {}).get("instagram", {}).get("url"),
            "category": config.get("category"),
            "objectives": config.get("objectives"),
            "model_provider": config.get("model_provider", "openai"),
            "optimization_metric": config.get("optimization_metric"),
            "target_metrics": config.get("target_metrics"),
            "daily_budget": config.get("budget", {}).get("daily"),
            "total_budget": config.get("budget", {}).get("total"),
            "is_active": True,
            "settings": {
                "content_strategy": config.get("content_strategy"),
                "target_audience": config.get("target_audience")
            }
        }
        
        logger.info("Creating initiative with data:")
        logger.info(initiative_data)
        
        # Use service key client for initial setup (no tenant context)
        db = DatabaseClient()  # No tenant_id for admin operations
        
        # Direct insert using the raw Supabase client
        result = db.client.table("initiatives").insert(initiative_data).execute()
        
        if result.data and len(result.data) > 0:
            created_initiative = result.data[0]
            logger.info(f"Initiative created successfully: {created_initiative['id']}")
            logger.info(f"Tenant ID: {tenant_id}")
            
            print(f"\n✅ Initiative created successfully!")
            print(f"Initiative ID: {created_initiative['id']}")
            print(f"Tenant ID: {tenant_id}")
            print(f"\nSave the Tenant ID above - you'll need it for API calls!")
            
            return created_initiative
        else:
            logger.error("No data returned from insert operation")
            return None
        
    except Exception as e:
        logger.error(f"Failed to create initiative: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python create_initiative.py <config_file>")
        print("Example: python create_initiative.py initiatives/penn_education/config.yaml")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    if not Path(config_path).exists():
        print(f"Configuration file not found: {config_path}")
        sys.exit(1)
    
    result = await create_initiative_from_config(config_path)


if __name__ == "__main__":
    asyncio.run(main())