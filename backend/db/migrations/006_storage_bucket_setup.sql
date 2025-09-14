-- backend/db/migrations/006_storage_bucket_setup.sql
-- Migration: Document storage bucket requirements
-- Revision ID: 006  
-- Revises: 005
-- Create Date: 2025-01-14

-- ============================================================================
-- IMPORTANT: Storage Bucket Setup Required
-- ============================================================================
-- This migration documents that a Supabase Storage bucket must be created
-- separately from SQL migrations. Run the following after this migration:
--
-- python scripts/setup/create_storage_bucket.py
--
-- Or manually create in Supabase Dashboard:
-- 1. Go to Storage section
-- 2. Create bucket named: generated-media
-- 3. Set to PUBLIC access
-- 4. Configure policies for upload/download

-- Add a check constraint to ensure proper file types
ALTER TABLE media_files 
ADD CONSTRAINT check_file_type 
CHECK (file_type IN ('image', 'video', 'reel', 'carousel'));

-- Add an index for faster media lookups by creation date and type
CREATE INDEX IF NOT EXISTS idx_media_files_created_type 
ON media_files(created_at DESC, file_type);

-- Create a function to validate storage paths
CREATE OR REPLACE FUNCTION validate_storage_path()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure path starts with initiative_id
    IF NOT NEW.supabase_path ~ ('^' || NEW.initiative_id::text) THEN
        RAISE EXCEPTION 'Storage path must start with initiative_id';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add trigger to validate paths
DROP TRIGGER IF EXISTS validate_media_storage_path ON media_files;
CREATE TRIGGER validate_media_storage_path
    BEFORE INSERT OR UPDATE ON media_files
    FOR EACH ROW
    EXECUTE FUNCTION validate_storage_path();

-- Document the storage bucket requirement
COMMENT ON TABLE media_files IS 
    'Stores metadata for AI-generated media files in Supabase storage.
     REQUIRES: Supabase storage bucket "generated-media" with public access.
     Run: python scripts/setup/create_storage_bucket.py to create bucket.';