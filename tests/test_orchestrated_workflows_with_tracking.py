#!/usr/bin/env python3
# tests/test_orchestrated_workflows_with_tracking.py

"""
Test script for orchestrated workflows with execution tracking.
Now includes visibility for the entire execution trace.

Usage:
    python tests/test_orchestrated_workflows_with_tracking.py [workflow_type]
    
    workflow_type options:
        - research-only
        - planning-only
        - content-creation-only
        - research-then-planning
        - planning-then-content
        - full-campaign
        - all (runs all workflows)
        - trace <execution_id> (trace a specific execution)
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import argparse
import logging
from uuid import UUID
from typing import List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import logging config first
from backend.config.logging_config import LoggingConfig

# Setup logging before other imports
LoggingConfig.setup_test_logging()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

from agents.orchestrator.agent import OrchestratorAgent, WorkflowType
from agents.base.agent import AgentConfig
from backend.db.supabase_client import DatabaseClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test configuration - REPLACE WITH YOUR ACTUAL INITIATIVE ID
TEST_INITIATIVE_ID = "bf2d9675-b236-4a86-8514-78b0b6d75a53"


class ExecutionTracer:
    """Trace and display execution details"""
    
    def __init__(self, initiative_id: str):
        self.initiative_id = initiative_id
        self.db_client = DatabaseClient(initiative_id=initiative_id)
    
    async def trace_execution(self, execution_id: str) -> Dict[str, Any]:
        """Trace all entities created by a specific execution"""
        logger.info("\n" + "="*80)
        logger.info(f"EXECUTION TRACE: {execution_id}")
        logger.info("="*80)
        
        # Get execution log
        logs = await self.db_client.select(
            "execution_logs",
            filters={"execution_id": execution_id}
        )
        
        if not logs:
            logger.error(f"No execution found with ID: {execution_id}")
            return {}
        
        execution_log = logs[0]
        
        logger.info(f"\n📊 EXECUTION SUMMARY")
        logger.info(f"  Workflow Type: {execution_log.get('workflow_type')}")
        logger.info(f"  Status: {execution_log.get('status')}")
        logger.info(f"  Started: {execution_log.get('started_at')}")
        logger.info(f"  Completed: {execution_log.get('completed_at')}")
        
        # Calculate duration
        if execution_log.get('started_at') and execution_log.get('completed_at'):
            start = datetime.fromisoformat(execution_log['started_at'].replace('Z', '+00:00'))
            end = datetime.fromisoformat(execution_log['completed_at'].replace('Z', '+00:00'))
            duration = (end - start).total_seconds()
            logger.info(f"  Duration: {duration:.2f} seconds")
        
        logger.info(f"\n  Steps Completed: {', '.join(execution_log.get('steps_completed', []))}")
        if execution_log.get('steps_failed'):
            logger.warning(f"  Steps Failed: {', '.join(execution_log['steps_failed'])}")
        
        # Trace entities
        trace_results = {}
        
        # Research entries
        research = await self.db_client.select(
            "research",
            filters={"execution_id": execution_id}
        )
        trace_results['research'] = research
        logger.info(f"\n🔬 RESEARCH: {len(research)} entries")
        for r in research[:3]:
            logger.info(f"  - {r.get('topic', 'N/A')}: {r.get('summary', '')[:100]}...")
            if r.get('recommended_hashtags'):
                logger.info(f"    Hashtags: {len(r.get('recommended_hashtags', []))} found")
        
        # Campaigns
        campaigns = await self.db_client.select(
            "campaigns",
            filters={"execution_id": execution_id}
        )
        trace_results['campaigns'] = campaigns
        logger.info(f"\n📅 CAMPAIGNS: {len(campaigns)} created")
        for c in campaigns:
            logger.info(f"  - {c.get('name', 'N/A')}")
            logger.info(f"    Objective: {c.get('objective', 'N/A')}")
            budget = c.get('lifetime_budget')
            if budget is not None:
                logger.info(f"    Budget: ${budget:,.2f}")
            else:
                logger.info(f"    Budget: Not specified")
        
        # Ad Sets
        ad_sets = await self.db_client.select(
            "ad_sets",
            filters={"execution_id": execution_id}
        )
        trace_results['ad_sets'] = ad_sets
        logger.info(f"\n🎯 AD SETS: {len(ad_sets)} created")
        for a in ad_sets[:5]:
            logger.info(f"  - {a.get('name', 'N/A')}")
            logger.info(f"    Campaign: {a.get('campaign_id', 'N/A')}")
            if a.get('target_audience'):
                audience = a['target_audience']
                logger.info(f"    Audience: {audience.get('age_range', [])} | {', '.join(audience.get('locations', []))}")
        
        # Posts
        posts = await self.db_client.select(
            "posts",
            filters={"execution_id": execution_id}
        )
        trace_results['posts'] = posts
        logger.info(f"\n📝 POSTS: {len(posts)} created")
        for p in posts[:5]:
            logger.info(f"  - Type: {p.get('post_type', 'N/A')}")
            logger.info(f"    Caption: {p.get('text_content', '')[:80]}...")
            if p.get('hashtags'):
                logger.info(f"    Hashtags: {', '.join(p['hashtags'][:5])}")
        
        # Media Files
        media_files = await self.db_client.select(
            "media_files",
            filters={"execution_id": execution_id}
        )
        trace_results['media_files'] = media_files
        logger.info(f"\n🖼️ MEDIA FILES: {len(media_files)} created")
        for m in media_files[:3]:
            logger.info(f"  - Type: {m.get('file_type', 'N/A')}")
            logger.info(f"    URL: {m.get('public_url', 'N/A')}")
        
        # Summary
        logger.info(f"\n" + "="*80)
        logger.info(f"EXECUTION TRACE COMPLETE")
        logger.info(f"Total Entities Created:")
        logger.info(f"  - Research: {len(research)}")
        logger.info(f"  - Campaigns: {len(campaigns)}")
        logger.info(f"  - Ad Sets: {len(ad_sets)}")
        logger.info(f"  - Posts: {len(posts)}")
        logger.info(f"  - Media Files: {len(media_files)}")
        logger.info("="*80)
        
        return trace_results
    
    async def list_recent_executions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent executions"""
        executions = await self.db_client.select(
            "execution_logs",
            limit=limit
        )
        
        logger.info(f"\n📋 RECENT EXECUTIONS (Last {limit})")
        logger.info("-" * 60)
        
        for exec in executions:
            status_icon = "✅" if exec.get('status') == 'completed' else "❌"
            logger.info(f"{status_icon} {exec.get('execution_id')}")
            logger.info(f"   Workflow: {exec.get('workflow_type')}")
            logger.info(f"   Started: {exec.get('started_at')}")
            logger.info(f"   Status: {exec.get('status')}")
            logger.info("")
        
        return executions


class WorkflowTester:
    """Test harness for orchestrated workflows with execution tracking"""
    
    def __init__(self, initiative_id: str):
        self.initiative_id = initiative_id
        self.test_results = {}
        self.execution_ids = []
        self.tracer = ExecutionTracer(initiative_id)
        self.db_client = DatabaseClient(initiative_id=initiative_id)
        
    async def test_workflow(self, workflow_type: WorkflowType) -> bool:
        """
        Test a specific workflow with execution tracking
        
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
            
            # Store execution ID for tracing
            execution_id = orchestrator.execution_id
            self.execution_ids.append(execution_id)
            
            logger.info(f"🔑 Execution ID: {execution_id}")
            
            # Prepare input based on workflow type
            input_data = await self._get_workflow_input(workflow_type)
            
            logger.info(f"\n📋 Input for {workflow_type}:")
            logger.info(json.dumps(input_data, indent=2, default=str))
            
            # Execute workflow
            logger.info(f"\n🚀 Executing {workflow_type} workflow...")
            result = await orchestrator.execute(input_data)
            
            # Process result
            if result.success:
                logger.info(f"\n✅ {workflow_type} workflow completed successfully")
                logger.info(f"   Execution ID: {execution_id}")
                
                self._display_workflow_results(workflow_type, result.data)
                self.test_results[workflow_type] = {
                    "success": True,
                    "execution_id": execution_id,
                    "data": result.data
                }
                
                # Save results to file
                await self._save_test_results(workflow_type, result.data, execution_id)
                
                # Trace the execution
                logger.info(f"\n🔍 Tracing execution {execution_id}...")
                await self.tracer.trace_execution(execution_id)
                
                return True
            else:
                logger.error(f"\n❌ {workflow_type} workflow failed")
                logger.error(f"Errors: {result.errors}")
                self.test_results[workflow_type] = {
                    "success": False,
                    "execution_id": execution_id,
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
    
    async def _get_workflow_input(self, workflow_type: WorkflowType) -> Dict[str, Any]:
        """Get appropriate input data for the workflow type"""
        base_input = {
            "trigger": "test",
            "test_mode": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Special handling for content-creation-only
        if workflow_type == "content-creation-only":
            logger.info("Loading existing campaigns for content creation...")
            
            # Fetch existing campaigns from database
            campaigns = await self.db_client.select(
                "campaigns",
                filters={"is_active": True},
                limit=5  # Limit to recent campaigns
            )
            
            if not campaigns:
                logger.warning("No existing campaigns found. Creating mock campaign structure...")
                # Create a mock campaign structure for testing
                campaigns = [{
                    "id": "mock-campaign-id",
                    "name": "Test Campaign for Content Creation",
                    "objective": "ENGAGEMENT",
                    "ad_sets": []
                }]
            
            # Fetch ad_sets for each campaign
            for campaign in campaigns:
                ad_sets = await self.db_client.select(
                    "ad_sets",
                    filters={"campaign_id": campaign["id"], "is_active": True}
                )
                
                if not ad_sets and campaign["id"] == "mock-campaign-id":
                    # Create mock ad_sets for testing
                    ad_sets = [{
                        "id": "mock-ad-set-id",
                        "name": "Test Ad Set",
                        "creative_brief": {
                            "theme": "Test Theme",
                            "tone": "professional",
                            "format_preferences": ["image", "video"]
                        },
                        "materials": {
                            "links": ["https://example.com"],
                            "hashtags": ["#test", "#content"],
                            "brand_assets": []
                        },
                        "post_frequency": 3,
                        "post_volume": 2
                    }]
                
                campaign["ad_sets"] = ad_sets
            
            base_input["campaigns"] = campaigns
            base_input["content_volume"] = 3
            base_input["content_types"] = ["image", "video", "carousel"]
            
            logger.info(f"Loaded {len(campaigns)} campaigns with ad_sets for content creation")
        
        # Customize input based on other workflow types
        elif workflow_type in ["planning-only", "research-then-planning", "full-campaign"]:
            base_input.update({
                "planning_window_days": 30,
                "force_new_campaigns": False,
                "budget_override": None
            })
        
        if workflow_type in ["planning-then-content", "full-campaign"]:
            base_input.update({
                "content_volume": 3,
                "content_types": ["image", "video", "carousel"]
            })
        
        if workflow_type in ["research-only", "research-then-planning", "full-campaign"]:
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
        logger.info(f"Execution ID: {results.get('execution_id', 'N/A')}")
        logger.info(f"Steps Completed: {', '.join(metadata.get('steps_completed', []))}")
        
        if metadata.get("steps_failed"):
            logger.warning(f"Steps Failed: {', '.join(metadata['steps_failed'])}")
    
    async def _save_test_results(self, workflow_type: str, results: Dict[str, Any], execution_id: str):
        """Save test results to file"""
        output_dir = Path("test_outputs")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{workflow_type}_{execution_id[:8]}_{timestamp}.json"
        filepath = output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"  💾 Results saved to: {filepath}")
    
    async def run_all_workflows(self):
        """Run tests for all available workflows"""
        workflows_to_test = [
            "research-only",
            "planning-only",
            "content-creation-only",  # Added
            "research-then-planning",
            "planning-then-content",
            "full-campaign"
        ]
        
        logger.info("\n" + "="*80)
        logger.info("TESTING ALL WORKFLOWS WITH EXECUTION TRACKING")
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
        
        # Display execution IDs
        logger.info(f"\n🔑 Execution IDs Generated:")
        for workflow, result in self.test_results.items():
            if 'execution_id' in result:
                status = "✅" if result["success"] else "❌"
                logger.info(f"{status} {workflow}: {result['execution_id']}")
        
        # List all recent executions
        logger.info("\n" + "="*80)
        await self.tracer.list_recent_executions()
        
        return failure_count == 0


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Test orchestrated workflows with execution tracking"
    )
    parser.add_argument(
        "workflow",
        nargs="?",
        default="all",
        choices=[
            "research-only",
            "planning-only",
            "content-creation-only",  # Added
            "research-then-planning",
            "planning-then-content",
            "full-campaign",
            "all",
            "trace",
            "list"
        ],
        help="Workflow to test or action to perform (default: all)"
    )
    parser.add_argument(
        "--initiative-id",
        default=TEST_INITIATIVE_ID,
        help="Initiative ID to use for testing"
    )
    parser.add_argument(
        "--execution-id",
        help="Execution ID to trace (use with 'trace' command)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of recent executions to list (use with 'list' command)"
    )
    
    args = parser.parse_args()
    
    # Verify environment
    required_env = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "OPENAI_API_KEY"]
    missing_env = [var for var in required_env if not os.getenv(var)]
    
    if missing_env:
        logger.error(f"Missing required environment variables: {', '.join(missing_env)}")
        sys.exit(1)
    
    # Initialize tracer for trace/list operations
    if args.workflow in ["trace", "list"]:
        tracer = ExecutionTracer(args.initiative_id)
        
        if args.workflow == "trace":
            if not args.execution_id:
                logger.error("--execution-id required for trace command")
                sys.exit(1)
            await tracer.trace_execution(args.execution_id)
        
        elif args.workflow == "list":
            await tracer.list_recent_executions(args.limit)
        
        sys.exit(0)
    
    # Initialize tester for workflow testing
    tester = WorkflowTester(args.initiative_id)
    
    logger.info("\n" + "="*80)
    logger.info("CAMPAIGN MANAGEMENT PLATFORM")
    logger.info("Orchestrated Workflow Test Suite with Execution Tracking")
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