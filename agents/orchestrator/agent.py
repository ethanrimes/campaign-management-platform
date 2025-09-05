# agents/orchestrator/agent.py

"""
Orchestrator Agent for workflow coordination.
Manages and coordinates the execution of multiple agents in defined workflows.
"""

from typing import Any, Dict, List, Optional, Literal
from datetime import datetime
from agents.base.agent import BaseAgent, AgentConfig, AgentOutput
from agents.planner.agent import PlanningAgent
from agents.researcher.agent import ResearchAgent
from agents.content_creator.agent import ContentCreatorAgent
from backend.db.supabase_client import DatabaseClient
import logging
import uuid

logger = logging.getLogger(__name__)

# Define available workflows
WorkflowType = Literal[
    "research-only",
    "planning-only", 
    "content-creation-only",
    "research-then-planning",
    "planning-then-content",
    "full-campaign",
    "test-workflow"
]

class WorkflowStep:
    """Represents a step in a workflow"""
    def __init__(self, agent_class, name: str, input_transformer: Optional[callable] = None):
        self.agent_class = agent_class
        self.name = name
        self.input_transformer = input_transformer or (lambda x, _: x)


class OrchestratorAgent(BaseAgent):
    """Orchestrator agent that coordinates multi-agent workflows"""
    
    # Define workflow configurations
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
                            "ad_sets": prev_results.get("Planning", {}).get("campaigns", [])[0].get("ad_sets", [])
                            if prev_results.get("Planning", {}).get("campaigns") else []
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
                            "ad_sets": prev_results.get("Planning", {}).get("campaigns", [])[0].get("ad_sets", [])
                            if prev_results.get("Planning", {}).get("campaigns") else []
                        })
        ],
        "test-workflow": [
            WorkflowStep(ResearchAgent, "Research")
        ]
    }
    
    def __init__(self, config: AgentConfig, workflow: WorkflowType = "full-campaign"):
        """
        Initialize orchestrator with a specific workflow
        
        Args:
            config: Agent configuration
            workflow: The workflow to execute
        """
        super().__init__(config)
        self.workflow = workflow
        self.workflow_id = str(uuid.uuid4())
        self.db_client = DatabaseClient(initiative_id=config.initiative_id)
        
        if workflow not in self.WORKFLOWS:
            raise ValueError(f"Unknown workflow: {workflow}. Available: {list(self.WORKFLOWS.keys())}")
        
        logger.info(f"Orchestrator initialized with workflow: {workflow}")
        
    def _initialize_tools(self) -> List[Any]:
        """Initialize orchestrator tools"""
        return []  # Orchestrator doesn't need specific tools, it manages agents
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for orchestrator"""
        return """You are an orchestrator AI that coordinates the execution of multiple specialized agents
        to complete complex workflows. Your role is to manage the flow of information between agents,
        ensure proper sequencing, and handle error recovery."""
    
    async def _run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the configured workflow"""
        logger.info("\n" + "="*80)
        logger.info(f"ORCHESTRATOR: EXECUTING WORKFLOW '{self.workflow}'")
        logger.info(f"Workflow ID: {self.workflow_id}")
        logger.info(f"Initiative ID: {self.config.initiative_id}")
        logger.info("="*80)
        
        workflow_steps = self.WORKFLOWS[self.workflow]
        results = {}
        workflow_metadata = {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow,
            "initiative_id": self.config.initiative_id,
            "started_at": datetime.utcnow().isoformat(),
            "steps_completed": [],
            "steps_failed": []
        }
        
        # Execute each step in the workflow
        for i, step in enumerate(workflow_steps, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"STEP {i}/{len(workflow_steps)}: {step.name}")
            logger.info(f"{'='*60}")
            
            try:
                # Create agent configuration
                agent_config = AgentConfig(
                    name=f"{step.name} Agent",
                    description=f"Agent for {step.name}",
                    initiative_id=self.config.initiative_id,
                    model_provider=self.config.model_provider,
                    llm_config=self.config.llm_config,
                    verbose=self.config.verbose
                )
                
                # Instantiate the agent
                agent = step.agent_class(agent_config)
                
                # Transform input based on previous results
                step_input = step.input_transformer(input_data, results)
                
                # Add workflow context to input
                step_input["workflow_context"] = {
                    "workflow_id": self.workflow_id,
                    "workflow_type": self.workflow,
                    "current_step": step.name,
                    "step_number": i,
                    "total_steps": len(workflow_steps),
                    "previous_results_available": list(results.keys())
                }
                
                logger.info(f"Executing {step.name} agent...")
                
                # Execute the agent
                agent_result = await agent.execute(step_input)
                
                if agent_result.success:
                    results[step.name] = agent_result.data
                    workflow_metadata["steps_completed"].append(step.name)
                    
                    # Save intermediate results to database
                    await self._save_step_result(step.name, agent_result.data)
                    
                    logger.info(f"✅ {step.name} completed successfully")
                else:
                    workflow_metadata["steps_failed"].append(step.name)
                    logger.error(f"❌ {step.name} failed: {agent_result.errors}")
                    
                    # Decide whether to continue or abort workflow
                    if self._should_abort_on_failure(step.name):
                        logger.error("Aborting workflow due to critical step failure")
                        break
                
            except Exception as e:
                logger.error(f"❌ Exception in {step.name}: {e}")
                workflow_metadata["steps_failed"].append(step.name)
                
                if self._should_abort_on_failure(step.name):
                    logger.error("Aborting workflow due to exception")
                    break
        
        # Finalize workflow
        workflow_metadata["completed_at"] = datetime.utcnow().isoformat()
        workflow_metadata["success"] = len(workflow_metadata["steps_failed"]) == 0
        
        # Save workflow metadata
        await self._save_workflow_metadata(workflow_metadata)
        
        # Compile final output
        output = {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow,
            "success": workflow_metadata["success"],
            "steps_completed": workflow_metadata["steps_completed"],
            "steps_failed": workflow_metadata["steps_failed"],
            "results": results,
            "metadata": workflow_metadata
        }
        
        logger.info("\n" + "="*80)
        if workflow_metadata["success"]:
            logger.info(f"✅ WORKFLOW '{self.workflow}' COMPLETED SUCCESSFULLY")
        else:
            logger.info(f"⚠️ WORKFLOW '{self.workflow}' COMPLETED WITH ERRORS")
        logger.info(f"Steps completed: {len(workflow_metadata['steps_completed'])}/{len(workflow_steps)}")
        logger.info("="*80)
        
        return output
    
    def _should_abort_on_failure(self, step_name: str) -> bool:
        """Determine if workflow should abort when a step fails"""
        # Critical steps that should abort the workflow if they fail
        critical_steps = ["Research", "Planning"]
        return step_name in critical_steps
    
    async def _save_step_result(self, step_name: str, result: Dict[str, Any]):
        """Save intermediate step results to database"""
        try:
            entry = {
                "workflow_id": self.workflow_id,
                "initiative_id": self.config.initiative_id,
                "step_name": step_name,
                "result_data": result,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Save to a workflow_results table or appropriate location
            # For now, we'll log it - you can implement the actual DB save
            logger.debug(f"Saving {step_name} results to database")
            
        except Exception as e:
            logger.error(f"Failed to save step result: {e}")
    
    async def _save_workflow_metadata(self, metadata: Dict[str, Any]):
        """Save workflow metadata to database"""
        try:
            entry = {
                "workflow_id": self.workflow_id,
                "initiative_id": self.config.initiative_id,
                "workflow_type": self.workflow,
                "metadata": metadata,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Save to a workflows table or appropriate location
            logger.debug("Saving workflow metadata to database")
            
        except Exception as e:
            logger.error(f"Failed to save workflow metadata: {e}")
    
    def validate_output(self, output: Any) -> bool:
        """Validate orchestrator output"""
        if not isinstance(output, dict):
            return False
        
        required_fields = ["workflow_id", "workflow_type", "success", "results"]
        return all(field in output for field in required_fields)
    
    async def get_workflow_status(self) -> Dict[str, Any]:
        """Get the current status of the workflow execution"""
        # This could query the database for workflow status
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow,
            "initiative_id": self.config.initiative_id,
            "status": "running"  # or "completed", "failed", etc.
        }