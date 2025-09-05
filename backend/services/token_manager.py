# backend/services/token_manager.py

"""
Token management service for secure retrieval and decryption of social media tokens.
Used by agents to fetch necessary credentials for API calls.
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime
import logging
from backend.utils.encryption import TokenEncryption
from backend.db.supabase_client import DatabaseClient
from supabase import create_client

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages encrypted token retrieval and decryption for agents"""
    
    def __init__(self, initiative_id: str):
        """
        Initialize token manager for a specific initiative
        
        Args:
            initiative_id: Initiative identifier
        """
        self.initiative_id = initiative_id
        self.encryption = TokenEncryption()
        self._tokens_cache = None
        self._cache_timestamp = None
        self.cache_duration = 3600  # Cache for 1 hour
        
        # Initialize Supabase client
        self.client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_KEY")
        )
    
    async def get_facebook_tokens(self) -> Dict[str, str]:
        """
        Retrieve and decrypt Facebook tokens
        
        Returns:
            Dictionary containing:
            - page_access_token: Decrypted page access token
            - system_user_token: Decrypted system user token (if available)
            - page_id: Facebook page ID (not encrypted)
            - page_name: Facebook page name (if available)
        """
        tokens = await self._get_tokens()
        
        fb_tokens = {
            "page_id": tokens.get("fb_page_id", ""),
            "page_name": tokens.get("fb_page_name", "")
        }
        
        # Decrypt sensitive tokens
        if tokens.get("fb_page_access_token_encrypted"):
            try:
                fb_tokens["page_access_token"] = self.encryption.decrypt(
                    tokens["fb_page_access_token_encrypted"]
                )
            except Exception as e:
                logger.error(f"Failed to decrypt Facebook page access token: {e}")
                raise
        
        if tokens.get("fb_system_user_token_encrypted"):
            try:
                fb_tokens["system_user_token"] = self.encryption.decrypt(
                    tokens["fb_system_user_token_encrypted"]
                )
            except Exception as e:
                logger.warning(f"Failed to decrypt Facebook system user token: {e}")
                # System user token is optional, so don't raise
        
        return fb_tokens
    
    async def get_instagram_tokens(self) -> Dict[str, str]:
        """
        Retrieve and decrypt Instagram tokens
        
        Returns:
            Dictionary containing:
            - access_token: Decrypted Instagram access token
            - app_id: Decrypted Instagram app ID (if available)
            - app_secret: Decrypted Instagram app secret (if available)
            - business_id: Instagram business account ID (not encrypted)
            - username: Instagram username (if available)
        """
        tokens = await self._get_tokens()
        
        ig_tokens = {
            "business_id": tokens.get("insta_business_id", ""),
            "username": tokens.get("insta_username", "")
        }
        
        # Decrypt sensitive tokens
        if tokens.get("insta_access_token_encrypted"):
            try:
                ig_tokens["access_token"] = self.encryption.decrypt(
                    tokens["insta_access_token_encrypted"]
                )
            except Exception as e:
                logger.error(f"Failed to decrypt Instagram access token: {e}")
                raise
        
        if tokens.get("insta_app_id_encrypted"):
            try:
                ig_tokens["app_id"] = self.encryption.decrypt(
                    tokens["insta_app_id_encrypted"]
                )
            except Exception as e:
                logger.warning(f"Failed to decrypt Instagram app ID: {e}")
        
        if tokens.get("insta_app_secret_encrypted"):
            try:
                ig_tokens["app_secret"] = self.encryption.decrypt(
                    tokens["insta_app_secret_encrypted"]
                )
            except Exception as e:
                logger.warning(f"Failed to decrypt Instagram app secret: {e}")
        
        return ig_tokens
    
    async def get_all_tokens(self) -> Dict[str, Dict[str, str]]:
        """
        Retrieve all tokens for both platforms
        
        Returns:
            Dictionary with 'facebook' and 'instagram' keys containing respective tokens
        """
        return {
            "facebook": await self.get_facebook_tokens(),
            "instagram": await self.get_instagram_tokens()
        }
    
    async def _get_tokens(self) -> Dict[str, Any]:
        """
        Fetch tokens from database with caching
        
        Returns:
            Raw token data from database
        """
        # Check cache
        if self._tokens_cache and self._cache_timestamp:
            cache_age = (datetime.now() - self._cache_timestamp).total_seconds()
            if cache_age < self.cache_duration:
                return self._tokens_cache
        
        # Fetch from database
        try:
            result = self.client.table("initiative_tokens").select("*").eq(
                "initiative_id", self.initiative_id
            ).execute()
            
            if not result.data or len(result.data) == 0:
                raise ValueError(f"No tokens found for initiative {self.initiative_id}")
            
            tokens = result.data[0]
            
            # Update cache
            self._tokens_cache = tokens
            self._cache_timestamp = datetime.now()
            
            return tokens
            
        except Exception as e:
            logger.error(f"Failed to fetch tokens from database: {e}")
            raise
    
    async def validate_tokens(self) -> Dict[str, bool]:
        """
        Validate that all required tokens are present
        
        Returns:
            Dictionary indicating which token sets are valid
        """
        try:
            tokens = await self._get_tokens()
            
            validation = {
                "facebook": bool(tokens.get("fb_page_access_token_encrypted")),
                "instagram": bool(tokens.get("insta_access_token_encrypted")),
                "has_fb_system_token": bool(tokens.get("fb_system_user_token_encrypted")),
                "has_ig_app_credentials": bool(
                    tokens.get("insta_app_id_encrypted") and 
                    tokens.get("insta_app_secret_encrypted")
                )
            }
            
            return validation
            
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return {
                "facebook": False,
                "instagram": False,
                "has_fb_system_token": False,
                "has_ig_app_credentials": False
            }
    
    def clear_cache(self):
        """Clear the token cache"""
        self._tokens_cache = None
        self._cache_timestamp = None


class TokenContext:
    """Context manager for temporary token usage"""
    
    def __init__(self, initiative_id: str):
        self.manager = TokenManager(initiative_id)
        self.tokens = None
    
    async def __aenter__(self):
        """Load and decrypt tokens on entry"""
        self.tokens = await self.manager.get_all_tokens()
        return self.tokens
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clear sensitive data on exit"""
        self.tokens = None
        self.manager.clear_cache()