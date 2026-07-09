-- Add file_hash to document_meta for deduplication
-- SHA-256 hex digest of the original (pre-encryption) file bytes

ALTER TABLE document_meta
  ADD COLUMN IF NOT EXISTS file_hash TEXT;

-- Unique constraint: one hash per user prevents duplicate file uploads
CREATE UNIQUE INDEX IF NOT EXISTS document_meta_user_hash_unique
  ON document_meta (user_id, file_hash)
  WHERE file_hash IS NOT NULL;

COMMENT ON COLUMN document_meta.file_hash IS
  'SHA-256 hex digest of original file bytes (computed client-side before encryption). '
  'Used to reject duplicate uploads of the same document content.';
