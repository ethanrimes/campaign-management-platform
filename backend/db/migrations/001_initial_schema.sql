-- backend/db/migrations/001_initial_schema.sql

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create initiatives table
CREATE TABLE IF NOT EXISTS initiatives (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,  -- Keep for backwards compatibility but will match initiative_id
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Social Media Accounts
    facebook_page_id VARCHAR(255),
    facebook_page_name VARCHAR(255),
    facebook_page_url VARCHAR(500),
    instagram_username VARCHAR(255),
    instagram_account_id VARCHAR(255),
    instagram_url VARCHAR(500),
    
    -- Configuration
    category VARCHAR(100),
    objectives JSONB,
    brand_assets JSONB,
    custom_prompts JSONB,
    
    -- Budget
    daily_budget JSONB,
    total_budget JSONB,
    
    -- Model Configuration
    model_provider VARCHAR(50) DEFAULT 'openai',
    llm_config JSONB,
    
    -- Metrics Goals
    optimization_metric VARCHAR(50),
    target_metrics JSONB,
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Additional Settings
    settings JSONB
);

-- Create campaigns table
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,  -- Will match initiative_id for consistency
    initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
    
    -- Campaign Details
    name VARCHAR(255) NOT NULL,
    objective VARCHAR(50) NOT NULL,
    description TEXT,
    
    -- Budget
    budget_mode VARCHAR(50),
    daily_budget DECIMAL(10, 2),
    lifetime_budget DECIMAL(10, 2),
    spent_budget DECIMAL(10, 2) DEFAULT 0,
    
    -- Schedule
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    
    -- Status
    status VARCHAR(50) DEFAULT 'draft',
    is_active BOOLEAN DEFAULT true,
    
    -- Performance
    metrics JSONB,
    
    -- Meta Campaign ID
    meta_campaign_id VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create ad_sets table
CREATE TABLE IF NOT EXISTS ad_sets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,  -- Will match initiative_id
    initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    
    -- Ad Set Details
    name VARCHAR(255) NOT NULL,
    objective VARCHAR(100),
    
    -- Targeting
    target_audience JSONB,
    placements JSONB,
    
    -- Budget & Schedule
    daily_budget DECIMAL(10, 2),
    lifetime_budget DECIMAL(10, 2),
    spent_budget DECIMAL(10, 2) DEFAULT 0,
    bid_strategy VARCHAR(50),
    
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    schedule JSONB,
    
    -- Content Strategy
    post_frequency INTEGER,
    post_volume INTEGER,
    creative_brief JSONB,
    materials JSONB,
    
    -- Status
    status VARCHAR(50) DEFAULT 'draft',
    is_active BOOLEAN DEFAULT true,
    
    -- Performance
    metrics JSONB,
    
    -- Meta Ad Set ID
    meta_ad_set_id VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add initiative_id to ad_sets if missing
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'ad_sets' 
                   AND column_name = 'initiative_id') THEN
        ALTER TABLE ad_sets ADD COLUMN initiative_id UUID;
        -- Update existing rows to get initiative_id from campaigns
        UPDATE ad_sets a SET initiative_id = c.initiative_id 
        FROM campaigns c WHERE a.campaign_id = c.id;
        -- Add foreign key constraint
        ALTER TABLE ad_sets ADD CONSTRAINT ad_sets_initiative_fkey 
        FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Create posts table
CREATE TABLE IF NOT EXISTS posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
    ad_set_id UUID NOT NULL REFERENCES ad_sets(id) ON DELETE CASCADE,
    
    -- Content
    post_type VARCHAR(50) NOT NULL,
    text_content TEXT,
    hashtags JSONB,
    links JSONB,
    
    -- Media
    media_urls JSONB,
    media_metadata JSONB,
    
    -- Schedule
    scheduled_time TIMESTAMP,
    published_time TIMESTAMP,
    
    -- Platform-specific IDs
    facebook_post_id VARCHAR(255),
    instagram_post_id VARCHAR(255),
    
    -- Status
    status VARCHAR(50) DEFAULT 'draft',
    is_published BOOLEAN DEFAULT false,
    
    -- Performance
    reach INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    engagement INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    
    -- AI Generation Metadata
    generation_metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add initiative_id to posts if missing
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'posts' 
                   AND column_name = 'initiative_id') THEN
        ALTER TABLE posts ADD COLUMN initiative_id UUID;
        -- Update existing rows
        UPDATE posts p SET initiative_id = a.initiative_id 
        FROM ad_sets a WHERE p.ad_set_id = a.id;
        -- Add foreign key constraint
        ALTER TABLE posts ADD CONSTRAINT posts_initiative_fkey 
        FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Create metrics table
CREATE TABLE IF NOT EXISTS metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    
    -- Metrics
    impressions INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    engagement INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    spend DECIMAL(10, 2) DEFAULT 0,
    
    -- Calculated metrics
    ctr DECIMAL(5, 2),
    cpc DECIMAL(10, 2),
    cpm DECIMAL(10, 2),
    engagement_rate DECIMAL(5, 2),
    
    -- Time period
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    
    -- Raw data
    raw_metrics JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add initiative_id to metrics if missing
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'metrics' 
                   AND column_name = 'initiative_id') THEN
        ALTER TABLE metrics ADD COLUMN initiative_id UUID;
        ALTER TABLE metrics ADD CONSTRAINT metrics_initiative_fkey 
        FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Create research table
CREATE TABLE IF NOT EXISTS research (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
    
    -- Research Details
    research_type VARCHAR(100) NOT NULL,
    topic VARCHAR(255) NOT NULL,
    
    -- Content
    summary TEXT,
    insights JSONB,
    raw_data JSONB,
    
    -- Sources
    sources JSONB,
    search_queries JSONB,
    
    -- Relevance
    relevance_score JSONB,
    tags JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- Create agent_memories table
CREATE TABLE IF NOT EXISTS agent_memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add initiative_id to agent_memories if missing
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'agent_memories' 
                   AND column_name = 'initiative_id') THEN
        ALTER TABLE agent_memories ADD COLUMN initiative_id UUID;
        ALTER TABLE agent_memories ADD CONSTRAINT agent_memories_initiative_fkey 
        FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Create indexes (idempotent)
CREATE INDEX IF NOT EXISTS idx_campaigns_initiative ON campaigns(initiative_id);
CREATE INDEX IF NOT EXISTS idx_ad_sets_initiative ON ad_sets(initiative_id);
CREATE INDEX IF NOT EXISTS idx_ad_sets_campaign ON ad_sets(campaign_id);
CREATE INDEX IF NOT EXISTS idx_posts_initiative ON posts(initiative_id);
CREATE INDEX IF NOT EXISTS idx_posts_ad_set ON posts(ad_set_id);
CREATE INDEX IF NOT EXISTS idx_posts_scheduled ON posts(scheduled_time);
CREATE INDEX IF NOT EXISTS idx_metrics_initiative ON metrics(initiative_id);
CREATE INDEX IF NOT EXISTS idx_metrics_entity ON metrics(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_research_initiative ON research(initiative_id);
CREATE INDEX IF NOT EXISTS idx_agent_memories_initiative ON agent_memories(initiative_id);
CREATE INDEX IF NOT EXISTS idx_agent_memories_agent ON agent_memories(agent_id);

-- Enable Row Level Security (idempotent)
DO $$ 
BEGIN
    ALTER TABLE initiatives ENABLE ROW LEVEL SECURITY;
EXCEPTION
    WHEN OTHERS THEN NULL;
END $$;

DO $$ 
BEGIN
    ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
EXCEPTION
    WHEN OTHERS THEN NULL;
END $$;

DO $$ 
BEGIN
    ALTER TABLE ad_sets ENABLE ROW LEVEL SECURITY;
EXCEPTION
    WHEN OTHERS THEN NULL;
END $$;

DO $$ 
BEGIN
    ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
EXCEPTION
    WHEN OTHERS THEN NULL;
END $$;

DO $$ 
BEGIN
    ALTER TABLE metrics ENABLE ROW LEVEL SECURITY;
EXCEPTION
    WHEN OTHERS THEN NULL;
END $$;

DO $$ 
BEGIN
    ALTER TABLE research ENABLE ROW LEVEL SECURITY;
EXCEPTION
    WHEN OTHERS THEN NULL;
END $$;

DO $$ 
BEGIN
    ALTER TABLE agent_memories ENABLE ROW LEVEL SECURITY;
EXCEPTION
    WHEN OTHERS THEN NULL;
END $$;

-- Create RLS policies based on initiative_id (idempotent - using CREATE OR REPLACE)
-- Drop old policies if they exist, then create new ones

-- Initiatives table - accessed by initiative_id directly
DROP POLICY IF EXISTS "initiatives_access_policy" ON initiatives;
CREATE POLICY "initiatives_access_policy" ON initiatives
    FOR ALL 
    USING (id = current_setting('app.current_initiative_id', true)::UUID);

-- Campaigns - filtered by initiative_id
DROP POLICY IF EXISTS "campaigns_access_policy" ON campaigns;
CREATE POLICY "campaigns_access_policy" ON campaigns
    FOR ALL
    USING (initiative_id = current_setting('app.current_initiative_id', true)::UUID);

-- Ad Sets - filtered by initiative_id
DROP POLICY IF EXISTS "ad_sets_access_policy" ON ad_sets;
CREATE POLICY "ad_sets_access_policy" ON ad_sets
    FOR ALL
    USING (initiative_id = current_setting('app.current_initiative_id', true)::UUID);

-- Posts - filtered by initiative_id
DROP POLICY IF EXISTS "posts_access_policy" ON posts;
CREATE POLICY "posts_access_policy" ON posts
    FOR ALL
    USING (initiative_id = current_setting('app.current_initiative_id', true)::UUID);

-- Metrics - filtered by initiative_id
DROP POLICY IF EXISTS "metrics_access_policy" ON metrics;
CREATE POLICY "metrics_access_policy" ON metrics
    FOR ALL
    USING (initiative_id = current_setting('app.current_initiative_id', true)::UUID);

-- Research - filtered by initiative_id
DROP POLICY IF EXISTS "research_access_policy" ON research;
CREATE POLICY "research_access_policy" ON research
    FOR ALL
    USING (initiative_id = current_setting('app.current_initiative_id', true)::UUID);

-- Agent Memories - filtered by initiative_id
DROP POLICY IF EXISTS "agent_memories_access_policy" ON agent_memories;
CREATE POLICY "agent_memories_access_policy" ON agent_memories
    FOR ALL
    USING (initiative_id = current_setting('app.current_initiative_id', true)::UUID);

-- Create update trigger function (idempotent)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add update triggers (idempotent)
DROP TRIGGER IF EXISTS update_initiatives_updated_at ON initiatives;
CREATE TRIGGER update_initiatives_updated_at 
    BEFORE UPDATE ON initiatives
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
    
DROP TRIGGER IF EXISTS update_campaigns_updated_at ON campaigns;
CREATE TRIGGER update_campaigns_updated_at 
    BEFORE UPDATE ON campaigns
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
    
DROP TRIGGER IF EXISTS update_ad_sets_updated_at ON ad_sets;
CREATE TRIGGER update_ad_sets_updated_at 
    BEFORE UPDATE ON ad_sets
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
    
DROP TRIGGER IF EXISTS update_posts_updated_at ON posts;
CREATE TRIGGER update_posts_updated_at 
    BEFORE UPDATE ON posts
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();