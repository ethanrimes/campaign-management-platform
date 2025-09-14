-- backend/db/migrations/005_add_media_files_table.sql
-- Migration: Add media_files table for tracking generated media
-- Revision ID: 005
-- Revises: 004
-- Create Date: 2024-12-19

-- ============================================================================
-- UPGRADE
-- ============================================================================

-- Create media_files table
CREATE TABLE IF NOT EXISTS media_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
    file_type VARCHAR(50) NOT NULL,
    supabase_path VARCHAR(500) NOT NULL,
    public_url VARCHAR(1000) NOT NULL,
    prompt_used TEXT,
    dimensions JSONB,
    duration_seconds INTEGER,
    file_size_bytes BIGINT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_media_files_initiative ON media_files(initiative_id);
CREATE INDEX idx_media_files_type ON media_files(file_type);
CREATE INDEX idx_media_files_created ON media_files(created_at);

-- Add trigger for updated_at
CREATE TRIGGER update_media_files_updated_at 
    BEFORE UPDATE ON media_files
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security
ALTER TABLE media_files ENABLE ROW LEVEL SECURITY;

-- Create RLS policy
CREATE POLICY media_files_access_policy ON media_files
    FOR ALL
    USING (initiative_id = current_setting('app.current_initiative_id', true)::UUID);

-- Add table comment
COMMENT ON TABLE media_files IS 
    'Stores metadata for AI-generated media files stored in Supabase storage. 
     Requires Supabase storage bucket: generated-media (public access)';

-- Add column comments
COMMENT ON COLUMN media_files.file_type IS 'Type of media: image, video, reel';
COMMENT ON COLUMN media_files.supabase_path IS 'Path in Supabase storage bucket';
COMMENT ON COLUMN media_files.public_url IS 'Public URL for accessing the file';
COMMENT ON COLUMN media_files.prompt_used IS 'AI prompt used to generate the media';
COMMENT ON COLUMN media_files.dimensions IS 'JSON with width/height for images/videos';
COMMENT ON COLUMN media_files.duration_seconds IS 'Duration for video files';
COMMENT ON COLUMN media_files.file_size_bytes IS 'File size in bytes';
COMMENT ON COLUMN media_files.metadata IS 'Additional metadata as JSON';
COMMENT ON COLUMN media_files.created_at IS 'Timestamp when the record was created';
COMMENT ON COLUMN media_files.updated_at IS 'Timestamp when the record was last updated';

-- ============================================================================
-- DOWNGRADE
-- ============================================================================
-- To rollback this migration, run the following:

/*
-- Drop RLS policy
DROP POLICY IF EXISTS media_files_access_policy ON media_files;

-- Drop trigger
DROP TRIGGER IF EXISTS update_media_files_updated_at ON media_files;

-- Drop indexes
DROP INDEX IF EXISTS idx_media_files_created;
DROP INDEX IF EXISTS idx_media_files_type;
DROP INDEX IF EXISTS idx_media_files_initiative;

-- Drop table
DROP TABLE IF EXISTS media_files;
*/