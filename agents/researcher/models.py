# agents/researcher/models.py

"""
Researcher agent models that use centralized database models for persistence.
Agent-specific structures for research logic with database model integration.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import UUID

# Import centralized database models
from backend.db.models.research import ResearchInsert
from backend.db.models.serialization import serialize_dict, prepare_for_db


class ResearchType(str, Enum):
    """Types of research"""
    COMPETITOR = "competitor"
    TREND = "trend"
    HASHTAG = "hashtag"
    AUDIENCE = "audience"
    COMPREHENSIVE = "comprehensive"


class SourceReliability(str, Enum):
    """Source reliability ratings"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResearchSource(BaseModel):
    """Research source information for agent use"""
    url: str = Field(description="Source URL")
    title: str = Field(description="Source title")
    platform: str = Field(description="Platform (web, facebook, instagram)")
    reliability: SourceReliability = Field(default=SourceReliability.MEDIUM)
    accessed_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'url': self.url,
            'title': self.title,
            'platform': self.platform,
            'reliability': self.reliability.value,
            'accessed_at': self.accessed_at.isoformat()
        }


class KeyFinding(BaseModel):
    """Individual research finding for agent use"""
    topic: str = Field(description="Topic area")
    finding: str = Field(description="The finding or insight")
    source: str = Field(description="Source URL")
    relevance_score: float = Field(ge=0.0, le=1.0, description="Relevance score (0-1)")
    confidence: float = Field(ge=0.0, le=1.0, default=0.7, description="Confidence level")
    
    @validator('finding')
    def validate_finding_length(cls, v):
        if len(v) < 10:
            raise ValueError("Finding must be at least 10 characters")
        return v


class CompetitorInsight(BaseModel):
    """Competitor analysis insight"""
    name: str = Field(description="Competitor name")
    platform: str = Field(description="Platform")
    category: Optional[str] = Field(None, description="Business category")
    link: str = Field(description="Profile link")
    followers: int = Field(ge=0, description="Follower count")
    engagement_rate: Optional[float] = Field(None, ge=0.0, description="Engagement rate")
    content_frequency: Optional[str] = Field(None, description="Posting frequency")
    key_strategies: List[str] = Field(default_factory=list, description="Observed strategies")


class TrendingTopic(BaseModel):
    """Trending topic information"""
    topic: str = Field(description="Topic name")
    trend_score: float = Field(ge=0.0, le=100.0, description="Trend score (0-100)")
    growth_rate: Optional[float] = Field(None, description="Growth rate percentage")
    related_hashtags: List[str] = Field(default_factory=list, description="Related hashtags")
    peak_times: Optional[List[str]] = Field(None, description="Peak engagement times")


class ContentOpportunity(BaseModel):
    """Content opportunity identified through research"""
    opportunity_type: str = Field(description="Type of opportunity")
    description: str = Field(description="Opportunity description")
    priority: str = Field(default="medium", description="Priority level (low/medium/high)")
    target_audience: Optional[str] = Field(None, description="Target audience for this opportunity")
    estimated_impact: Optional[str] = Field(None, description="Estimated impact")
    implementation_notes: Optional[str] = Field(None, description="How to implement")


class HashtagRecommendation(BaseModel):
    """Hashtag recommendations"""
    hashtag: str = Field(description="Hashtag (with #)")
    category: str = Field(default="general", description="Hashtag category")
    popularity: str = Field(default="medium", description="Popularity level")
    relevance_score: float = Field(ge=0.0, le=1.0, description="Relevance to initiative")
    
    @validator('hashtag')
    def validate_hashtag_format(cls, v):
        if not v.startswith('#'):
            v = f"#{v}"
        # Remove spaces and special characters except underscores
        v = v.replace(' ', '').replace('-', '_')
        return v
    
    def to_simple_hashtag(self) -> str:
        """Get just the hashtag string"""
        return self.hashtag


class ResearchPlan(BaseModel):
    """Research execution plan"""
    topics: List[str] = Field(description="Topics to research")
    competitor_pages: List[str] = Field(default_factory=list, description="Competitor pages to analyze")
    hashtags: List[str] = Field(default_factory=list, description="Hashtags to track")
    trends: List[str] = Field(default_factory=list, description="Trends to monitor")
    search_queries: List[str] = Field(default_factory=list, description="Search queries to execute")


class ResearchSummary(BaseModel):
    """Summary of research findings"""
    executive_summary: str = Field(description="Executive summary of findings")
    key_takeaways: List[str] = Field(min_items=1, max_items=5, description="Key takeaways")
    action_items: List[str] = Field(default_factory=list, description="Recommended actions")
    timeframe: str = Field(default="immediate", description="Timeframe for action")


class ResearchOutput(BaseModel):
    """Main research agent output structure"""
    research_type: ResearchType = Field(description="Type of research conducted")
    summary: ResearchSummary = Field(description="Research summary")
    key_findings: List[KeyFinding] = Field(description="Key findings from research")
    content_opportunities: List[ContentOpportunity] = Field(default_factory=list)
    recommended_hashtags: List[HashtagRecommendation] = Field(default_factory=list, max_items=30)
    competitor_insights: List[CompetitorInsight] = Field(default_factory=list)
    trending_topics: List[TrendingTopic] = Field(default_factory=list)
    sources: List[ResearchSource] = Field(description="Research sources used")
    research_plan: Optional[ResearchPlan] = Field(None, description="Research plan executed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('key_findings')
    def validate_findings(cls, v):
        if len(v) == 0:
            raise ValueError("Must have at least one key finding")
        return v
    
    @validator('sources')
    def validate_sources(cls, v):
        if len(v) == 0:
            raise ValueError("Must have at least one source")
        return v
    
    def to_db_insert(self, initiative_id: UUID, execution_id: Optional[UUID] = None) -> ResearchInsert:
        """Convert to database insert model"""
        # Prepare insights for database
        insights = [
            {
                'topic': finding.topic,
                'finding': finding.finding,
                'source': finding.source,
                'relevance_score': finding.relevance_score,
                'confidence': finding.confidence
            }
            for finding in self.key_findings
        ]
        
        # Extract source URLs
        source_urls = [source.url for source in self.sources]
        
        # Prepare hashtags as list of strings
        hashtags = [h.to_simple_hashtag() for h in self.recommended_hashtags]
        
        # Build raw data for storage
        raw_data = {
            'research_type': self.research_type.value,
            'summary': serialize_dict(self.summary.dict()),
            'key_findings': serialize_dict(insights),
            'content_opportunities': serialize_dict([o.dict() for o in self.content_opportunities]),
            'recommended_hashtags': hashtags,
            'competitor_insights': serialize_dict([c.dict() for c in self.competitor_insights]),
            'trending_topics': serialize_dict([t.dict() for t in self.trending_topics]),
            'sources': serialize_dict([s.to_dict() for s in self.sources]),
            'metadata': serialize_dict(self.metadata)
        }
        
        # Create database insert model
        return ResearchInsert(
            initiative_id=initiative_id,
            research_type=self.research_type.value,
            topic="automated_research",
            summary=self.summary.executive_summary,
            insights=insights,
            raw_data=raw_data,
            sources=source_urls,
            relevance_score={'overall': 0.8},  # Calculate based on findings
            tags=['automated', 'ai_generated'],
            expires_at=(datetime.now(timezone.utc) + timedelta(days=7)),
            execution_id=execution_id,
            execution_step='Research'
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for serialization"""
        return serialize_dict(self.dict())


# Export models for agent use
__all__ = [
    'ResearchType',
    'SourceReliability',
    'ResearchSource',
    'KeyFinding',
    'CompetitorInsight',
    'TrendingTopic',
    'ContentOpportunity',
    'HashtagRecommendation',
    'ResearchPlan',
    'ResearchSummary',
    'ResearchOutput'
]