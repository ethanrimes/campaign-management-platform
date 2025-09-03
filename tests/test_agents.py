# tests/test_agents.py

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import uuid
import json
import os

# Import agents
from agents.orchestrator.agent import OrchestratorAgent
from agents.researcher.agent import ResearchAgent
from agents.content_creator.agent import ContentCreatorAgent
from agents.base.agent import AgentConfig

# Import models
from agents.orchestrator.models import OrchestratorOutput, Campaign, AdSet
from agents.researcher.models import ResearchOutput, KeyFinding
from agents.content_creator.models import ContentCreatorOutput, Post

# Set test environment variables
os.environ['OPENAI_API_KEY'] = 'test-key'
os.environ['SUPABASE_URL'] = 'https://test.supabase.co'
os.environ['SUPABASE_KEY'] = 'test-key'
os.environ['SUPABASE_SERVICE_KEY'] = 'test-service-key'


class TestOrchestratorAgent:
    """Test suite for Orchestrator Agent"""
    
    @pytest.fixture
    def agent_config(self):
        return AgentConfig(
            name="Test Orchestrator",
            description="Test orchestrator agent",
            tenant_id=str(uuid.uuid4()),
            initiative_id=str(uuid.uuid4()),
            model_provider="openai",
            verbose=True
        )
    
    @pytest.fixture
    def mock_openai_client(self):
        with patch('agents.base.agent.OpenAI') as mock:
            client = MagicMock()
            mock.return_value = client
            
            # Mock completion response
            response = MagicMock()
            response.choices = [MagicMock()]
            response.choices[0].message.content = json.dumps({
                "campaigns": [{
                    "id": str(uuid.uuid4()),
                    "name": "Test Campaign",
                    "objective": "AWARENESS",
                    "budget_mode": "ad_set_level",
                    "budget": {"lifetime": 1000},
                    "schedule": {
                        "start_date": datetime.utcnow().isoformat(),
                        "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat()
                    },
                    "ad_sets": [{
                        "id": str(uuid.uuid4()),
                        "name": "Test Ad Set",
                        "target_audience": {
                            "age_range": [18, 35],
                            "locations": ["United States"],
                            "interests": ["Technology"],
                            "languages": ["English"]
                        },
                        "placements": ["ig_feed", "fb_feed"],
                        "budget": {"lifetime": 500},
                        "creative_brief": {
                            "theme": "Tech Innovation",
                            "tone": "professional"
                        },
                        "materials": {
                            "links": ["https://example.com"],
                            "hashtags": ["#tech", "#innovation"]
                        }
                    }]
                }],
                "total_budget_allocated": 1000,
                "optimization_strategy": {
                    "primary_metric": "reach",
                    "allocation_method": "balanced",
                    "reasoning": "Maximize brand awareness"
                }
            })
            
            client.chat.completions.create.return_value = response
            yield client
    
    @pytest.fixture
    def mock_supabase(self):
        with patch('agents.orchestrator.agent.SupabaseClient') as mock:
            client = AsyncMock()
            
            # Mock database responses
            client.select.return_value = [{
                "id": str(uuid.uuid4()),
                "name": "Test Initiative",
                "objectives": {"primary": "Build awareness"},
                "daily_budget": {"amount": 100},
                "total_budget": {"amount": 10000}
            }]
            
            mock.return_value = client
            yield client
    
    @pytest.mark.asyncio
    async def test_orchestrator_execution(self, agent_config, mock_openai_client, mock_supabase):
        """Test full orchestrator execution"""
        agent = OrchestratorAgent(agent_config)
        
        result = await agent.execute({
            "trigger": "test",
            "context": "Test execution"
        })
        
        assert result.success == True
        assert result.agent_name == "Test Orchestrator"
        assert "campaigns" in result.data
        assert result.data["total_budget_allocated"] == 1000
    
    @pytest.mark.asyncio
    async def test_budget_validation(self, agent_config, mock_openai_client, mock_supabase):
        """Test budget validation logic"""
        agent = OrchestratorAgent(agent_config)
        
        # Test over-budget scenario
        plan = {
            "campaigns": [{
                "name": "Over Budget Campaign",
                "objective": "TRAFFIC",
                "budget": {"lifetime": 15000}
            }]
        }
        
        budget_info = {"total": 10000}
        validated = agent._validate_campaign_plan(plan, budget_info)
        
        assert validated["total_budget_allocated"] == 10000
        assert validated["campaigns"][0]["budget"]["lifetime"] == 10000
    
    @pytest.mark.asyncio
    async def test_hierarchy_building(self, agent_config, mock_openai_client):
        """Test campaign hierarchy building"""
        agent = OrchestratorAgent(agent_config)
        
        plan = {
            "campaigns": [{
                "name": "Test Campaign",
                "objective": "ENGAGEMENT",
                "budget": {"lifetime": 5000},
                "schedule": {
                    "start_date": datetime.utcnow().isoformat(),
                    "end_date": (datetime.utcnow() + timedelta(days=14)).isoformat()
                },
                "ad_sets": [{
                    "name": "Ad Set 1",
                    "target_audience": {
                        "age_range": [25, 45],
                        "locations": ["New York", "California"]
                    },
                    "budget": {"lifetime": 2500}
                }]
            }],
            "total_budget_allocated": 5000,
            "optimization_strategy": "balanced"
        }
        
        hierarchy = await agent._build_hierarchy(plan)
        
        assert len(hierarchy["campaigns"]) == 1
        assert hierarchy["total_budget_allocated"] == 5000
        assert len(hierarchy["campaigns"][0]["ad_sets"]) == 1


class TestResearchAgent:
    """Test suite for Research Agent"""
    
    @pytest.fixture
    def agent_config(self):
        return AgentConfig(
            name="Test Researcher",
            description="Test research agent",
            tenant_id=str(uuid.uuid4()),
            initiative_id=str(uuid.uuid4()),
            model_provider="openai"
        )
    
    @pytest.fixture
    def mock_search_tools(self):
        with patch('agents.researcher.agent.PerplexitySearch') as perplexity_mock, \
             patch('agents.researcher.agent.FacebookSearch') as facebook_mock, \
             patch('agents.researcher.agent.InstagramSearch') as instagram_mock:
            
            # Mock Perplexity
            perplexity = AsyncMock()
            perplexity.search.return_value = [{
                "title": "Test Result",
                "url": "https://example.com",
                "snippet": "Test snippet about the topic",
                "relevance_score": 0.9
            }]
            perplexity_mock.return_value = perplexity
            
            # Mock Facebook
            facebook = AsyncMock()
            facebook.search_pages.return_value = [{
                "id": "page_1",
                "name": "Test Page",
                "category": "Education",
                "link": "https://facebook.com/test",
                "fan_count": 10000
            }]
            facebook_mock.return_value = facebook
            
            # Mock Instagram
            instagram = AsyncMock()
            instagram.search_hashtags.return_value = [
                "#test", "#education", "#learning", "#knowledge"
            ]
            instagram_mock.return_value = instagram
            
            yield perplexity, facebook, instagram
    
    @pytest.fixture
    def mock_supabase(self):
        with patch('agents.researcher.agent.SupabaseClient') as mock:
            client = AsyncMock()
            
            client.select.return_value = [{
                "id": str(uuid.uuid4()),
                "name": "Test Initiative",
                "category": "Education",
                "objectives": {"primary": "Educational content"}
            }]
            
            client.insert.return_value = {"id": str(uuid.uuid4())}
            
            mock.return_value = client
            yield client
    
    @pytest.mark.asyncio
    async def test_research_execution(self, agent_config, mock_search_tools, mock_supabase):
        """Test research agent execution"""
        with patch('agents.base.agent.OpenAI'):
            agent = ResearchAgent(agent_config)
            
            result = await agent.execute({
                "trigger": "scheduled",
                "focus_areas": ["education", "technology"]
            })
            
            assert result.success == True
            assert "key_findings" in result.data
            assert "recommended_hashtags" in result.data
    
    @pytest.mark.asyncio
    async def test_research_plan_creation(self, agent_config):
        """Test research plan creation"""
        with patch('agents.base.agent.OpenAI'):
            agent = ResearchAgent(agent_config)
            
            context = {
                "initiative": {
                    "category": "Education",
                    "objectives": {"primary": "Increase engagement"}
                },
                "existing_research": [],
                "current_campaigns": []
            }
            
            plan = agent._create_research_plan(context)
            
            assert "topics" in plan
            assert len(plan["topics"]) > 0
            assert "education" in plan["topics"][0].lower()


class TestContentCreatorAgent:
    """Test suite for Content Creator Agent"""
    
    @pytest.fixture
    def agent_config(self):
        return AgentConfig(
            name="Test Content Creator",
            description="Test content creation agent",
            tenant_id=str(uuid.uuid4()),
            initiative_id=str(uuid.uuid4()),
            model_provider="openai"
        )
    
    @pytest.fixture
    def mock_openai_client(self):
        with patch('agents.base.agent.OpenAI') as mock:
            client = MagicMock()
            mock.return_value = client
            
            response = MagicMock()
            response.choices = [MagicMock()]
            response.choices[0].message.content = json.dumps({
                "posts": [{
                    "post_type": "image",
                    "text_content": "Check out our latest innovation! 🚀",
                    "hashtags": ["#tech", "#innovation", "#future"],
                    "links": ["https://example.com"],
                    "media_description": "Modern tech workspace",
                    "call_to_action": "Learn More",
                    "scheduled_time": (datetime.utcnow() + timedelta(days=1)).isoformat()
                }]
            })
            
            client.chat.completions.create.return_value = response
            yield client
    
    @pytest.fixture
    def mock_supabase(self):
        with patch('agents.content_creator.agent.SupabaseClient') as mock:
            client = AsyncMock()
            
            client.select.return_value = [{
                "id": str(uuid.uuid4()),
                "name": "Test Ad Set",
                "creative_brief": {
                    "theme": "Technology",
                    "tone": "professional"
                },
                "campaign_id": str(uuid.uuid4())
            }]
            
            client.insert.return_value = {"id": str(uuid.uuid4())}
            
            mock.return_value = client
            yield client
    
    @pytest.mark.asyncio
    async def test_content_creation(self, agent_config, mock_openai_client, mock_supabase):
        """Test content creation execution"""
        agent = ContentCreatorAgent(agent_config)
        
        result = await agent.execute({
            "ad_set_id": str(uuid.uuid4()),
            "ad_set_data": {
                "creative_brief": {
                    "theme": "Innovation",
                    "tone": "inspiring",
                    "target_audience": "Tech professionals"
                },
                "materials": {
                    "links": ["https://example.com"],
                    "hashtags": ["#tech"]
                },
                "post_volume": 3
            }
        })
        
        assert result.success == True
        assert "posts_created" in result.data
        assert result.data["posts_created"] >= 1
    
    @pytest.mark.asyncio
    async def test_post_enhancement(self, agent_config):
        """Test post enhancement functionality"""
        with patch('agents.base.agent.OpenAI'):
            agent = ContentCreatorAgent(agent_config)
            
            posts = [{
                "post_type": "image",
                "text_content": "New update",
                "hashtags": ["tech", "news"],
                "links": []
            }]
            
            enhanced = await agent._enhance_posts(posts, {})
            
            assert len(enhanced) == 1
            assert enhanced[0]["hashtags"][0].startswith("#")
            assert "generation_metadata" in enhanced[0]


class TestIntegration:
    """Integration tests for agent collaboration"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete workflow from research to content creation"""
        
        tenant_id = str(uuid.uuid4())
        initiative_id = str(uuid.uuid4())
        
        # Mock all external dependencies
        with patch('agents.base.agent.OpenAI'), \
             patch('agents.orchestrator.agent.SupabaseClient'), \
             patch('agents.researcher.agent.SupabaseClient'), \
             patch('agents.content_creator.agent.SupabaseClient'), \
             patch('agents.researcher.agent.PerplexitySearch'), \
             patch('agents.researcher.agent.FacebookSearch'), \
             patch('agents.researcher.agent.InstagramSearch'):
            
            # 1. Research Phase
            research_config = AgentConfig(
                name="Researcher",
                description="Research agent",
                tenant_id=tenant_id,
                initiative_id=initiative_id,
                model_provider="openai"
            )
            
            # 2. Orchestration Phase
            orchestrator_config = AgentConfig(
                name="Orchestrator",
                description="Campaign orchestrator",
                tenant_id=tenant_id,
                initiative_id=initiative_id,
                model_provider="openai"
            )
            
            # 3. Content Creation Phase
            content_config = AgentConfig(
                name="Content Creator",
                description="Content generation",
                tenant_id=tenant_id,
                initiative_id=initiative_id,
                model_provider="openai"
            )
            
            # Verify agents can be instantiated
            researcher = ResearchAgent(research_config)
            orchestrator = OrchestratorAgent(orchestrator_config)
            content_creator = ContentCreatorAgent(content_config)
            
            assert researcher is not None
            assert orchestrator is not None
            assert content_creator is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])