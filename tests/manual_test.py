#!/usr/bin/env python3
# tests/manual_test.py

"""
Manual test script to test individual agents with predefined inputs.
Usage: python tests/manual_test.py [orchestrator|researcher|content_creator|all]
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.orchestrator.agent import OrchestratorAgent
from agents.researcher.agent import ResearchAgent
from agents.content_creator.agent import ContentCreatorAgent
from agents.base.agent import AgentConfig


# Test configurations
TEST_TENANT_ID = "9c7ff6ae-5f41-40bf-97a9-c56f337c3186"
TEST_INITIATIVE_ID = "ce2ea2b3-ae0e-4082-9d5a-43c645912b04"

async def test_orchestrator():
    """Test the Orchestrator Agent"""
    print("\n" + "="*60)
    print("TESTING ORCHESTRATOR AGENT")
    print("="*60)
    
    config = AgentConfig(
        name="Test Orchestrator",
        description="Campaign planning and budget allocation",
        tenant_id=TEST_TENANT_ID,
        initiative_id=TEST_INITIATIVE_ID,
        model_provider="openai",
        verbose=True
    )
    
    # Create test input
    test_input = {
        "trigger": "manual_test",
        "context": {
            "objective": "Increase brand awareness",
            "budget_available": 5000,
            "duration_days": 30
        }
    }
    
    print(f"\nInput: {json.dumps(test_input, indent=2)}")
    
    try:
        agent = OrchestratorAgent(config)
        result = await agent.execute(test_input)
        
        print(f"\nSuccess: {result.success}")
        
        if result.success:
            print("\nOutput Summary:")
            print(f"- Campaigns created: {len(result.data.get('campaigns', []))}")
            print(f"- Total budget allocated: ${result.data.get('total_budget_allocated', 0)}")
            print(f"- Optimization strategy: {result.data.get('optimization_strategy', {}).get('primary_metric', 'N/A')}")
            
            # Print campaign details
            for campaign in result.data.get('campaigns', []):
                print(f"\nCampaign: {campaign.get('name')}")
                print(f"  - Objective: {campaign.get('objective')}")
                print(f"  - Budget: ${campaign.get('budget', {}).get('lifetime', 0)}")
                print(f"  - Ad Sets: {len(campaign.get('ad_sets', []))}")
                
                for ad_set in campaign.get('ad_sets', []):
                    print(f"    - {ad_set.get('name')}: ${ad_set.get('budget', {}).get('lifetime', 0)}")
        else:
            print(f"\nErrors: {result.errors}")
            
    except Exception as e:
        print(f"\nError testing orchestrator: {e}")
        import traceback
        traceback.print_exc()


async def test_researcher():
    """Test the Research Agent"""
    print("\n" + "="*60)
    print("TESTING RESEARCH AGENT")
    print("="*60)
    
    config = AgentConfig(
        name="Test Researcher",
        description="Market research and competitive analysis",
        tenant_id=TEST_TENANT_ID,
        initiative_id=TEST_INITIATIVE_ID,
        model_provider="openai"
    )
    
    # Create test input
    test_input = {
        "trigger": "manual_test",
        "research_focus": ["education technology", "online learning"],
        "competitor_analysis": True,
        "hashtag_research": True
    }
    
    print(f"\nInput: {json.dumps(test_input, indent=2)}")
    
    try:
        agent = ResearchAgent(config)
        result = await agent.execute(test_input)
        
        print(f"\nSuccess: {result.success}")
        
        if result.success:
            print("\nResearch Summary:")
            print(f"- Summary: {result.data.get('summary', 'N/A')[:200]}...")
            print(f"- Key findings: {len(result.data.get('key_findings', []))}")
            print(f"- Hashtags found: {len(result.data.get('recommended_hashtags', []))}")
            print(f"- Competitor insights: {len(result.data.get('competitor_insights', []))}")
            
            # Print sample findings
            findings = result.data.get('key_findings', [])
            if findings:
                print("\nSample Key Findings:")
                for finding in findings[:3]:
                    print(f"  - {finding.get('topic', 'N/A')}: {finding.get('finding', '')[:100]}...")
            
            # Print sample hashtags
            hashtags = result.data.get('recommended_hashtags', [])
            if hashtags:
                print(f"\nSample Hashtags: {', '.join(hashtags[:10])}")
                
        else:
            print(f"\nErrors: {result.errors}")
            
    except Exception as e:
        print(f"\nError testing researcher: {e}")
        import traceback
        traceback.print_exc()


async def test_content_creator():
    """Test the Content Creator Agent"""
    print("\n" + "="*60)
    print("TESTING CONTENT CREATOR AGENT")
    print("="*60)
    
    config = AgentConfig(
        name="Test Content Creator",
        description="Content generation for social media",
        tenant_id=TEST_TENANT_ID,
        initiative_id=TEST_INITIATIVE_ID,
        model_provider="openai"
    )
    
    # Create test input with ad set data
    test_input = {
        "ad_set_id": str(uuid.uuid4()),
        "ad_set_data": {
            "name": "Tech Education Campaign",
            "creative_brief": {
                "theme": "Innovation in Education",
                "tone": "inspiring",
                "target_audience": "Educators and students",
                "key_messages": [
                    "Technology transforms learning",
                    "Accessible education for all"
                ]
            },
            "materials": {
                "links": ["https://example.com/learn"],
                "hashtags": ["#EdTech", "#Innovation", "#Learning"],
                "brand_assets": []
            },
            "post_volume": 3,
            "post_frequency": 5
        }
    }
    
    print(f"\nInput: {json.dumps(test_input, indent=2)}")
    
    try:
        agent = ContentCreatorAgent(config)
        result = await agent.execute(test_input)
        
        print(f"\nSuccess: {result.success}")
        
        if result.success:
            print("\nContent Generation Summary:")
            print(f"- Posts created: {result.data.get('posts_created', 0)}")
            
            # Print post details
            posts = result.data.get('posts', [])
            for i, post in enumerate(posts, 1):
                print(f"\nPost {i}:")
                print(f"  Type: {post.get('post_type')}")
                print(f"  Caption: {post.get('text_content', '')[:100]}...")
                print(f"  Hashtags: {', '.join(post.get('hashtags', [])[:5])}")
                print(f"  Scheduled: {post.get('scheduled_time', 'Not scheduled')}")
                print(f"  Media: {post.get('media_description', 'No media description')}")
                
        else:
            print(f"\nErrors: {result.errors}")
            
    except Exception as e:
        print(f"\nError testing content creator: {e}")
        import traceback
        traceback.print_exc()


async def test_all_agents():
    """Test all agents in sequence"""
    print("\n" + "="*60)
    print("TESTING ALL AGENTS IN SEQUENCE")
    print("="*60)
    
    # Test in logical order
    await test_researcher()
    await asyncio.sleep(1)  # Brief pause between tests
    
    await test_orchestrator()
    await asyncio.sleep(1)
    
    await test_content_creator()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)


async def main():
    """Main entry point"""
    # Check environment variables
    required_vars = [
        "OPENAI_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "SUPABASE_SERVICE_KEY"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing environment variables: {', '.join(missing_vars)}")
        print("Please copy .env.example to .env and fill in your credentials")
        sys.exit(1)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "orchestrator":
            await test_orchestrator()
        elif command == "researcher":
            await test_researcher()
        elif command == "content_creator":
            await test_content_creator()
        elif command == "all":
            await test_all_agents()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python tests/manual_test.py [orchestrator|researcher|content_creator|all]")
            sys.exit(1)
    else:
        # Default to testing all
        await test_all_agents()


if __name__ == "__main__":
    print("Campaign Management Platform - Manual Test Suite")
    print("=" * 60)
    asyncio.run(main())