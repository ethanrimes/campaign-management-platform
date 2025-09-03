# # tests/test_orchestrator.py

# import pytest
# import asyncio
# from unittest.mock import Mock, patch, AsyncMock
# from agents.orchestrator.agent import OrchestratorAgent, AgentConfig
# from backend.config.database import SupabaseClient
# import uuid


# @pytest.fixture
# def agent_config():
#     """Create test agent configuration"""
#     return AgentConfig(
#         name="Test Orchestrator",
#         description="Test orchestrator agent",
#         tenant_id=str(uuid.uuid4()),
#         initiative_id=str(uuid.uuid4()),
#         model_provider="openai"
#     )


# @pytest.fixture
# def mock_supabase():
#     """Mock Supabase client"""
#     with patch('agents.orchestrator.agent.SupabaseClient') as mock:
#         client = AsyncMock()
#         mock.return_value = client
#         yield client


# @pytest.mark.asyncio
# async def test_orchestrator_initialization(agent_config):
#     """Test orchestrator agent initialization"""
#     with patch('agents.orchestrator.agent.OrchestratorAgent._initialize_client'):
#         agent = OrchestratorAgent(agent_config)
        
#         assert agent.config.name == "Test Orchestrator"
#         assert agent.config.tenant_id == agent_config.tenant_id
#         assert agent.config.initiative_id == agent_config.initiative_id


# @pytest.mark.asyncio
# async def test_orchestrator_budget_validation(agent_config, mock_supabase):
#     """Test budget validation in orchestrator"""
#     with patch('agents.orchestrator.agent.OrchestratorAgent._initialize_client'):
#         agent = OrchestratorAgent(agent_config)
        
#         # Test plan with valid budget
#         valid_plan = {
#             "campaigns": [
#                 {
#                     "name": "Test Campaign",
#                     "objective": "AWARENESS",
#                     "budget": {"lifetime": 500}
#                 }
#             ]
#         }
        
#         budget_info = {"total": 1000}
#         validated = agent._validate_campaign_plan(valid_plan, budget_info)
        
#         assert validated["total_budget_allocated"] == 500
        
#         # Test plan exceeding budget
#         over_budget_plan = {
#             "campaigns": [
#                 {
#                     "name": "Test Campaign",
#                     "objective": "AWARENESS",
#                     "budget": {"lifetime": 2000}
#                 }
#             ]
#         }
        
#         validated = agent._validate_campaign_plan(over_budget_plan, budget_info)
#         assert validated["total_budget_allocated"] == 1000
#         assert validated["campaigns"][0]["budget"]["lifetime"] == 1000


# @pytest.mark.asyncio
# async def test_orchestrator_hierarchy_building(agent_config):
#     """Test campaign hierarchy building"""
#     with patch('agents.orchestrator.agent.OrchestratorAgent._initialize_client'):
#         agent = OrchestratorAgent(agent_config)
        
#         plan = {
#             "campaigns": [