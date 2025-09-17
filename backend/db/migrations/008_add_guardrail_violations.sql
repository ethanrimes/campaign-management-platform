-- backend/db/migrations/008_add_guardrail_violations.sql
-- Migration: Add guardrail_violations column to execution_logs
-- Revision ID: 008
-- Revises: 007
-- Create Date: 2025-01-15

-- ============================================================================
-- UPGRADE: Add missing guardrail_violations column
-- ============================================================================

-- Add guardrail_violations column to execution_logs table
ALTER TABLE execution_logs 
ADD COLUMN IF NOT EXISTS guardrail_violations JSONB DEFAULT '[]'::jsonb;

-- Add comment for documentation
COMMENT ON COLUMN execution_logs.guardrail_violations IS 
    'Array of guardrail violations that occurred during execution. Each entry contains step name and error message.';

-- Create index for performance when querying violations
CREATE INDEX IF NOT EXISTS idx_execution_logs_violations 
ON execution_logs USING GIN (guardrail_violations) 
WHERE guardrail_violations IS NOT NULL AND guardrail_violations != '[]'::jsonb;

-- Update any existing execution_logs that might have violations in metadata
-- This ensures backward compatibility if violations were stored elsewhere
UPDATE execution_logs
SET guardrail_violations = metadata->'guardrail_violations'
WHERE metadata ? 'guardrail_violations' 
  AND guardrail_violations IS NULL;

-- ============================================================================
-- VERIFICATION: Ensure all expected columns exist
-- ============================================================================

-- This is a safety check to ensure all columns the code expects are present
DO $$
BEGIN
    -- Check if all required columns exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'execution_logs' 
        AND column_name = 'guardrail_violations'
    ) THEN
        RAISE EXCEPTION 'Failed to add guardrail_violations column';
    END IF;
END $$;

-- ============================================================================
-- DOWNGRADE: Remove guardrail_violations column
-- ============================================================================
-- To rollback this migration, run the following:

/*
-- Drop index
DROP INDEX IF EXISTS idx_execution_logs_violations;

-- Drop column
ALTER TABLE execution_logs DROP COLUMN IF EXISTS guardrail_violations;
*/