# agents/orchestrator/agent.py


from typing import Any, Dict, List, Optional, Literal
from datetime import datetime
from uuid import UUID
from agents.base.agent import AgentConfig, AgentOutput
from agents.orchestrator.prompt_builder import OrchestratorPromptBuilder
from agents.planner.agent import PlanningAgent
from agents.researcher.agent import ResearchAgent
from agents.content_creator.agent import ContentCreatorAgent
from agents.guardrails.initiative_loader import InitiativeLoader
from agents.guardrails.state import InitiativeGenerationState
from backend.db.supabase_client import DatabaseClient
from backend.config.settings import settings
import logging
import uuid

logger = logging.getLogger(__name__)

WorkflowType = Literal[
    "research-only", "planning-only", "content-creation-only",
    "research-then-planning", "planning-then-content", "full-campaign"
]


class WorkflowStep:
    def __init__(self, agent_class, name: str, input_transformer: Optional[callable] = None):
        self.agent_class = agent_class
        self.name = name
        self.input_transformer = input_transformer or (lambda x, _: x)


class OrchestratorAgent:
    """Orchestrator manages workflow execution with guardrails"""
    
    WORKFLOWS = {
        "research-only": [
            WorkflowStep(ResearchAgent, "Research")
        ],
        "planning-only": [
            WorkflowStep(PlanningAgent, "Planning")
        ],
        "content-creation-only": [
            WorkflowStep(ContentCreatorAgent, "Content Creation")
        ],
        "research-then-planning": [
            WorkflowStep(ResearchAgent, "Research"),
            WorkflowStep(PlanningAgent, "Planning",
                lambda input_data, prev_results: {
                    **input_data,
                    "research_results": prev_results.get("Research", {})
                })
        ],
        "planning-then-content": [
            WorkflowStep(PlanningAgent, "Planning"),
            WorkflowStep(ContentCreatorAgent, "Content Creation",
                lambda input_data, prev_results: {
                    **input_data,
                    "campaigns": prev_results.get("Planning", {}).get("campaigns", [])
                })
        ],
        "full-campaign": [
            WorkflowStep(ResearchAgent, "Research"),
            WorkflowStep(PlanningAgent, "Planning",
                lambda input_data, prev_results: {
                    **input_data,
                    "research_results": prev_results.get("Research", {})
                }),
            WorkflowStep(ContentCreatorAgent, "Content Creation",
                lambda input_data, prev_results: {
                    **input_data,
                    "campaigns": prev_results.get("Planning", {}).get("campaigns", [])
                })
        ]
    }
    
    def __init__(self, config: AgentConfig, workflow: WorkflowType = "full-campaign"):
        self.config = config
        self.agent_id = str(uuid.uuid4())
        self.workflow = workflow
        self.workflow_id = str(uuid.uuid4())
        self.execution_id = str(uuid.uuid4())
        self.db_client = DatabaseClient(initiative_id=config.initiative_id)
        self.prompt_builder = OrchestratorPromptBuilder(config.initiative_id)
        self.initiative_loader = InitiativeLoader(config.initiative_id)
        self.initiative_context = None
        self.generation_state = None
        
        if workflow not in self.WORKFLOWS:
            raise ValueError(f"Unknown workflow: {workflow}")
    
    def get_system_prompt(self) -> str:
        """Delegate to prompt builder"""
        return self.prompt_builder.get_system_prompt(self.workflow)
    
    def build_status_message(self, step_name: str, step_num: int, total: int) -> str:
        """Build status message for logging"""
        return self.prompt_builder.build_status_message(
            step_name, step_num, total,
            self.initiative_context.get("statistics", {}) if self.initiative_context else {}
        )
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentOutput:
        """Execute workflow with guardrails and state management"""
        logger.info("\n" + "=" * 80)
        logger.info(f"ORCHESTRATOR: EXECUTING WORKFLOW '{self.workflow}'")
        logger.info("=" * 80)
        
        # Load initiative context
        self.initiative_context = await self.initiative_loader.load_full_context()
        
        # Initialize generation state for content tracking
        ad_set_counts = self._extract_ad_set_counts()
        self.generation_state = InitiativeGenerationState(
            self.config.initiative_id, ad_set_counts
        )
        
        # Create execution log
        await self._create_execution_log()
        
        workflow_steps = self.WORKFLOWS[self.workflow]
        results = {}
        workflow_metadata = {
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "workflow_type": self.workflow,
            "steps_completed": [],
            "steps_failed": [],
            "guardrail_violations": []
        }
        
        # Execute each step
        for i, step in enumerate(workflow_steps, 1):
            logger.info(self.build_status_message(step.name, i, len(workflow_steps)))
            
            try:
                # Create agent configuration
                agent_config = AgentConfig(
                    name=f"{step.name} Agent",
                    description=f"Agent for {step.name}",
                    initiative_id=self.config.initiative_id,
                    model_provider=self.config.model_provider,
                    llm_config=self.config.llm_config,
                    execution_id=self.execution_id,
                    execution_step=step.name
                )
                
                # Instantiate agent
                agent = step.agent_class(agent_config)
                
                # Special handling for ContentCreatorAgent
                if isinstance(agent, ContentCreatorAgent):
                    agent.generation_state = self.generation_state
                
                # Transform input
                step_input = step.input_transformer(input_data, results)
                step_input["workflow_context"] = {
                    "workflow_id": self.workflow_id,
                    "execution_id": self.execution_id,
                    "initiative_context": self.initiative_context,
                    "generation_state": self.generation_state
                }
                
                # Execute agent
                agent_result = await agent.execute(step_input)
                
                if agent_result.success:
                    results[step.name] = agent_result.data
                    workflow_metadata["steps_completed"].append(step.name)
                    
                    # Refresh context if needed
                    if step.name in ["Planning", "Content Creation"]:
                        self.initiative_context = await self.initiative_loader.load_full_context(
                            force_refresh=True
                        )
                else:
                    workflow_metadata["steps_failed"].append(step.name)
                    
                    if "LIMIT EXCEEDED" in str(agent_result.errors):
                        workflow_metadata["guardrail_violations"].append({
                            "step": step.name,
                            "error": agent_result.errors[0]
                        })
                    
                    if self._should_abort_on_failure(step.name):
                        break
                        
            except Exception as e:
                logger.error(f"Exception in {step.name}: {e}")
                workflow_metadata["steps_failed"].append(step.name)
                
                if self._should_abort_on_failure(step.name):
                    break
        
        # Finalize
        workflow_metadata["completed_at"] = datetime.utcnow().isoformat()
        workflow_metadata["success"] = len(workflow_metadata["steps_failed"]) == 0
        
        if self.generation_state:
            workflow_metadata["generation_summary"] = self.generation_state.get_all_summaries()
        
        return AgentOutput(
            agent_name="Orchestrator",
            success=workflow_metadata["success"],
            data=results,
            errors=workflow_metadata.get("steps_failed", []),
            metadata=workflow_metadata
        )
    
    def _extract_ad_set_counts(self) -> Dict[str, Dict[str, int]]:
        """Extract content counts for each ad set"""
        ad_set_counts = {}
        for ad_set in self.initiative_context.get("ad_sets", []):
            counts = ad_set.get("content_counts", {})
            ad_set_counts[ad_set["id"]] = {
                "facebook_posts": counts.get("facebook_posts", 0),
                "instagram_posts": counts.get("instagram_posts", 0),
                "photos": counts.get("photos", 0),
                "videos": counts.get("videos", 0)
            }
        return ad_set_counts
    
    def _should_abort_on_failure(self, step_name: str) -> bool:
        """Determine if workflow should abort on failure"""
        critical_steps = ["Research", "Planning"]
        return settings.ENFORCE_HARD_LIMITS or step_name in critical_steps
    
    async def _create_execution_log(self):
        """Create execution log entry"""
        entry = {
            "execution_id": self.execution_id,
            "initiative_id": self.config.initiative_id,
            "workflow_type": self.workflow,
            "status": "running",
            "started_at": datetime.utcnow().isoformat()
        }
        await self.db_client.insert("execution_logs", entry)