-- backend/db/migrations/002_add_encrypted_tokens.sql

-- Add encrypted token columns to initiatives table (idempotent)
ALTER TABLE initiatives ADD COLUMN IF NOT EXISTS encrypted_tokens JSONB;
ALTER TABLE initiatives ADD COLUMN IF NOT EXISTS tokens_metadata JSONB;

-- Create a separate secure tokens table
CREATE TABLE IF NOT EXISTS initiative_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,  -- Will match initiative_id
    initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
    
    -- Encrypted tokens
    fb_page_access_token_encrypted TEXT,
    fb_system_user_token_encrypted TEXT,
    insta_access_token_encrypted TEXT,
    insta_app_id_encrypted TEXT,
    insta_app_secret_encrypted TEXT,
    
    -- Token metadata (non-sensitive)
    fb_page_id VARCHAR(255),
    fb_page_name VARCHAR(255),
    insta_business_id VARCHAR(255),
    insta_username VARCHAR(255),
    
    -- Token validity tracking
    tokens_last_validated TIMESTAMP,
    tokens_expire_at TIMESTAMP,
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    
    CONSTRAINT unique_initiative_tokens UNIQUE(initiative_id)
);

-- Handle existing UNIQUE constraint if it exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'unique_initiative_tokens'
    ) THEN
        ALTER TABLE initiative_tokens 
        ADD CONSTRAINT unique_initiative_tokens UNIQUE(initiative_id);
    END IF;
END $$;

-- Create indexes (idempotent)
CREATE INDEX IF NOT EXISTS idx_initiative_tokens_initiative ON initiative_tokens(initiative_id);

-- Enable RLS (idempotent)
DO $$ 
BEGIN
    ALTER TABLE initiative_tokens ENABLE ROW LEVEL SECURITY;
EXCEPTION
    WHEN OTHERS THEN NULL;
END $$;

-- Create RLS policy for tokens table based on initiative_id
DROP POLICY IF EXISTS "initiative_tokens_access_policy" ON initiative_tokens;
CREATE POLICY "initiative_tokens_access_policy" ON initiative_tokens
    FOR ALL
    USING (initiative_id = current_setting('app.current_initiative_id', true)::UUID);

-- Add update trigger (idempotent)
DROP TRIGGER IF EXISTS update_initiative_tokens_updated_at ON initiative_tokens;
CREATE TRIGGER update_initiative_tokens_updated_at 
    BEFORE UPDATE ON initiative_tokens
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create validation function (idempotent)
CREATE OR REPLACE FUNCTION validate_token_access(
    p_initiative_id UUID
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 
        FROM initiatives 
        WHERE id = p_initiative_id 
        AND is_active = true
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add comments (idempotent - comments replace existing)
COMMENT ON TABLE initiative_tokens IS 'Stores encrypted access tokens for social media platforms';
COMMENT ON COLUMN initiative_tokens.fb_page_access_token_encrypted IS 'Encrypted Facebook Page Access Token';
COMMENT ON COLUMN initiative_tokens.insta_access_token_encrypted IS 'Encrypted Instagram Access Token';