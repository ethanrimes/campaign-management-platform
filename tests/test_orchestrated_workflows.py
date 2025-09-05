#!/usr/bin/env python3
# tests/test_orchestrated_workflows.py

"""
Test script for orchestrated workflows.
Uses the OrchestratorAgent to coordinate multi-agent workflows.

Usage:
    python tests/test_orchestrated_workflows.py [workflow_type]
    
    workflow_type options:
        - research-only
        - planning-only
        - research-then-planning
        - full-campaign
        - all (runs all workflows)
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import argparse
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import logging config first
from backend.config.logging_config import LoggingConfig

# Setup logging before other imports
LoggingConfig.setup_test_logging()
logger = logging.getLogger(__name__)

from agents.orchestrator.agent import OrchestratorAgent, WorkflowType
from agents.base.agent import AgentConfig
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test configuration - REPLACE WITH YOUR ACTUAL INITIATIVE ID
TEST_INITIATIVE_ID = "bf2d9675-b236-4a86-8514-78b0b6d75a53"


class WorkflowTester:
    """Test harness for orchestrated workflows"""
    
    def __init__(self, initiative_id: str):
        self.initiative_id = initiative_id
        self.test_results = {}
        
    async def test_workflow(self, workflow_type: WorkflowType) -> bool:
        """
        Test a specific workflow
        
        Args:
            workflow_type: The workflow to test
            
        Returns:
            True if successful, False otherwise
        """
        logger.info("\n" + "="*80)
        logger.info(f"TESTING WORKFLOW: {workflow_type}")
        logger.info("="*80)
        
        try:
            # Create orchestrator configuration
            config = AgentConfig(
                name=f"Orchestrator for {workflow_type}",
                description=f"Testing {workflow_type} workflow",
                initiative_id=self.initiative_id,
                model_provider="openai",
                verbose=True
            )
            
            # Initialize orchestrator with specified workflow
            orchestrator = OrchestratorAgent(config, workflow=workflow_type)
            
            # Prepare input based on workflow type
            input_data = self._get_workflow_input(workflow_type)
            
            logger.info(f"\n📋 Input for {workflow_type}:")
            logger.info(json.dumps(input_data, indent=2))
            
            # Execute workflow
            logger.info(f"\n🚀 Executing {workflow_type} workflow...")
            result = await orchestrator.execute(input_data)
            
            # Process result
            if result.success:
                logger.info(f"\n✅ {workflow_type} workflow completed successfully")
                self._display_workflow_results(workflow_type, result.data)
                self.test_results[workflow_type] = {
                    "success": True,
                    "data": result.data
                }
                
                # Save results to file
                await self._save_test_results(workflow_type, result.data)
                
                return True
            else:
                logger.error(f"\n❌ {workflow_type} workflow failed")
                logger.error(f"Errors: {result.errors}")
                self.test_results[workflow_type] = {
                    "success": False,
                    "errors": result.errors
                }
                return False
                
        except Exception as e:
            logger.error(f"\n❌ Exception testing {workflow_type}: {e}")
            import traceback
            traceback.print_exc()
            self.test_results[workflow_type] = {
                "success": False,
                "error": str(e)
            }
            return False
    
    def _get_workflow_input(self, workflow_type: WorkflowType) -> Dict[str, Any]:
        """Get appropriate input data for the workflow type"""
        base_input = {
            "trigger": "test",
            "test_mode": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Customize input based on workflow
        if workflow_type in ["planning-only", "research-then-planning", "full-campaign"]:
            base_input.update({
                "planning_window_days": 30,
                "force_new_campaigns": False,
                "budget_override": None
            })
        
        if workflow_type in ["content-creation-only", "planning-then-content"]:
            base_input.update({
                "content_volume": 3,
                "content_types": ["image", "video", "carousel"]
            })
        
        if workflow_type == "research-only":
            base_input.update({
                "research_focus": ["market trends", "competitor analysis"],
                "include_hashtags": True
            })
        
        return base_input
    
    def _display_workflow_results(self, workflow_type: str, results: Dict[str, Any]):
        """Display workflow results in a formatted way"""
        logger.info(f"\n📊 RESULTS FOR {workflow_type}")
        logger.info("-" * 60)
        
        # Display workflow metadata
        metadata = results.get("metadata", {})
        logger.info(f"Workflow ID: {results.get('workflow_id', 'N/A')}")
        logger.info(f"Steps Completed: {', '.join(metadata.get('steps_completed', []))}")
        
        if metadata.get("steps_failed"):
            logger.warning(f"Steps Failed: {', '.join(metadata['steps_failed'])}")
        
        # Display step-specific results
        step_results = results.get("results", {})
        
        for step_name, step_data in step_results.items():
            logger.info(f"\n📌 {step_name} Results:")
            
            if step_name == "Research":
                self._display_research_results(step_data)
            elif step_name == "Planning":
                self._display_planning_results(step_data)
            elif step_name == "Content Creation":
                self._display_content_results(step_data)
    
    def _display_research_results(self, data: Dict[str, Any]):
        """Display research results"""
        logger.info(f"  Summary: {data.get('summary', 'N/A')[:200]}...")
        logger.info(f"  Key Findings: {len(data.get('key_findings', []))}")
        logger.info(f"  Hashtags Found: {len(data.get('recommended_hashtags', []))}")
        
        # Sample hashtags
        hashtags = data.get('recommended_hashtags', [])[:10]
        if hashtags:
            logger.info(f"  Sample Hashtags: {', '.join(hashtags)}")
    
    def _display_planning_results(self, data: Dict[str, Any]):
        """Display planning results"""
        campaigns = data.get('campaigns', [])
        logger.info(f"  Campaigns Created: {len(campaigns)}")
        logger.info(f"  Total Budget: ${data.get('total_budget_allocated', 0):,.2f}")
        
        for campaign in campaigns[:2]:  # Show first 2 campaigns
            logger.info(f"  - {campaign.get('name', 'N/A')}: {campaign.get('objective', 'N/A')}")
            ad_sets = campaign.get('ad_sets', [])
            logger.info(f"    Ad Sets: {len(ad_sets)}")
    
    def _display_content_results(self, data: Dict[str, Any]):
        """Display content creation results"""
        logger.info(f"  Posts Created: {data.get('posts_created', 0)}")
        
        posts = data.get('posts', [])
        for i, post in enumerate(posts[:3], 1):  # Show first 3 posts
            logger.info(f"  Post {i}: {post.get('post_type', 'N/A')}")
            logger.info(f"    Caption: {post.get('text_content', '')[:100]}...")
    
    async def _save_test_results(self, workflow_type: str, results: Dict[str, Any]):
        """Save test results to file"""
        output_dir = Path("test_outputs")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{workflow_type}_{timestamp}.json"
        filepath = output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"  💾 Results saved to: {filepath}")
    
    async def run_all_workflows(self):
        """Run tests for all available workflows"""
        workflows_to_test = [
            "research-only",
            "planning-only",
            "research-then-planning",
            "full-campaign"
        ]
        
        logger.info("\n" + "="*80)
        logger.info("TESTING ALL WORKFLOWS")
        logger.info("="*80)
        
        success_count = 0
        failure_count = 0
        
        for workflow in workflows_to_test:
            success = await self.test_workflow(workflow)
            if success:
                success_count += 1
            else:
                failure_count += 1
            
            # Brief pause between workflows
            await asyncio.sleep(2)
        
        # Display summary
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Total Workflows Tested: {len(workflows_to_test)}")
        logger.info(f"✅ Successful: {success_count}")
        logger.info(f"❌ Failed: {failure_count}")
        
        # Display individual results
        for workflow, result in self.test_results.items():
            status = "✅" if result["success"] else "❌"
            logger.info(f"{status} {workflow}")
        
        return failure_count == 0


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Test orchestrated workflows"
    )
    parser.add_argument(
        "workflow",
        nargs="?",
        default="all",
        choices=[
            "research-only",
            "planning-only", 
            "research-then-planning",
            "planning-then-content",
            "full-campaign",
            "all"
        ],
        help="Workflow to test (default: all)"
    )
    parser.add_argument(
        "--initiative-id",
        default=TEST_INITIATIVE_ID,
        help="Initiative ID to use for testing"
    )
    
    args = parser.parse_args()
    
    # Verify environment
    required_env = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "OPENAI_API_KEY"]
    missing_env = [var for var in required_env if not os.getenv(var)]
    
    if missing_env:
        logger.error(f"Missing required environment variables: {', '.join(missing_env)}")
        sys.exit(1)
    
    # Initialize tester
    tester = WorkflowTester(args.initiative_id)
    
    logger.info("\n" + "="*80)
    logger.info("CAMPAIGN MANAGEMENT PLATFORM")
    logger.info("Orchestrated Workflow Test Suite")
    logger.info("="*80)
    logger.info(f"Initiative ID: {args.initiative_id}")
    
    # Run tests
    if args.workflow == "all":
        success = await tester.run_all_workflows()
    else:
        success = await tester.test_workflow(args.workflow)
    
    if success:
        logger.info("\n✅ All tests passed!")
        sys.exit(0)
    else:
        logger.error("\n❌ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())