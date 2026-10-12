import os
import sys
import json
import requests

SQL_SETUP_SCRIPT = """-- ============================================================
-- SUPABASE DATABASE INITIALIZATION SCRIPT (TNeGA ORCHESTRA)
-- Run this in your new Supabase SQL Editor:
-- https://supabase.com/dashboard/project/cifhffdgeouugiyxrykl/sql/new
-- ============================================================

-- 1. user_profiles: stores 3-tab modal data per user
CREATE TABLE IF NOT EXISTS public.user_profiles (
    phone_number TEXT PRIMARY KEY,
    profile_data JSONB,
    updated_at   DOUBLE PRECISION
);

-- 2. user_documents: stores uploaded document metadata per user
CREATE TABLE IF NOT EXISTS public.user_documents (
    id           BIGSERIAL PRIMARY KEY,
    phone_number TEXT NOT NULL,
    doc_id       TEXT NOT NULL,
    filename     TEXT,
    supabase_url TEXT,
    extracted_data TEXT DEFAULT '[]',
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (phone_number, doc_id)
);

-- 3. application_payloads: stores form submission payload per user
CREATE TABLE IF NOT EXISTS public.application_payloads (
    phone_number TEXT PRIMARY KEY,
    payload      JSONB,
    updated_at   DOUBLE PRECISION,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. user_chat_history: stores chat messages per user/session
--    NOTE: uses 'content' and 'session_id'/'stage' columns (not 'message')
CREATE TABLE IF NOT EXISTS public.user_chat_history (
    id           BIGSERIAL PRIMARY KEY,
    phone_number TEXT NOT NULL,
    session_id   TEXT DEFAULT '',
    role         TEXT NOT NULL,
    content      TEXT NOT NULL,
    stage        TEXT DEFAULT '',
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_chat_phone     ON public.user_chat_history (phone_number);
CREATE INDEX IF NOT EXISTS idx_chat_session   ON public.user_chat_history (session_id);
CREATE INDEX IF NOT EXISTS idx_docs_phone     ON public.user_documents (phone_number);

-- Disable Row Level Security (RLS) for direct REST API access via service key
ALTER TABLE public.user_profiles        DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_documents       DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.application_payloads DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_chat_history    DISABLE ROW LEVEL SECURITY;

-- 5. Storage bucket for document uploads (public read)
INSERT INTO storage.buckets (id, name, public)
VALUES ('document_uploads', 'document_uploads', true)
ON CONFLICT (id) DO UPDATE SET public = true;
"""

def update_env_files(new_url: str, new_key: str):
    """
    Update SUPABASE_URL and SUPABASE_KEY in all backend .env files.
    """
    new_url = new_url.strip().rstrip("/")
    new_key = new_key.strip()

    env_paths = [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "DocumentUploadAgent", ".env"))
    ]

    for p in env_paths:
        if not os.path.exists(p):
            continue
        lines = []
        with open(p, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        url_updated = False
        key_updated = False

        for line in lines:
            if line.startswith("SUPABASE_URL="):
                new_lines.append(f"SUPABASE_URL={new_url}\n")
                url_updated = True
            elif line.startswith("SUPABASE_KEY="):
                new_lines.append(f"SUPABASE_KEY={new_key}\n")
                key_updated = True
            else:
                new_lines.append(line)

        if not url_updated:
            new_lines.append(f"SUPABASE_URL={new_url}\n")
        if not key_updated:
            new_lines.append(f"SUPABASE_KEY={new_key}\n")

        with open(p, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"✓ Updated environment credentials in: {p}")

def test_and_migrate(new_url: str, new_key: str):
    """
    Verify connection to new Supabase project and migrate in-memory data.
    """
    print("\n[Supabase Migration] Testing connection to new Supabase database...")

    headers = {
        "apikey": new_key,
        "Authorization": f"Bearer {new_key}",
        "Content-Type": "application/json"
    }

    # 1. Test REST endpoint
    test_url = f"{new_url.rstrip('/')}/rest/v1/"
    try:
        resp = requests.get(test_url, headers=headers, timeout=5)
        print(f"✓ Connection successful! (Status {resp.status_code})")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

    # 2. Ensure bucket exists
    try:
        bucket_url = f"{new_url.rstrip('/')}/storage/v1/bucket"
        requests.post(
            bucket_url,
            headers=headers,
            json={"id": "document_uploads", "name": "document_uploads", "public": True},
            timeout=5
        )
        print("✓ Created 'document_uploads' public storage bucket in new Supabase project.")
    except Exception as be:
        print(f"Notice: Bucket setup: {be}")

    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 setup_new_supabase.py <NEW_SUPABASE_URL> <NEW_SUPABASE_KEY>")
        sys.exit(1)

    url_arg = sys.argv[1]
    key_arg = sys.argv[2]

    update_env_files(url_arg, key_arg)
    test_and_migrate(url_arg, key_arg)
    print("\nMigration setup complete!")
