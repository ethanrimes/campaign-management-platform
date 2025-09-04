#!/usr/bin/env python3
# scripts/setup/create_initiative.py

"""
Interactive script to create a new initiative with encrypted token storage.
Prompts user for all necessary tokens and configuration, encrypts sensitive data,
and stores everything in Supabase.

Usage:
    python scripts/setup/create_initiative.py
"""

import asyncio
import os
import sys
import uuid
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from getpass import getpass
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.utils.encryption import TokenEncryption
from backend.db.supabase_client import DatabaseClient
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class InitiativeCreator:
    """Interactive initiative creation with encrypted token storage"""
    
    def __init__(self):
        self.encryption = TokenEncryption()
        self.initiative_id = str(uuid.uuid4())
        self.tokens = {}
        self.metadata = {}
        
    def print_header(self):
        """Print welcome header"""
        print("\n" + "="*70)
        print("CAMPAIGN MANAGEMENT PLATFORM - INITIATIVE SETUP")
        print("="*70)
        print("\nThis wizard will guide you through creating a new initiative.")
        print("You'll need to provide access tokens for Facebook and Instagram.")
        print("All tokens will be encrypted before storage.\n")
        
    def prompt_basic_info(self) -> Dict[str, Any]:
        """Prompt for basic initiative information"""
        print("\n" + "-"*50)
        print("BASIC INITIATIVE INFORMATION")
        print("-"*50)
        
        info = {}
        
        # Initiative name
        info['name'] = input("\nInitiative Name: ").strip()
        while not info['name']:
            print("❌ Name cannot be empty")
            info['name'] = input("Initiative Name: ").strip()
        
        # Description
        info['description'] = input("Description (optional): ").strip()
        
        # Category
        print("\nCategory Options:")
        categories = ["Education", "Business", "Nonprofit", "Entertainment", "Technology", "Other"]
        for i, cat in enumerate(categories, 1):
            print(f"  {i}. {cat}")
        
        while True:
            choice = input("Select category (1-6): ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(categories):
                    info['category'] = categories[idx]
                    break
            except:
                pass
            print("❌ Invalid selection")
        
        # Optimization metric
        print("\nOptimization Metric:")
        metrics = ["reach", "engagement", "traffic", "conversions"]
        for i, metric in enumerate(metrics, 1):
            print(f"  {i}. {metric}")
        
        while True:
            choice = input("Select metric (1-4): ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(metrics):
                    info['optimization_metric'] = metrics[idx]
                    break
            except:
                pass
            print("❌ Invalid selection")
        
        # Budget
        print("\nBudget Configuration:")
        while True:
            try:
                daily = input("Daily budget in USD (e.g., 100): ").strip()
                info['daily_budget'] = {"amount": float(daily), "currency": "USD"}
                break
            except:
                print("❌ Invalid amount")
        
        while True:
            try:
                total = input("Total campaign budget in USD (e.g., 3000): ").strip()
                info['total_budget'] = {"amount": float(total), "currency": "USD"}
                break
            except:
                print("❌ Invalid amount")
        
        return info
    
    def prompt_facebook_tokens(self) -> Dict[str, str]:
        """Prompt for Facebook-related tokens"""
        print("\n" + "-"*50)
        print("FACEBOOK CONFIGURATION")
        print("-"*50)
        print("\nYou'll need:")
        print("1. Facebook Page ID")
        print("2. Facebook Page Access Token")
        print("3. System User Token (optional)")
        print("\nRefer to Meta Business Suite to obtain these values.")
        
        fb_tokens = {}
        
        # Page ID (not encrypted, just metadata)
        fb_tokens['page_id'] = input("\nFacebook Page ID: ").strip()
        while not fb_tokens['page_id']:
            print("❌ Page ID cannot be empty")
            fb_tokens['page_id'] = input("Facebook Page ID: ").strip()
        
        # Page Name (optional metadata)
        fb_tokens['page_name'] = input("Facebook Page Name (optional): ").strip()
        
        # Page Access Token (sensitive - will be encrypted)
        print("\nPaste Facebook Page Access Token (hidden):")
        fb_tokens['page_access_token'] = getpass("Token: ").strip()
        while not fb_tokens['page_access_token']:
            print("❌ Page Access Token cannot be empty")
            fb_tokens['page_access_token'] = getpass("Token: ").strip()
        
        # System User Token (optional, sensitive)
        print("\nSystem User Token (optional, press Enter to skip):")
        system_token = getpass("Token: ").strip()
        if system_token:
            fb_tokens['system_user_token'] = system_token
        
        return fb_tokens
    
    def prompt_instagram_tokens(self) -> Dict[str, str]:
        """Prompt for Instagram-related tokens"""
        print("\n" + "-"*50)
        print("INSTAGRAM CONFIGURATION")
        print("-"*50)
        print("\nYou'll need:")
        print("1. Instagram Business Account ID")
        print("2. Instagram Access Token")
        print("3. Instagram App ID (optional)")
        print("4. Instagram App Secret (optional)")
        
        ig_tokens = {}
        
        # Business Account ID (metadata)
        ig_tokens['business_id'] = input("\nInstagram Business Account ID: ").strip()
        while not ig_tokens['business_id']:
            print("❌ Business Account ID cannot be empty")
            ig_tokens['business_id'] = input("Instagram Business Account ID: ").strip()
        
        # Username (metadata)
        ig_tokens['username'] = input("Instagram Username (optional): ").strip()
        
        # Access Token (sensitive)
        print("\nPaste Instagram Access Token (hidden):")
        ig_tokens['access_token'] = getpass("Token: ").strip()
        while not ig_tokens['access_token']:
            print("❌ Instagram Access Token cannot be empty")
            ig_tokens['access_token'] = getpass("Token: ").strip()
        
        # App ID (optional, sensitive)
        ig_app_id = input("\nInstagram App ID (optional, press Enter to skip): ").strip()
        if ig_app_id:
            ig_tokens['app_id'] = ig_app_id
        
        # App Secret (optional, sensitive)
        print("\nInstagram App Secret (optional, hidden):")
        ig_app_secret = getpass("Secret: ").strip()
        if ig_app_secret:
            ig_tokens['app_secret'] = ig_app_secret
        
        return ig_tokens
    
    def encrypt_tokens(self, fb_tokens: Dict, ig_tokens: Dict) -> Dict[str, str]:
        """Encrypt sensitive tokens"""
        encrypted = {}
        
        # Encrypt Facebook tokens
        if fb_tokens.get('page_access_token'):
            encrypted['fb_page_access_token_encrypted'] = self.encryption.encrypt(
                fb_tokens['page_access_token']
            )
        
        if fb_tokens.get('system_user_token'):
            encrypted['fb_system_user_token_encrypted'] = self.encryption.encrypt(
                fb_tokens['system_user_token']
            )
        
        # Encrypt Instagram tokens
        if ig_tokens.get('access_token'):
            encrypted['insta_access_token_encrypted'] = self.encryption.encrypt(
                ig_tokens['access_token']
            )
        
        if ig_tokens.get('app_id'):
            encrypted['insta_app_id_encrypted'] = self.encryption.encrypt(
                ig_tokens['app_id']
            )
        
        if ig_tokens.get('app_secret'):
            encrypted['insta_app_secret_encrypted'] = self.encryption.encrypt(
                ig_tokens['app_secret']
            )
        
        return encrypted
    
    async def save_to_database(self, basic_info: Dict, fb_tokens: Dict, ig_tokens: Dict):
        """Save initiative and encrypted tokens to Supabase"""
        try:
            # Initialize Supabase client with service key for admin operations
            client = create_client(
                os.getenv("SUPABASE_URL"),
                os.getenv("SUPABASE_SERVICE_KEY")
            )
            
            # Prepare initiative data
            initiative_data = {
                "id": self.initiative_id,
                "tenant_id": self.initiative_id,
                "name": basic_info['name'],
                "description": basic_info.get('description', ''),
                "category": basic_info.get('category'),
                "optimization_metric": basic_info.get('optimization_metric'),
                "daily_budget": basic_info.get('daily_budget'),
                "total_budget": basic_info.get('total_budget'),
                "model_provider": "openai",
                "is_active": True,
                # Store non-sensitive metadata
                "facebook_page_id": fb_tokens.get('page_id'),
                "facebook_page_name": fb_tokens.get('page_name'),
                "instagram_business_id": ig_tokens.get('business_id'),
                "instagram_username": ig_tokens.get('username'),
            }
            
            # Save initiative
            result = client.table("initiatives").insert(initiative_data).execute()
            
            if not result.data:
                raise Exception("Failed to create initiative")
            
            # Encrypt sensitive tokens
            encrypted_tokens = self.encrypt_tokens(fb_tokens, ig_tokens)
            
            # Prepare token data
            token_data = {
                "tenant_id": self.initiative_id,
                "initiative_id": self.initiative_id,
                **encrypted_tokens,
                # Non-sensitive metadata
                "fb_page_id": fb_tokens.get('page_id'),
                "fb_page_name": fb_tokens.get('page_name'),
                "insta_business_id": ig_tokens.get('business_id'),
                "insta_username": ig_tokens.get('username'),
                "created_by": "setup_script"
            }
            
            # Save encrypted tokens
            token_result = client.table("initiative_tokens").insert(token_data).execute()
            
            if not token_result.data:
                # Rollback initiative creation if token storage fails
                client.table("initiatives").delete().eq("id", self.initiative_id).execute()
                raise Exception("Failed to store tokens")
            
            return True
            
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise
    
    def save_credentials(self, basic_info: Dict):
        """Save tenant ID and initiative ID to a file for reference"""
        creds_dir = Path("credentials")
        creds_dir.mkdir(exist_ok=True)
        
        creds_file = creds_dir / f"{basic_info['name'].replace(' ', '_').lower()}_credentials.json"
        
        credentials = {
            "initiative_name": basic_info['name'],
            "initiative_id": self.initiative_id,
            "created_at": datetime.now().isoformat(),
            "note": "Use these IDs for API calls and agent operations"
        }
        
        with open(creds_file, 'w') as f:
            json.dump(credentials, f, indent=2)
        
        return creds_file
    
    async def run(self):
        """Run the interactive setup process"""
        self.print_header()
        
        # Check encryption key
        if not os.getenv("ENCRYPTION_KEY"):
            print("\n⚠️  WARNING: No ENCRYPTION_KEY found in .env file")
            print("Generating a new encryption key...")
            key = TokenEncryption.generate_key()
            print(f"\nAdd this to your .env file:")
            print(f"ENCRYPTION_KEY={key}")
            print("\nPress Enter after adding the key to continue...")
            input()
            os.environ["ENCRYPTION_KEY"] = key
        
        # Collect information
        basic_info = self.prompt_basic_info()
        fb_tokens = self.prompt_facebook_tokens()
        ig_tokens = self.prompt_instagram_tokens()
        
        # Confirm before saving
        print("\n" + "="*50)
        print("REVIEW YOUR CONFIGURATION")
        print("="*50)
        print(f"\nInitiative: {basic_info['name']}")
        print(f"Category: {basic_info.get('category')}")
        print(f"Daily Budget: ${basic_info['daily_budget']['amount']}")
        print(f"Facebook Page: {fb_tokens.get('page_name', fb_tokens['page_id'])}")
        print(f"Instagram: @{ig_tokens.get('username', ig_tokens['business_id'])}")
        
        confirm = input("\nSave this configuration? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("❌ Setup cancelled")
            return
        
        # Save to database
        print("\n🔄 Saving to database...")
        try:
            await self.save_to_database(basic_info, fb_tokens, ig_tokens)
            
            # Save credentials file
            creds_file = self.save_credentials(basic_info)
            
            print("\n" + "="*70)
            print("✅ INITIATIVE CREATED SUCCESSFULLY!")
            print("="*70)
            print(f"\n📋 Initiative Name: {basic_info['name']}")
            print(f"🆔 Initiative ID: {self.initiative_id}")
            print(f"🏢 Tenant ID: {self.tenant_id}")
            print(f"\n💾 Credentials saved to: {creds_file}")
            print("\n⚡ Use these IDs for:")
            print("  • API calls (X-Tenant-ID header)")
            print("  • Running agents")
            print("  • Accessing data")
            print("\n🔒 All tokens have been encrypted and stored securely.")
            
        except Exception as e:
            print(f"\n❌ Error creating initiative: {e}")
            print("\nPlease check your database connection and try again.")
            sys.exit(1)


async def main():
    """Main entry point"""
    creator = InitiativeCreator()
    await creator.run()


if __name__ == "__main__":
    asyncio.run(main())