# agents/base/agent.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from openai import OpenAI
import os
import uuid
import yaml
from backend.config.settings import settings, ModelConfig


class AgentConfig(BaseModel):
    """Base configuration for all agents"""
    name: str
    description: str
    initiative_id: str  # Only use initiative_id
    model_provider: str = "openai"
    llm_config: Optional[ModelConfig] = None
    verbose: bool = False
    
    class Config:
        arbitrary_types_allowed = True


class AgentOutput(BaseModel):
    """Base output structure for all agents"""
    agent_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool
    data: Dict[str, Any]
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """Base agent class for all system agents using OpenAI SDK"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = str(uuid.uuid4())
        self.client = self._initialize_client()
        self.memory = []  # Simple memory as list of messages
        self.tools = self._initialize_tools()
        
    def _initialize_client(self) -> OpenAI:
        """Initialize OpenAI client with appropriate configuration"""
        # Load initiative config to get model settings
        model_config = self.config.llm_config or self._load_model_config()
        
        # Get API key from environment
        api_key = os.getenv(model_config.api_key_env)
        if not api_key:
            raise ValueError(f"API key not found for {model_config.api_key_env}")
        
        # Create OpenAI client with custom endpoint if needed
        client_kwargs = {
            "api_key": api_key,
            "timeout": model_config.timeout
        }
        
        if model_config.api_base:
            client_kwargs["base_url"] = model_config.api_base
        
        return OpenAI(**client_kwargs)
    
    def _load_model_config(self) -> ModelConfig:
        """Load model configuration from initiative settings"""
        # Try to load from initiative config file
        initiative_config_path = f"initiatives/{self.config.initiative_id}/config.yaml"
        
        if os.path.exists(initiative_config_path):
            with open(initiative_config_path, 'r') as f:
                config_data = yaml.safe_load(f)
                model_provider = config_data.get("model_provider", self.config.model_provider)
        else:
            model_provider = self.config.model_provider
        
        # Get model config from settings
        if model_provider in settings.MODEL_CONFIGS:
            return settings.MODEL_CONFIGS[model_provider]
        
        # Default to OpenAI
        return settings.MODEL_CONFIGS["openai"]
    
    @abstractmethod
    def _initialize_tools(self) -> List[Any]:
        """Initialize agent-specific tools"""
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for the agent"""
        pass
    
    @abstractmethod
    def validate_output(self, output: Any) -> bool:
        """Validate agent output"""
        pass
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentOutput:
        """Execute the agent's main task"""
        try:
            # Run the agent
            result = await self._run(input_data)
            
            # Validate output
            if not self.validate_output(result):
                return AgentOutput(
                    agent_name=self.config.name,
                    success=False,
                    data={},
                    errors=["Output validation failed"]
                )
            
            return AgentOutput(
                agent_name=self.config.name,
                success=True,
                data=result,
                metadata={"agent_id": self.agent_id}
            )
            
        except Exception as e:
            return AgentOutput(
                agent_name=self.config.name,
                success=False,
                data={},
                errors=[str(e)]
            )
    
    async def _run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the agent with OpenAI SDK"""
        # Prepare messages
        messages = [
            {"role": "system", "content": self.get_system_prompt()}
        ]
        
        # Add memory/context
        messages.extend(self.memory[-10:])  # Last 10 messages for context
        
        # Add current input
        user_message = self._format_input(input_data)
        messages.append({"role": "user", "content": user_message})
        
        # Get model config
        model_config = self.config.llm_config or self._load_model_config()
        
        # Call OpenAI API
        response = self.client.chat.completions.create(
            model=model_config.model_name,
            messages=messages,
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens,
            response_format={"type": "json_object"}  # Force JSON output
        )
        
        # Parse response
        result = self._parse_response(response.choices[0].message.content)
        
        # Add to memory
        self.memory.append({"role": "user", "content": user_message})
        self.memory.append({"role": "assistant", "content": response.choices[0].message.content})
        
        return result
    
    def _format_input(self, input_data: Dict[str, Any]) -> str:
        """Format input data for the prompt"""
        import json
        return json.dumps(input_data, indent=2)
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the response from the model"""
        import json
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"raw_response": response}
    
    def clear_memory(self):
        """Clear agent memory"""
        self.memory = []
    
    def get_memory_summary(self) -> str:
        """Get a summary of the agent's memory"""
        return "\n".join([f"{msg['role']}: {msg['content'][:100]}..." for msg in self.memory])

