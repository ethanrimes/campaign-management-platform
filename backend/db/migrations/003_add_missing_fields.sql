-- backend/db/migrations/003_add_missing_fields.sql

-- Add missing Instagram Business ID field to initiatives table
ALTER TABLE initiatives ADD COLUMN IF NOT EXISTS instagram_business_id VARCHAR(255);

-- Add index for Instagram Business ID if needed
CREATE INDEX IF NOT EXISTS idx_initiatives_instagram_business_id ON initiatives(instagram_business_id);

-- Add comment for clarity
COMMENT ON COLUMN initiatives.instagram_business_id IS 'Instagram Business Account ID for the initiative';

-- Ensure consistency between initiatives and initiative_tokens tables
-- The initiative_tokens table already has insta_business_id from migration 002
-- This migration ensures the initiatives table has the corresponding field