-- Migration: Add encryption support for user files
-- This enables end-to-end encryption where even database admins cannot view files

-- Add encryption metadata columns to user_files table
ALTER TABLE user_files
ADD COLUMN IF NOT EXISTS encrypted BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS encryption_iv TEXT,
ADD COLUMN IF NOT EXISTS encryption_tag TEXT,
ADD COLUMN IF NOT EXISTS encryption_salt TEXT,
ADD COLUMN IF NOT EXISTS encrypted_filename TEXT,
ADD COLUMN IF NOT EXISTS filename_iv TEXT,
ADD COLUMN IF NOT EXISTS filename_tag TEXT,
ADD COLUMN IF NOT EXISTS requires_otp BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS last_accessed_at TIMESTAMPTZ;

-- Create index for faster queries on encrypted files
CREATE INDEX IF NOT EXISTS idx_user_files_encrypted ON user_files(user_id, encrypted);
CREATE INDEX IF NOT EXISTS idx_user_files_requires_otp ON user_files(user_id, requires_otp);

-- Create table to track OTP-based file access attempts
CREATE TABLE IF NOT EXISTS file_access_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  file_id UUID NOT NULL REFERENCES user_files(id) ON DELETE CASCADE,
  access_type TEXT NOT NULL CHECK (access_type IN ('view', 'download', 'decrypt')),
  otp_verified BOOLEAN DEFAULT FALSE,
  ip_address TEXT,
  user_agent TEXT,
  success BOOLEAN DEFAULT FALSE,
  error_message TEXT,
  accessed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for access logs
CREATE INDEX IF NOT EXISTS idx_file_access_logs_user ON file_access_logs(user_id, accessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_file_access_logs_file ON file_access_logs(file_id, accessed_at DESC);

-- Enable RLS on file_access_logs
ALTER TABLE file_access_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only view their own access logs
CREATE POLICY "Users can view own file access logs"
  ON file_access_logs
  FOR SELECT
  USING (auth.uid() = user_id);

-- RLS Policy: System can insert access logs
CREATE POLICY "System can insert file access logs"
  ON file_access_logs
  FOR INSERT
  WITH CHECK (true);

-- Create table to store user encryption keys (encrypted with user password)
CREATE TABLE IF NOT EXISTS user_encryption_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  encrypted_master_key TEXT NOT NULL,
  key_iv TEXT NOT NULL,
  key_tag TEXT NOT NULL,
  key_salt TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on user_encryption_keys
ALTER TABLE user_encryption_keys ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only access their own encryption keys
CREATE POLICY "Users can view own encryption keys"
  ON user_encryption_keys
  FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own encryption keys"
  ON user_encryption_keys
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own encryption keys"
  ON user_encryption_keys
  FOR UPDATE
  USING (auth.uid() = user_id);

-- Update otp_verifications table to support Message Central integration
ALTER TABLE otp_verifications
ADD COLUMN IF NOT EXISTS phone TEXT,
ADD COLUMN IF NOT EXISTS verification_id TEXT,
ADD COLUMN IF NOT EXISTS attempts INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_attempt_at TIMESTAMPTZ;

-- Create index for faster OTP lookups
CREATE INDEX IF NOT EXISTS idx_otp_verifications_user_purpose ON otp_verifications(user_id, purpose, verified);
CREATE INDEX IF NOT EXISTS idx_otp_verifications_verification_id ON otp_verifications(verification_id);

-- Add comment for verification_id
COMMENT ON COLUMN otp_verifications.verification_id IS 'Message Central verification ID for OTP tracking';
COMMENT ON COLUMN otp_verifications.phone IS 'Phone number where OTP was sent';
COMMENT ON COLUMN otp_verifications.attempts IS 'Number of failed verification attempts';
COMMENT ON COLUMN otp_verifications.last_attempt_at IS 'Timestamp of last verification attempt';

-- Create function to log file access
CREATE OR REPLACE FUNCTION log_file_access(
  p_user_id UUID,
  p_file_id UUID,
  p_access_type TEXT,
  p_otp_verified BOOLEAN,
  p_ip_address TEXT,
  p_user_agent TEXT,
  p_success BOOLEAN,
  p_error_message TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_log_id UUID;
BEGIN
  INSERT INTO file_access_logs (
    user_id,
    file_id,
    access_type,
    otp_verified,
    ip_address,
    user_agent,
    success,
    error_message
  ) VALUES (
    p_user_id,
    p_file_id,
    p_access_type,
    p_otp_verified,
    p_ip_address,
    p_user_agent,
    p_success,
    p_error_message
  )
  RETURNING id INTO v_log_id;
  
  -- Update last_accessed_at on the file
  IF p_success THEN
    UPDATE user_files
    SET last_accessed_at = NOW()
    WHERE id = p_file_id;
  END IF;
  
  RETURN v_log_id;
END;
$$;

-- Create function to get file access statistics
CREATE OR REPLACE FUNCTION get_file_access_stats(p_user_id UUID)
RETURNS TABLE (
  total_accesses BIGINT,
  successful_accesses BIGINT,
  failed_accesses BIGINT,
  otp_verified_accesses BIGINT,
  last_access_time TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT
    COUNT(*)::BIGINT AS total_accesses,
    COUNT(*) FILTER (WHERE success = TRUE)::BIGINT AS successful_accesses,
    COUNT(*) FILTER (WHERE success = FALSE)::BIGINT AS failed_accesses,
    COUNT(*) FILTER (WHERE otp_verified = TRUE)::BIGINT AS otp_verified_accesses,
    MAX(accessed_at) AS last_access_time
  FROM file_access_logs
  WHERE user_id = p_user_id;
END;
$$;

-- Add comments for documentation
COMMENT ON COLUMN user_files.encrypted IS 'Whether the file is encrypted (true) or stored in plaintext (false)';
COMMENT ON COLUMN user_files.encryption_iv IS 'Initialization vector for AES-256-GCM encryption (base64)';
COMMENT ON COLUMN user_files.encryption_tag IS 'Authentication tag for AES-256-GCM encryption (base64)';
COMMENT ON COLUMN user_files.encryption_salt IS 'Salt used for key derivation (base64)';
COMMENT ON COLUMN user_files.encrypted_filename IS 'Encrypted original filename for additional privacy (base64)';
COMMENT ON COLUMN user_files.requires_otp IS 'Whether OTP verification is required to access this file';
COMMENT ON COLUMN user_files.last_accessed_at IS 'Timestamp of last successful file access';

COMMENT ON TABLE file_access_logs IS 'Audit log of all file access attempts with OTP verification status';
COMMENT ON TABLE user_encryption_keys IS 'User-specific master encryption keys, encrypted with user password';
