# scripts/setup/create_initiative.py

import asyncio
import yaml
from pathlib import Path
from backend.config.database import SupabaseClient
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
        
        # Generate tenant ID (in production, this would be provided)
        tenant_id = str(uuid.uuid4())
        
        # Create initiative model
        initiative = Initiative(
            tenant_id=tenant_id,
            name=config["name"],
            description=config["description"],
            facebook_page_id=config["social_accounts"]["facebook"]["page_id"],
            facebook_page_name=config["social_accounts"]["facebook"]["page_name"],
            facebook_page_url=config["social_accounts"]["facebook"]["page_url"],
            instagram_username=config["social_accounts"]["instagram"]["username"],
            instagram_account_id=config["social_accounts"]["instagram"]["account_id"],
            instagram_url=config["social_accounts"]["instagram"]["url"],
            category=config["category"],
            objectives=config["objectives"],
            model_provider=config["model_provider"],
            optimization_metric=config["optimization_metric"],
            target_metrics=config["target_metrics"],
            daily_budget=config["budget"]["daily"],
            total_budget=config["budget"]["total"],
            settings={
                "content_strategy": config["content_strategy"],
                "target_audience": config["target_audience"]
            }
        )
        
        # Save to database
        db = SupabaseClient(tenant_id=tenant_id)
        result = await db.insert("initiatives", initiative.dict())
        
        logger.info(f"Initiative created successfully: {result['id']}")
        logger.info(f"Tenant ID: {tenant_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to create initiative: {e}")
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
    
    if result:
        print(f"Initiative created successfully!")
        print(f"Initiative ID: {result['id']}")
        print(f"Save this Tenant ID for API calls: {result['tenant_id']}")


if __name__ == "__main__":
    asyncio.run(main())