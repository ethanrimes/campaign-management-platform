# tests/test_research_agent.py

#!/usr/bin/env python3
"""
Direct test script for the Research Agent.
Tests the agent's ability to fetch initiative data, generate queries,
perform searches, and filter results.

Usage:
    python tests/test_research_agent.py
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.researcher.agent import ResearchAgent
from agents.base.agent import AgentConfig

# Load environment variables
load_dotenv()

# Test configuration - REPLACE WITH YOUR ACTUAL INITIATIVE ID
TEST_INITIATIVE_ID = "bf2d9675-b236-4a86-8514-78b0b6d75a53"


async def test_research_agent():
    """Test the research agent with a real initiative"""
    
    print("\n" + "=" * 80)
    print("RESEARCH AGENT TEST")
    print("=" * 80)
    print(f"\nTesting with Initiative ID: {TEST_INITIATIVE_ID}")
    print("This test will:")
    print("1. Fetch initiative data from database")
    print("2. Generate search queries")
    print("3. Execute searches via Perplexity")
    print("4. Filter and store results")
    print("-" * 80)
    
    # Verify environment variables
    required_env = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "PERPLEXITY_API_KEY", "OPENAI_API_KEY"]
    missing_env = [var for var in required_env if not os.getenv(var)]
    
    if missing_env:
        logger.error(f"Missing required environment variables: {', '.join(missing_env)}")
        logger.error("Please ensure your .env file contains all required variables")
        return False
    
    try:
        # Create agent configuration
        config = AgentConfig(
            name="Research Agent Test",
            description="Testing research agent functionality",
            initiative_id=TEST_INITIATIVE_ID,
            model_provider="openai",
            verbose=True
        )
        
        logger.info("\n🚀 Initializing Research Agent...")
        agent = ResearchAgent(config)
        
        logger.info("✓ Agent initialized successfully")
        
        # Execute research
        logger.info("\n🔬 Executing research workflow...")
        
        result = await agent.execute({
            "trigger": "test",
            "test_mode": True
        })
        
        # Check if execution was successful
        if result.success:
            logger.info("\n" + "=" * 80)
            logger.info("✅ RESEARCH COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            
            # Display results
            research_data = result.data
            
            print("\n📋 RESEARCH RESULTS SUMMARY")
            print("-" * 40)
            print(f"Summary: {research_data.get('summary', 'N/A')[:200]}...")
            print(f"\nTotal Results Analyzed: {research_data.get('total_results_analyzed', 0)}")
            print(f"Relevant Results Found: {research_data.get('relevant_results_found', 0)}")
            
            # Display key findings
            print("\n🔍 KEY FINDINGS:")
            print("-" * 40)
            findings = research_data.get("key_findings", [])
            for i, finding in enumerate(findings[:5], 1):
                print(f"\n{i}. Topic: {finding.get('topic', 'N/A')}")
                print(f"   Finding: {finding.get('finding', '')[:150]}...")
                print(f"   Source: {finding.get('source', 'N/A')}")
                print(f"   Relevance: {finding.get('relevance_score', 0):.2f}")
            
            # Display content opportunities
            print("\n💡 CONTENT OPPORTUNITIES:")
            print("-" * 40)
            opportunities = research_data.get("content_opportunities", [])
            for opp in opportunities:
                print(f"- {opp.get('description', 'N/A')} (Priority: {opp.get('priority', 'N/A')})")
            
            # Display hashtags
            print("\n#️⃣ RECOMMENDED HASHTAGS:")
            print("-" * 40)
            hashtags = research_data.get("recommended_hashtags", [])
            if hashtags:
                print(", ".join(hashtags[:15]))
            else:
                print("No hashtags found")
            
            # Save full output to file
            output_dir = Path("test_outputs")
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"research_output_{timestamp}.json"
            
            with open(output_file, "w") as f:
                json.dump(research_data, f, indent=2, default=str)
            
            print(f"\n💾 Full output saved to: {output_file}")
            
            # Display metadata
            print("\n📊 EXECUTION METADATA:")
            print("-" * 40)
            print(f"Agent ID: {result.metadata.get('agent_id', 'N/A')}")
            print(f"Timestamp: {result.timestamp}")
            print(f"Success: {result.success}")
            
            return True
            
        else:
            logger.error("\n" + "=" * 80)
            logger.error("❌ RESEARCH FAILED")
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
    print("Research Agent Test Suite")
    print("=" * 80)
    
    # Run the test
    success = await test_research_agent()
    
    if success:
        print("\n✅ All tests passed successfully!")
    else:
        print("\n❌ Tests failed. Check the logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    # Note: Update TEST_INITIATIVE_ID with an actual initiative ID from your database
    print(f"\n⚠️  Note: Using Initiative ID: {TEST_INITIATIVE_ID}")
    print("If this ID doesn't exist in your database, the test will fail.")
    print("Update TEST_INITIATIVE_ID in this script with a valid initiative ID.\n")
    
    asyncio.run(main())