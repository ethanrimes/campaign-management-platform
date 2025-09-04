-- backend/db/migrations/004_remove_tenant_id.sql

-- Remove tenant_id columns as we're using initiative_id for isolation
-- Keep them for now but mark as deprecated to avoid breaking existing data

-- Add comment to indicate deprecation
COMMENT ON COLUMN initiatives.tenant_id IS 'DEPRECATED - Use initiative_id for RLS';
COMMENT ON COLUMN campaigns.tenant_id IS 'DEPRECATED - Use initiative_id for RLS';
COMMENT ON COLUMN ad_sets.tenant_id IS 'DEPRECATED - Use initiative_id for RLS';
COMMENT ON COLUMN posts.tenant_id IS 'DEPRECATED - Use initiative_id for RLS';
COMMENT ON COLUMN metrics.tenant_id IS 'DEPRECATED - Use initiative_id for RLS';
COMMENT ON COLUMN research.tenant_id IS 'DEPRECATED - Use initiative_id for RLS';
COMMENT ON COLUMN agent_memories.tenant_id IS 'DEPRECATED - Use initiative_id for RLS';
COMMENT ON COLUMN initiative_tokens.tenant_id IS 'DEPRECATED - Use initiative_id for RLS';

-- Ensure all tables have initiative_id and it's not null
ALTER TABLE campaigns ALTER COLUMN initiative_id SET NOT NULL;
ALTER TABLE ad_sets ALTER COLUMN initiative_id SET NOT NULL;
ALTER TABLE posts ALTER COLUMN initiative_id SET NOT NULL;
ALTER TABLE metrics ALTER COLUMN initiative_id SET NOT NULL;
ALTER TABLE research ALTER COLUMN initiative_id SET NOT NULL;
ALTER TABLE agent_memories ALTER COLUMN initiative_id SET NOT NULL;