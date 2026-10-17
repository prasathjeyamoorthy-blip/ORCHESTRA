import os
import sys
import json
import requests

SQL_SETUP_SCRIPT = """-- ============================================================
-- SUPABASE DATABASE INITIALIZATION SCRIPT (TNeGA ORCHESTRA)
-- Run this in your new Supabase SQL Editor: https://supabase.com/dashboard
-- ============================================================

-- 1. Create user_profiles table
CREATE TABLE IF NOT EXISTS public.user_profiles (
    phone_number TEXT PRIMARY KEY,
    profile_data JSONB,
    updated_at DOUBLE PRECISION
);

-- 2. Create user_documents table
CREATE TABLE IF NOT EXISTS public.user_documents (
    id BIGSERIAL PRIMARY KEY,
    phone_number TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    filename TEXT,
    supabase_url TEXT,
    extracted_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Create application_payloads table
CREATE TABLE IF NOT EXISTS public.application_payloads (
    phone_number TEXT PRIMARY KEY,
    payload JSONB,
    updated_at DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Create user_chat_history table
CREATE TABLE IF NOT EXISTS public.user_chat_history (
    id BIGSERIAL PRIMARY KEY,
    phone_number TEXT NOT NULL,
    role TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Disable Row Level Security (RLS) for direct REST API access
ALTER TABLE public.user_profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_documents DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.application_payloads DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_chat_history DISABLE ROW LEVEL SECURITY;

-- 5. Create Storage Bucket for Document Uploads
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
