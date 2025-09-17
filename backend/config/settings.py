# backend/config/settings.py (Updated with Wavespeed)

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
    APP_VERSION: str = "2.1.0"  # Updated for Wavespeed integration
    DEBUG: bool = False
    
    # Database
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: str  # For admin operations
    SUPABASE_DB_URL: Optional[str] = None  # Direct Postgres connection for migrations
    
    # Encryption
    ENCRYPTION_KEY: Optional[str] = None  # Key for encrypting tokens
    
    # API Keys (loaded from environment)
    OPENAI_API_KEY: Optional[str] = None
    GROK_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    PERPLEXITY_API_KEY: Optional[str] = None
    WAVESPEED_API_KEY: Optional[str] = None  # Added Wavespeed API key
    
    # Meta (Facebook/Instagram) API
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
    
    # Media Generation Configuration
    WAVESPEED_IMAGE_MODEL: str = "stability-ai/sdxl-lora"
    WAVESPEED_VIDEO_MODEL: str = "wavespeed-ai/wan-2.2/i2v-5b-720p"
    WAVESPEED_API_BASE: str = "https://api.wavespeed.ai/api/v3"
    WAVESPEED_POLLING_INTERVAL: float = 2.0  # seconds between polls
    WAVESPEED_MAX_POLL_ATTEMPTS: int = 120  # max attempts before timeout
    
    # Budget Configuration
    DEFAULT_DAILY_BUDGET: float = 100.0
    DEFAULT_CAMPAIGN_BUDGET: float = 1000.0
    BUDGET_WARNING_THRESHOLD: float = 0.8
    
    # Scheduling
    ORCHESTRATOR_SCHEDULE: str = "0 */6 * * *"
    CONTENT_CREATOR_SCHEDULE: str = "0 */4 * * *"
    RESEARCHER_SCHEDULE: str = "0 0 * * *"
    METRICS_COLLECTOR_SCHEDULE: str = "0 * * * *"
    
    # Content Generation
    MAX_HASHTAGS: int = 30
    MAX_POST_LENGTH: int = 2200
    
    # Rate Limiting
    API_RATE_LIMIT: int = 100
    CONTENT_GENERATION_LIMIT: int = 50
    
    # Security
    TOKEN_CACHE_DURATION: int = 3600
    REQUIRE_ENCRYPTED_TOKENS: bool = True
    
    # Paths
    PROMPTS_DIR: str = "agents/*/prompts"
    INITIATIVES_DIR: str = "initiatives"
    ASSETS_DIR: str = "assets"
    CREDENTIALS_DIR: str = "credentials"

    # Content generation limits per ad set (on a single content_creator call)
    MAX_FACEBOOK_POSTS_PER_AD_SET: int = 5
    MAX_INSTAGRAM_POSTS_PER_AD_SET: int = 5
    MAX_PHOTOS_PER_AD_SET: int = 25
    MAX_VIDEOS_PER_AD_SET: int = 4

    # Content limits per individual post
    MAX_VIDEOS_PER_POST: int = 1
    MAX_PHOTOS_PER_POST: int = 3

    # Planner limits for active entities
    MAX_ACTIVE_CAMPAIGNS_PER_INITIATIVE: int = 2
    MIN_ACTIVE_CAMPAIGNS_PER_INITIATIVE: int = 1
    MAX_ACTIVE_AD_SETS_PER_CAMPAIGN: int = 5
    MIN_ACTIVE_AD_SETS_PER_CAMPAIGN: int = 1

    # --- Agent Guardrail Settings ---
    RESEARCH_AGENT_MAX_ATTEMPTS: int = 1
    PLANNER_AGENT_MAX_ATTEMPTS: int = 3
    CONTENT_CREATOR_AGENT_MAX_ATTEMPTS: int = 3
    MAX_RESEARCH_OUTPUT_LENGTH: int = 50000  # Character limit for researcher output

    # --- Validation Strictness ---
    ENFORCE_HARD_LIMITS: bool = True  # If False, log warnings but don't block
    VALIDATION_ERROR_DETAIL_LEVEL: str = "verbose"  # "verbose" or "simple"
    
    MAX_RESEARCH_QUERIES: int = 1

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