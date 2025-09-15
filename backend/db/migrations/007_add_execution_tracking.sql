-- backend/db/migrations/007_add_execution_tracking.sql
-- Migration: Add execution_id for tracking orchestrator workflow execution
-- Revision ID: 007
-- Revises: 006
-- Create Date: 2025-01-14

-- ============================================================================
-- UPGRADE: Add execution_id columns to track workflow execution
-- ============================================================================

-- Add execution_id to campaigns table
ALTER TABLE campaigns 
ADD COLUMN IF NOT EXISTS execution_id UUID,
ADD COLUMN IF NOT EXISTS execution_metadata JSONB;

-- Add execution_id to ad_sets table
ALTER TABLE ad_sets 
ADD COLUMN IF NOT EXISTS execution_id UUID,
ADD COLUMN IF NOT EXISTS execution_step VARCHAR(50);

-- Add execution_id to posts table
ALTER TABLE posts 
ADD COLUMN IF NOT EXISTS execution_id UUID,
ADD COLUMN IF NOT EXISTS execution_step VARCHAR(50);

-- Add execution_id to research table
ALTER TABLE research 
ADD COLUMN IF NOT EXISTS execution_id UUID,
ADD COLUMN IF NOT EXISTS execution_step VARCHAR(50);

-- Add execution_id to agent_memories table
ALTER TABLE agent_memories 
ADD COLUMN IF NOT EXISTS execution_id UUID;

-- Add execution_id to media_files table
ALTER TABLE media_files 
ADD COLUMN IF NOT EXISTS execution_id UUID,
ADD COLUMN IF NOT EXISTS execution_step VARCHAR(50);

-- Create execution_logs table to track overall execution
CREATE TABLE IF NOT EXISTS execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL UNIQUE,
    initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
    workflow_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'running',
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    steps_completed JSONB DEFAULT '[]'::jsonb,
    steps_failed JSONB DEFAULT '[]'::jsonb,
    error_messages JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for execution_id
CREATE INDEX IF NOT EXISTS idx_campaigns_execution ON campaigns(execution_id);
CREATE INDEX IF NOT EXISTS idx_ad_sets_execution ON ad_sets(execution_id);
CREATE INDEX IF NOT EXISTS idx_posts_execution ON posts(execution_id);
CREATE INDEX IF NOT EXISTS idx_research_execution ON research(execution_id);
CREATE INDEX IF NOT EXISTS idx_agent_memories_execution ON agent_memories(execution_id);
CREATE INDEX IF NOT EXISTS idx_media_files_execution ON media_files(execution_id);
CREATE INDEX IF NOT EXISTS idx_execution_logs_initiative ON execution_logs(initiative_id);
CREATE INDEX IF NOT EXISTS idx_execution_logs_execution ON execution_logs(execution_id);
CREATE INDEX IF NOT EXISTS idx_execution_logs_status ON execution_logs(status);

-- Add trigger for execution_logs updated_at
DROP TRIGGER IF EXISTS update_execution_logs_updated_at ON execution_logs;
CREATE TRIGGER update_execution_logs_updated_at 
    BEFORE UPDATE ON execution_logs
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS on execution_logs
ALTER TABLE execution_logs ENABLE ROW LEVEL SECURITY;

-- Create RLS policy for execution_logs
DROP POLICY IF EXISTS execution_logs_access_policy ON execution_logs;
CREATE POLICY execution_logs_access_policy ON execution_logs
    FOR ALL
    USING (initiative_id = current_setting('app.current_initiative_id', true)::UUID);

-- Add comments
COMMENT ON COLUMN campaigns.execution_id IS 'UUID linking to the orchestrator execution that created this campaign';
COMMENT ON COLUMN campaigns.execution_metadata IS 'Metadata about the execution context';
COMMENT ON COLUMN ad_sets.execution_id IS 'UUID linking to the orchestrator execution';
COMMENT ON COLUMN ad_sets.execution_step IS 'Step in the workflow that created this (e.g., Planning)';
COMMENT ON COLUMN posts.execution_id IS 'UUID linking to the orchestrator execution';
COMMENT ON COLUMN posts.execution_step IS 'Step in the workflow that created this (e.g., Content Creation)';
COMMENT ON COLUMN research.execution_id IS 'UUID linking to the orchestrator execution';
COMMENT ON COLUMN research.execution_step IS 'Step in the workflow that created this (e.g., Research)';
COMMENT ON COLUMN agent_memories.execution_id IS 'UUID linking to the orchestrator execution';
COMMENT ON COLUMN media_files.execution_id IS 'UUID linking to the orchestrator execution';
COMMENT ON COLUMN media_files.execution_step IS 'Step in the workflow that created this';

COMMENT ON TABLE execution_logs IS 'Tracks orchestrator workflow executions for visibility and debugging';

-- Create a view for easy execution tracking
CREATE OR REPLACE VIEW execution_summary AS
SELECT 
    el.execution_id,
    el.initiative_id,
    el.workflow_type,
    el.status,
    el.started_at,
    el.completed_at,
    EXTRACT(EPOCH FROM (COALESCE(el.completed_at, CURRENT_TIMESTAMP) - el.started_at)) as duration_seconds,
    (SELECT COUNT(*) FROM campaigns WHERE execution_id = el.execution_id) as campaigns_created,
    (SELECT COUNT(*) FROM ad_sets WHERE execution_id = el.execution_id) as ad_sets_created,
    (SELECT COUNT(*) FROM posts WHERE execution_id = el.execution_id) as posts_created,
    (SELECT COUNT(*) FROM research WHERE execution_id = el.execution_id) as research_entries,
    (SELECT COUNT(*) FROM media_files WHERE execution_id = el.execution_id) as media_files_created,
    el.steps_completed,
    el.steps_failed,
    el.metadata
FROM execution_logs el;

COMMENT ON VIEW execution_summary IS 'Summary view of execution logs with counts of created entities';

-- ============================================================================
-- DOWNGRADE: Remove execution tracking
-- ============================================================================
-- To rollback this migration, run the following:

/*
-- Drop view
DROP VIEW IF EXISTS execution_summary;

-- Drop RLS policy
DROP POLICY IF EXISTS execution_logs_access_policy ON execution_logs;

-- Drop triggers
DROP TRIGGER IF EXISTS update_execution_logs_updated_at ON execution_logs;

-- Drop indexes
DROP INDEX IF EXISTS idx_campaigns_execution;
DROP INDEX IF EXISTS idx_ad_sets_execution;
DROP INDEX IF EXISTS idx_posts_execution;
DROP INDEX IF EXISTS idx_research_execution;
DROP INDEX IF EXISTS idx_agent_memories_execution;
DROP INDEX IF EXISTS idx_media_files_execution;
DROP INDEX IF EXISTS idx_execution_logs_initiative;
DROP INDEX IF EXISTS idx_execution_logs_execution;
DROP INDEX IF EXISTS idx_execution_logs_status;

-- Drop execution_logs table
DROP TABLE IF EXISTS execution_logs;

-- Remove columns
ALTER TABLE campaigns DROP COLUMN IF EXISTS execution_id, DROP COLUMN IF EXISTS execution_metadata;
ALTER TABLE ad_sets DROP COLUMN IF EXISTS execution_id, DROP COLUMN IF EXISTS execution_step;
ALTER TABLE posts DROP COLUMN IF EXISTS execution_id, DROP COLUMN IF EXISTS execution_step;
ALTER TABLE research DROP COLUMN IF EXISTS execution_id, DROP COLUMN IF EXISTS execution_step;
ALTER TABLE agent_memories DROP COLUMN IF EXISTS execution_id;
ALTER TABLE media_files DROP COLUMN IF EXISTS execution_id, DROP COLUMN IF EXISTS execution_step;
*/