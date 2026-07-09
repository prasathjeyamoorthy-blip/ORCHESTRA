-- pan_extractions table
-- Stores encrypted Aadhaar extraction results permanently.
-- Written on every document upload by pan-rag /upload endpoint.
-- Survives Redis TTL expiry — used as last-resort fallback in finalize-application.
-- Keyed on (auth_id, doc_type) so upsert never duplicates.

CREATE TABLE IF NOT EXISTS pan_extractions (
    id              uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    auth_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    doc_type        text NOT NULL,                -- e.g. 'aadhaar', 'driving_license'
    extracted_data  text NOT NULL,               -- AES-256-GCM encrypted JSON blob
    session_id      text,                         -- session in which document was uploaded
    updated_at      timestamptz DEFAULT now(),
    created_at      timestamptz DEFAULT now(),

    UNIQUE (auth_id, doc_type)                   -- one row per user per doc type
);

-- Index for fast lookup by auth_id
CREATE INDEX IF NOT EXISTS pan_extractions_auth_id_idx
    ON pan_extractions (auth_id);

-- RLS: users can only read/write their own rows
ALTER TABLE pan_extractions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own extractions"
    ON pan_extractions FOR SELECT
    USING (auth.uid() = auth_id);

CREATE POLICY "Service role can do everything"
    ON pan_extractions FOR ALL
    USING (true)
    WITH CHECK (true);
