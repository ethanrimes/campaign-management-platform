-- Migration: 009_add_campaign_id_to_posts.sql

-- Add campaign_id column to posts table
ALTER TABLE posts 
ADD COLUMN campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE;

-- Create index for better query performance
CREATE INDEX idx_posts_campaign_id ON posts(campaign_id);

-- Backfill campaign_id from ad_sets for existing posts
UPDATE posts p
SET campaign_id = a.campaign_id
FROM ad_sets a
WHERE p.ad_set_id = a.id
AND p.campaign_id IS NULL;

-- Make it NOT NULL after backfilling (optional, depending on requirements)
-- ALTER TABLE posts ALTER COLUMN campaign_id SET NOT NULL;