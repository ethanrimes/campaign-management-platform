#!/usr/bin/env python3
# tests/test_orchestrator_agent.py

"""
Direct test script for the Orchestrator Agent.
Tests the agent's ability to fetch initiative data, plan campaigns,
allocate budgets, create ad sets, and save the hierarchy.

Usage:
    python tests/test_orchestrator_agent.py
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
from typing import Dict, Any
import uuid

# Setup logging with detailed formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.orchestrator.agent import OrchestratorAgent
from agents.base.agent import AgentConfig
from backend.db.supabase_client import DatabaseClient

# Load environment variables
load_dotenv()

# Test configuration - REPLACE WITH YOUR ACTUAL INITIATIVE ID
TEST_INITIATIVE_ID = "bf2d9675-b236-4a86-8514-78b0b6d75a53"


def print_campaign_hierarchy(campaigns: list):
    """Pretty print campaign hierarchy with indentation"""
    for campaign in campaigns:
        print(f"\n📊 CAMPAIGN: {campaign.get('name', 'Unnamed')}")
        print(f"   ID: {campaign.get('id', 'N/A')}")
        print(f"   Objective: {campaign.get('objective', 'N/A')}")
        print(f"   Budget Mode: {campaign.get('budget_mode', 'N/A')}")
        
        budget = campaign.get('budget', {})
        print(f"   💰 Budget:")
        print(f"      Daily: ${budget.get('daily', 0):,.2f}")
        print(f"      Lifetime: ${budget.get('lifetime', 0):,.2f}")
        
        schedule = campaign.get('schedule', {})
        print(f"   📅 Schedule:")
        print(f"      Start: {schedule.get('start_date', 'N/A')}")
        print(f"      End: {schedule.get('end_date', 'N/A')}")
        
        ad_sets = campaign.get('ad_sets', [])
        print(f"   📦 Ad Sets ({len(ad_sets)}):")
        
        for ad_set in ad_sets:
            print(f"\n      🎯 AD SET: {ad_set.get('name', 'Unnamed')}")
            print(f"         ID: {ad_set.get('id', 'N/A')}")
            
            # Target audience
            audience = ad_set.get('target_audience', {})
            print(f"         👥 Target Audience:")
            print(f"            Age Range: {audience.get('age_range', [])}")
            print(f"            Locations: {', '.join(audience.get('locations', []))}")
            print(f"            Interests: {', '.join(audience.get('interests', [])[:3])}...")
            
            # Budget
            ad_budget = ad_set.get('budget', {})
            print(f"         💵 Budget:")
            print(f"            Daily: ${ad_budget.get('daily', 0):,.2f}")
            print(f"            Lifetime: ${ad_budget.get('lifetime', 0):,.2f}")
            
            # Creative brief
            brief = ad_set.get('creative_brief', {})
            print(f"         🎨 Creative Brief:")
            print(f"            Theme: {brief.get('theme', 'N/A')}")
            print(f"            Tone: {brief.get('tone', 'N/A')}")
            print(f"            Formats: {', '.join(brief.get('format_preferences', []))}")
            
            # Materials
            materials = ad_set.get('materials', {})
            print(f"         📎 Materials:")
            print(f"            Links: {len(materials.get('links', []))} provided")
            print(f"            Hashtags: {len(materials.get('hashtags', []))} provided")
            
            # Post strategy
            print(f"         📝 Post Strategy:")
            print(f"            Frequency: {ad_set.get('post_frequency', 0)} posts/week")
            print(f"            Volume: {ad_set.get('post_volume', 0)} total posts")


def print_budget_summary(output: Dict[str, Any]):
    """Print budget allocation summary"""
    print("\n" + "="*60)
    print("💰 BUDGET ALLOCATION SUMMARY")
    print("="*60)
    
    total_allocated = output.get('total_budget_allocated', 0)
    print(f"Total Budget Allocated: ${total_allocated:,.2f}")
    
    campaigns = output.get('campaigns', [])
    
    # Campaign level budgets
    print("\n📊 Campaign-Level Budgets:")
    campaign_total = 0
    for campaign in campaigns:
        budget = campaign.get('budget', {})
        lifetime = budget.get('lifetime', 0)
        campaign_total += lifetime
        print(f"   {campaign.get('name', 'Unnamed')}: ${lifetime:,.2f}")
    
    print(f"\nTotal (Campaigns): ${campaign_total:,.2f}")
    
    # Ad set level budgets
    print("\n🎯 Ad Set-Level Budgets:")
    ad_set_total = 0
    for campaign in campaigns:
        print(f"\n   Campaign: {campaign.get('name', 'Unnamed')}")
        for ad_set in campaign.get('ad_sets', []):
            budget = ad_set.get('budget', {})
            lifetime = budget.get('lifetime', 0)
            ad_set_total += lifetime
            print(f"      - {ad_set.get('name', 'Unnamed')}: ${lifetime:,.2f}")
    
    print(f"\nTotal (Ad Sets): ${ad_set_total:,.2f}")
    
    # Validation
    print("\n✅ Budget Validation:")
    if abs(campaign_total - total_allocated) < 0.01:
        print("   ✓ Campaign budgets match total allocation")
    else:
        print(f"   ✗ Budget mismatch: ${campaign_total:,.2f} vs ${total_allocated:,.2f}")


async def fetch_initiative_context(initiative_id: str) -> Dict[str, Any]:
    """Fetch initiative and related data for context"""
    logger.info("📊 Fetching initiative context...")
    
    try:
        db = DatabaseClient(initiative_id=initiative_id)
        
        # Get initiative
        initiatives = await db.select("initiatives", filters={"id": initiative_id})
        if not initiatives:
            raise ValueError(f"Initiative {initiative_id} not found")
        
        initiative = initiatives[0]
        logger.info(f"✓ Found initiative: {initiative.get('name', 'Unknown')}")
        
        # Get recent research
        research = await db.select(
            "research",
            filters={"initiative_id": initiative_id},
            limit=3
        )
        logger.info(f"✓ Found {len(research)} recent research entries")
        
        # Get active campaigns
        campaigns = await db.select(
            "campaigns",
            filters={
                "initiative_id": initiative_id,
                "is_active": True
            }
        )
        logger.info(f"✓ Found {len(campaigns)} active campaigns")
        
        return {
            "initiative": initiative,
            "research": research,
            "existing_campaigns": campaigns
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch context: {e}")
        raise


async def test_orchestrator_agent():
    """Test the orchestrator agent with a real initiative"""
    
    print("\n" + "=" * 80)
    print("ORCHESTRATOR AGENT TEST")
    print("=" * 80)
    print(f"\nTesting with Initiative ID: {TEST_INITIATIVE_ID}")
    print("This test will:")
    print("1. Fetch initiative data and context")
    print("2. Plan campaign structures")
    print("3. Allocate budgets across campaigns and ad sets")
    print("4. Generate creative briefs and targeting")
    print("5. Save the hierarchy to database")
    print("-" * 80)
    
    # Verify environment variables
    required_env = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "OPENAI_API_KEY"]
    missing_env = [var for var in required_env if not os.getenv(var)]
    
    if missing_env:
        logger.error(f"Missing required environment variables: {', '.join(missing_env)}")
        logger.error("Please ensure your .env file contains all required variables")
        return False
    
    try:
        # Fetch context first
        print("\n📁 FETCHING INITIATIVE CONTEXT")
        print("-" * 40)
        context = await fetch_initiative_context(TEST_INITIATIVE_ID)
        
        initiative = context["initiative"]
        print(f"Initiative: {initiative.get('name', 'Unknown')}")
        print(f"Category: {initiative.get('category', 'N/A')}")
        print(f"Optimization Metric: {initiative.get('optimization_metric', 'N/A')}")
        
        daily_budget = initiative.get('daily_budget', {}).get('amount', 100)
        total_budget = initiative.get('total_budget', {}).get('amount', 3000)
        print(f"Daily Budget: ${daily_budget:,.2f}")
        print(f"Total Budget: ${total_budget:,.2f}")
        
        # Create agent configuration
        config = AgentConfig(
            name="Orchestrator Agent Test",
            description="Testing campaign orchestration",
            initiative_id=TEST_INITIATIVE_ID,
            model_provider=initiative.get('model_provider', 'openai'),
            verbose=True
        )
        
        logger.info("\n🚀 Initializing Orchestrator Agent...")
        agent = OrchestratorAgent(config)
        logger.info("✓ Agent initialized successfully")
        
        # Prepare input
        input_data = {
            "trigger": "test",
            "test_mode": True,
            "planning_window_days": 30,
            "force_new_campaigns": True  # Create new campaigns even if some exist
        }
        
        print("\n📥 INPUT DATA:")
        print("-" * 40)
        print(json.dumps(input_data, indent=2))
        
        # Execute orchestration
        logger.info("\n🎯 Executing orchestration workflow...")
        print("-" * 40)
        
        result = await agent.execute(input_data)
        
        # Check if execution was successful
        if result.success:
            logger.info("\n" + "=" * 80)
            logger.info("✅ ORCHESTRATION COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            
            orchestration_output = result.data
            
            # Display campaign hierarchy
            print("\n📋 CAMPAIGN HIERARCHY")
            print("=" * 60)
            campaigns = orchestration_output.get('campaigns', [])
            print(f"Total Campaigns Created: {len(campaigns)}")
            
            print_campaign_hierarchy(campaigns)
            
            # Display budget summary
            print_budget_summary(orchestration_output)
            
            # Display optimization strategy
            print("\n🎯 OPTIMIZATION STRATEGY")
            print("=" * 60)
            strategy = orchestration_output.get('optimization_strategy', {})
            print(f"Primary Metric: {strategy.get('primary_metric', 'N/A')}")
            print(f"Secondary Metrics: {', '.join(strategy.get('secondary_metrics', []))}")
            print(f"Allocation Method: {strategy.get('allocation_method', 'N/A')}")
            print(f"Reasoning: {strategy.get('reasoning', 'N/A')}")
            
            # Display recommendations
            recommendations = orchestration_output.get('recommendations', [])
            if recommendations:
                print("\n💡 RECOMMENDATIONS")
                print("=" * 60)
                for i, rec in enumerate(recommendations, 1):
                    print(f"{i}. {rec}")
            
            # Save full output to file
            output_dir = Path("test_outputs")
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"orchestrator_output_{timestamp}.json"
            
            with open(output_file, "w") as f:
                json.dump(orchestration_output, f, indent=2, default=str)
            
            print(f"\n💾 Full output saved to: {output_file}")
            
            # Test saving to database (optional)
            save_to_db = input("\n💾 Save hierarchy to database? (yes/no): ").strip().lower()
            if save_to_db == 'yes':
                logger.info("Saving campaign hierarchy to database...")
                await agent.save_hierarchy(orchestration_output)
                logger.info("✓ Hierarchy saved successfully!")
            
            # Display execution metadata
            print("\n📊 EXECUTION METADATA")
            print("-" * 40)
            print(f"Agent ID: {result.metadata.get('agent_id', 'N/A')}")
            print(f"Timestamp: {result.timestamp}")
            print(f"Success: {result.success}")
            
            # Statistics
            print("\n📈 STATISTICS")
            print("-" * 40)
            total_ad_sets = sum(len(c.get('ad_sets', [])) for c in campaigns)
            print(f"Total Ad Sets: {total_ad_sets}")
            
            avg_ad_sets = total_ad_sets / len(campaigns) if campaigns else 0
            print(f"Average Ad Sets per Campaign: {avg_ad_sets:.1f}")
            
            total_posts = sum(
                ad_set.get('post_volume', 0)
                for campaign in campaigns
                for ad_set in campaign.get('ad_sets', [])
            )
            print(f"Total Posts to Create: {total_posts}")
            
            return True
            
        else:
            logger.error("\n" + "=" * 80)
            logger.error("❌ ORCHESTRATION FAILED")
            logger.error("=" * 80)
            logger.error(f"Errors: {', '.join(result.errors)}")
            return False
            
    except Exception as e:
        logger.error(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main entry point"""
    print("\n" + "=" * 80)
    print("CAMPAIGN MANAGEMENT PLATFORM")
    print("Orchestrator Agent Test Suite")
    print("=" * 80)
    
    # Run the test
    success = await test_orchestrator_agent()
    
    if success:
        print("\n✅ All tests passed successfully!")
        print("\n🎉 The orchestrator agent successfully:")
        print("   • Analyzed the initiative context")
        print("   • Created campaign structures")
        print("   • Allocated budgets optimally")
        print("   • Generated ad sets with targeting")
        print("   • Produced creative briefs")
    else:
        print("\n❌ Tests failed. Check the logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    # Note: Update TEST_INITIATIVE_ID with an actual initiative ID from your database
    print(f"\n⚠️  Note: Using Initiative ID: {TEST_INITIATIVE_ID}")
    print("If this ID doesn't exist in your database, the test will fail.")
    print("Update TEST_INITIATIVE_ID in this script with a valid initiative ID.\n")
    
    confirm = input("Continue with test? (yes/no): ").strip().lower()
    if confirm == 'yes':
        asyncio.run(main())
    else:
        print("Test cancelled.")