# agents/base/chain.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from openai import OpenAI
from pydantic import BaseModel
import json
import os


class BaseChain(ABC):
    """Base chain class for OpenAI SDK integration"""
    
    def __init__(
        self,
        model_provider: str = "openai",
        llm_config: Optional[Dict[str, Any]] = None
    ):
        self.model_provider = model_provider
        self.llm_config = llm_config or {}
        self.client = self._initialize_client()
        
    def _initialize_client(self) -> OpenAI:
        """Initialize OpenAI client based on provider"""
        from backend.config.settings import settings
        
        # Get provider config
        provider_configs = settings.MODEL_CONFIGS
        config = provider_configs.get(self.model_provider, provider_configs["openai"])
        
        # Override with any provided config
        if self.llm_config:
            for key, value in self.llm_config.items():
                setattr(config, key, value)
        
        # Get API key
        api_key = os.getenv(config.api_key_env)
        if not api_key:
            raise ValueError(f"API key not found for {config.api_key_env}")
        
        # Create client
        client_kwargs = {
            "api_key": api_key,
            "timeout": config.timeout
        }
        
        if config.api_base:
            client_kwargs["base_url"] = config.api_base
        
        return OpenAI(**client_kwargs)
    
    @abstractmethod
    def create_prompt(self, **kwargs) -> str:
        """Create the prompt for the chain"""
        pass
    
    @abstractmethod
    def parse_output(self, output: str) -> Any:
        """Parse the output from the model"""
        pass
    
    async def run(self, **kwargs) -> Any:
        """Run the chain with given inputs"""
        # Validate input
        if not self.validate_input(kwargs):
            raise ValueError("Invalid input data")
        
        # Create prompt
        prompt = self.create_prompt(**kwargs)
        
        # Get model settings
        from backend.config.settings import settings
        provider_configs = settings.MODEL_CONFIGS
        config = provider_configs.get(self.model_provider, provider_configs["openai"])
        
        # Call OpenAI API
        response = self.client.chat.completions.create(
            model=config.model_name,
            messages=[
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            response_format={"type": "json_object"}
        )
        
        # Parse output
        output = self.parse_output(response.choices[0].message.content)
        
        # Validate output
        if not self.validate_output(output):
            raise ValueError("Invalid output from model")
        
        return output
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for the chain"""
        pass
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data"""
        return True
    
    def validate_output(self, output: Any) -> bool:
        """Validate output data"""
        return True