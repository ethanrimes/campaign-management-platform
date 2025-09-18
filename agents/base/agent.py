# agents/base/agent.py

"""
Base agent class with LangChain structured output support.
Provides common functionality for all system agents.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
import os
import uuid
import yaml
import json
import logging
from backend.config.settings import settings, ModelConfig
from backend.db.models.serialization import serialize_dict, prepare_for_db

# LangChain imports
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.schema.runnable import RunnablePassthrough

logger = logging.getLogger(__name__)


class AgentConfig(BaseModel):
    """Base configuration for all agents"""
    name: str
    description: str
    initiative_id: str
    model_provider: str = "openai"
    llm_config: Optional[ModelConfig] = None
    verbose: bool = False
    execution_id: Optional[str] = None
    execution_step: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True


class AgentOutput(BaseModel):
    """Base output structure for all agents with serialization support"""
    agent_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool
    data: Dict[str, Any]
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization"""
        return serialize_dict(self.dict())
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


class BaseAgent(ABC):
    """Base agent class for all system agents using LangChain with structured output"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = str(uuid.uuid4())
        self.execution_id = config.execution_id
        self.execution_step = config.execution_step
        
        # Initialize LangChain LLM
        model_config = config.llm_config or self._load_model_config()
        self.llm = self._initialize_llm(model_config)
        
        # Initialize shared loader if not already set by child
        if not hasattr(self, 'initiative_loader'):
            from agents.guardrails.initiative_loader import InitiativeLoader
            self.initiative_loader = InitiativeLoader(config.initiative_id)
        
        # Parser will be initialized per agent with their specific output model
        self.parser = None
        self.format_instructions = None
        
        # Initialize tools (agent-specific)
        self.tools = self._initialize_tools()
    
    def _initialize_llm(self, model_config: ModelConfig) -> ChatOpenAI:
        """Initialize LangChain LLM with appropriate configuration"""
        # Get API key from environment
        api_key = os.getenv(model_config.api_key_env)
        if not api_key:
            raise ValueError(f"API key not found for {model_config.api_key_env}")
        
        # Create LangChain LLM
        llm_kwargs = {
            "model": model_config.model_name,
            "temperature": model_config.temperature,
            "max_tokens": model_config.max_tokens,
            "openai_api_key": api_key,
            "request_timeout": model_config.timeout
        }
        
        # Add custom endpoint if specified
        if model_config.api_base:
            llm_kwargs["openai_api_base"] = model_config.api_base
        
        return ChatOpenAI(**llm_kwargs)
    
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
    def get_output_model(self) -> Type[BaseModel]:
        """Get the Pydantic model for structured output"""
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for the agent"""
        pass
    
    @abstractmethod
    def build_user_prompt(self, input_data: Dict[str, Any], error_feedback: Optional[str] = None) -> str:
        """Build the user prompt with input data and optional error feedback"""
        pass

    def _sanitize_llm_output(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-process LLM output to fix common issues like UUID generation.
        Override in child classes for agent-specific sanitization.
        """
        return output
    
    def initialize_parser(self):
        """Initialize the parser with the agent's output model"""
        output_model = self.get_output_model()
        self.parser = PydanticOutputParser(pydantic_object=output_model)
        self.format_instructions = self.parser.get_format_instructions()
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentOutput:
        """
        Main execution method that delegates to child's _run() method.
        This ensures child-specific logic (like save_plan) is executed.
        """
        try:
            # Ensure input data is properly serialized
            serialized_input = prepare_for_db(input_data)
            
            # Call the child's _run() method which handles all agent-specific logic
            result = await self._run(serialized_input)
            
            # Serialize the result data
            serialized_result = prepare_for_db(result)
            
            return AgentOutput(
                agent_name=self.config.name,
                success=True,
                data=serialized_result,
                metadata={
                    "agent_id": self.agent_id,
                    "execution_id": self.execution_id,
                    "execution_step": self.execution_step
                }
            )
            
        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            
            return AgentOutput(
                agent_name=self.config.name,
                success=False,
                data={},
                errors=[str(e)],
                metadata={
                    "agent_id": self.agent_id,
                    "error_detail": error_detail
                }
            )
    
    @abstractmethod
    async def _run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agent-specific execution logic. Must be implemented by each agent.
        This method should:
        1. Process input data
        2. Call execute_with_retries() for LLM interaction
        3. Validate output with guardrails
        4. Save/persist any necessary data
        5. Return the final result
        """
        pass
    
    async def execute_with_retries(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute LLM call with retry logic and structured output.
        Fetches fresh context on EACH attempt to ensure data consistency.
        """
        # Ensure parser is initialized
        if not self.parser:
            self.initialize_parser()
        
        max_attempts = getattr(settings, f"{self.__class__.__name__.upper()}_MAX_ATTEMPTS", 3)
        error_feedback = None
        
        for attempt in range(max_attempts):
            logger.info(f"🤖 {self.config.name} - Attempt {attempt + 1}/{max_attempts}")
            
            # CRITICAL: Always fetch fresh context for each attempt
            # This ensures we have the latest state from the database
            logger.debug(f"Fetching fresh context for attempt {attempt + 1}")
            fresh_context = await self.initiative_loader.load_full_context(force_refresh=True)
            
            # Merge fresh context with input data
            enhanced_input = {
                **input_data,
                "context": fresh_context,
                "statistics": fresh_context.get("statistics", {})
            }
            
            # Build prompts with fresh data
            system_prompt = self.get_system_prompt()
            user_prompt = self.build_user_prompt(enhanced_input, error_feedback)
            
            # Add format instructions
            enhanced_user_prompt = user_prompt + "\n\n{format_instructions}"
            
            # Create LangChain prompt template
            prompt = PromptTemplate(
                template=system_prompt + "\n\n" + enhanced_user_prompt,
                input_variables=[],
                partial_variables={"format_instructions": self.format_instructions}
            )
            
            # Adjust temperature for retries
            self.llm.temperature = self.llm.temperature * (0.9 ** attempt)
            
            # Create the chain
            chain = prompt | self.llm | self.parser
            
            try:
                # Execute the chain
                logger.info(f"Calling LLM for {self.config.name}...")
                output = chain.invoke({})
                
                logger.debug(f"Output: {output}")
                logger.debug(f"Output type: {type(output)}")
                
                # Convert to dict if it's a Pydantic model
                if isinstance(output, BaseModel):
                    result = output.dict()
                else:
                    result = output

                result = self._sanitize_llm_output(result)
                
                # Validate output structure
                if self.validate_output(result):
                    # Additional validation with fresh context if agent has validator
                    if hasattr(self, 'validator') and self.validator:
                        is_valid, error_msg = self.validator.validate(result, fresh_context)
                        if not is_valid:
                            error_feedback = f"Validation failed: {error_msg}"
                            logger.warning(error_feedback)
                            continue
                    
                    logger.info(f"✅ {self.config.name} succeeded on attempt {attempt + 1}")
                    return result
                else:
                    error_feedback = "Output validation failed. Check required fields."
                    
            except Exception as e:
                error_feedback = f"Error: {str(e)}"
                logger.warning(f"Attempt {attempt + 1} failed: {error_feedback}")
                
                if "Pydantic" in str(e) or "ValidationError" in str(e):
                    error_feedback = f"Output format error: {str(e)}. Ensure all required fields are present."
            
            if attempt < max_attempts - 1:
                logger.info("Retrying with fresh context and error feedback...")
        
        # If all attempts failed
        raise Exception(f"{self.config.name} failed after {max_attempts} attempts. Last error: {error_feedback}")
    
    async def fetch_fresh_context(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch fresh context from database. 
        Override in child classes for agent-specific context needs.
        """
        return input_data
    
    async def validate_output_with_context(self, output: Any, context: Dict[str, Any]) -> bool:
        """
        Validate output with fresh context.
        Override in child classes for context-aware validation.
        """
        return self.validate_output(output)
    

    @abstractmethod
    def validate_output(self, output: Any) -> bool:
        """
        Validate the structure of the LLM output.
        Must be implemented by each agent to validate their specific output model.
        """
        pass
    
    def _serialize_for_db(self, data: Any) -> Any:
        """Helper method for agents to serialize data for database operations"""
        return prepare_for_db(data)


class SerializableBaseModel(BaseModel):
    """Base Pydantic model with serialization support for agent models"""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization"""
        return serialize_dict(self.dict())
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to database-ready dictionary"""
        return prepare_for_db(self.dict())