-- Add file_hash and doc_type columns to user_files
-- file_hash: SHA-256 of the original file bytes — used for deduplication
-- doc_type:  normalized document type (aadhaar, photograph, signature, driving_license)

ALTER TABLE user_files
  ADD COLUMN IF NOT EXISTS file_hash  TEXT,
  ADD COLUMN IF NOT EXISTS doc_type   TEXT;

-- Unique constraint: one hash per user (prevents uploading exact duplicate files)
CREATE UNIQUE INDEX IF NOT EXISTS user_files_user_hash_unique
  ON user_files (user_id, file_hash)
  WHERE file_hash IS NOT NULL;

-- Index for fast doc_type lookup per user
CREATE INDEX IF NOT EXISTS user_files_user_doctype_idx
  ON user_files (user_id, doc_type)
  WHERE doc_type IS NOT NULL;

-- Comment on columns
COMMENT ON COLUMN user_files.file_hash IS 'SHA-256 hex digest of original file bytes. Used to detect duplicate uploads.';
COMMENT ON COLUMN user_files.doc_type  IS 'Normalized document category: aadhaar | photograph | signature | driving_license';
