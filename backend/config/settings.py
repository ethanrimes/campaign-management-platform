# backend/config/settings.py (Updated version with encryption)

from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum


class ModelProvider(str, Enum):
    OPENAI = "openai"
    GROK = "grok"
    GEMINI = "gemini"

class ModelConfig(BaseModel):
    """Model configuration for OpenAI SDK"""
    provider: ModelProvider
    api_key_env: str  # Environment variable name for API key
    api_base: Optional[str] = None  # Custom API endpoint
    model_name: str = "gpt-5"
    temperature: float = 0.7
    max_tokens: int = 4000
    timeout: int = 60


class Settings(BaseSettings):
    """Global application settings with encryption support"""
    
    # Application
    APP_NAME: str = "Campaign Management Platform"
    APP_VERSION: str = "2.0.0"  # Updated for token encryption feature
    DEBUG: bool = False
    
    # Database
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: str  # For admin operations
    SUPABASE_DB_URL: Optional[str] = None  # Direct Postgres connection for migrations
    
    # Encryption
    ENCRYPTION_KEY: Optional[str] = None  # Key for encrypting tokens
    
    # API Keys (loaded from environment) - for development/testing only
    # Production tokens should be stored encrypted in database
    OPENAI_API_KEY: Optional[str] = None
    GROK_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    PERPLEXITY_API_KEY: Optional[str] = None
    
    # Meta (Facebook/Instagram) API - App-level credentials only
    # Page/User specific tokens are stored encrypted in database
    META_APP_ID: str
    META_APP_SECRET: str
    
    # Model Provider Configurations
    MODEL_CONFIGS: Dict[str, ModelConfig] = {
        "openai": ModelConfig(
            provider=ModelProvider.OPENAI,
            api_key_env="OPENAI_API_KEY",
            model_name="gpt-4-turbo-preview"
        ),
        "grok": ModelConfig(
            provider=ModelProvider.GROK,
            api_key_env="GROK_API_KEY",
            api_base="https://api.x.ai/v1",
            model_name="grok-2"
        ),
        "gemini": ModelConfig(
            provider=ModelProvider.GEMINI,
            api_key_env="GEMINI_API_KEY",
            api_base="https://generativelanguage.googleapis.com/v1beta",
            model_name="gemini-1.5-pro"
        )
    }
    
    # Default Model Configuration
    DEFAULT_MODEL_PROVIDER: ModelProvider = ModelProvider.OPENAI
    
    # Budget Configuration
    DEFAULT_DAILY_BUDGET: float = 100.0
    DEFAULT_CAMPAIGN_BUDGET: float = 1000.0
    BUDGET_WARNING_THRESHOLD: float = 0.8  # Warn when 80% spent
    
    # Scheduling
    ORCHESTRATOR_SCHEDULE: str = "0 */6 * * *"  # Every 6 hours
    CONTENT_CREATOR_SCHEDULE: str = "0 */4 * * *"  # Every 4 hours
    RESEARCHER_SCHEDULE: str = "0 0 * * *"  # Daily at midnight
    METRICS_COLLECTOR_SCHEDULE: str = "0 * * * *"  # Every hour
    
    # Content Generation
    MAX_HASHTAGS: int = 30
    MAX_POST_LENGTH: int = 2200  # Instagram caption limit
    IMAGE_GENERATION_MODEL: str = "dalle-3"
    VIDEO_GENERATION_MODEL: str = "runway-ml"
    
    # Rate Limiting
    API_RATE_LIMIT: int = 100  # requests per minute
    CONTENT_GENERATION_LIMIT: int = 50  # posts per day
    
    # Security
    TOKEN_CACHE_DURATION: int = 3600  # Cache decrypted tokens for 1 hour
    REQUIRE_ENCRYPTED_TOKENS: bool = True  # Enforce encrypted token storage
    
    # Paths
    PROMPTS_DIR: str = "agents/*/prompts"
    INITIATIVES_DIR: str = "initiatives"
    ASSETS_DIR: str = "assets"
    CREDENTIALS_DIR: str = "credentials"  # For storing initiative credentials
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    def validate_encryption_key(self):
        """Validate that encryption key is configured"""
        if self.REQUIRE_ENCRYPTED_TOKENS and not self.ENCRYPTION_KEY:
            raise ValueError(
                "ENCRYPTION_KEY is required when REQUIRE_ENCRYPTED_TOKENS is True. "
                "Generate one with: python scripts/setup/generate_encryption_key.py"
            )


settings = Settings()

# Validate encryption on startup
if settings.REQUIRE_ENCRYPTED_TOKENS:
    settings.validate_encryption_key()