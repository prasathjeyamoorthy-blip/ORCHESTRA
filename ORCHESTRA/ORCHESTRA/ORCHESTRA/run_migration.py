"""
One-time database migration script for TNeGA ORCHESTRA Supabase project.
Run this once to create all required tables and storage bucket.
"""
import os
import requests
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path, override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ SUPABASE_URL or SUPABASE_KEY missing in .env")
    exit(1)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

SQL_STATEMENTS = [
    # 1. user_profiles
    """
    CREATE TABLE IF NOT EXISTS public.user_profiles (
        phone_number TEXT PRIMARY KEY,
        profile_data JSONB,
        updated_at DOUBLE PRECISION
    );
    """,
    # 2. user_documents
    """
    CREATE TABLE IF NOT EXISTS public.user_documents (
        id BIGSERIAL PRIMARY KEY,
        phone_number TEXT NOT NULL,
        doc_id TEXT NOT NULL,
        filename TEXT,
        supabase_url TEXT,
        extracted_data JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """,
    # 3. application_payloads
    """
    CREATE TABLE IF NOT EXISTS public.application_payloads (
        phone_number TEXT PRIMARY KEY,
        payload JSONB,
        updated_at DOUBLE PRECISION,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """,
    # 4. user_chat_history
    """
    CREATE TABLE IF NOT EXISTS public.user_chat_history (
        id BIGSERIAL PRIMARY KEY,
        phone_number TEXT NOT NULL,
        session_id TEXT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        stage TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """,
    # 5. Disable RLS on all tables
    "ALTER TABLE public.user_profiles DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE public.user_documents DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE public.application_payloads DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE public.user_chat_history DISABLE ROW LEVEL SECURITY;",
]

def run_sql(sql: str, label: str):
    url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
    # Use the pg/query endpoint for DDL
    url = f"{SUPABASE_URL}/pg/query"
    try:
        resp = requests.post(url, headers=HEADERS, json={"query": sql.strip()}, timeout=10)
        if resp.status_code in (200, 201):
            print(f"  ✓ {label}")
            return True
        else:
            # Try alternate endpoint
            url2 = f"{SUPABASE_URL}/rest/v1/rpc/query"
            resp2 = requests.post(url2, headers=HEADERS, json={"sql": sql.strip()}, timeout=10)
            if resp2.status_code in (200, 201):
                print(f"  ✓ {label}")
                return True
            print(f"  ⚠ {label} → HTTP {resp.status_code}: {resp.text[:120]}")
            return False
    except Exception as e:
        print(f"  ✗ {label} → {e}")
        return False

def create_storage_bucket():
    url = f"{SUPABASE_URL}/storage/v1/bucket"
    try:
        resp = requests.post(
            url,
            headers=HEADERS,
            json={"id": "document_uploads", "name": "document_uploads", "public": True},
            timeout=10
        )
        if resp.status_code in (200, 201):
            print("  ✓ Storage bucket 'document_uploads' created")
        elif resp.status_code == 409:
            print("  ✓ Storage bucket 'document_uploads' already exists")
        else:
            print(f"  ⚠ Storage bucket → HTTP {resp.status_code}: {resp.text[:120]}")
    except Exception as e:
        print(f"  ✗ Storage bucket → {e}")

def test_connection():
    url = f"{SUPABASE_URL}/rest/v1/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            print(f"✓ Connected to Supabase: {SUPABASE_URL}")
            return True
        else:
            print(f"✗ Connection failed ({resp.status_code}): {resp.text[:120]}")
            return False
    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False

if __name__ == "__main__":
    print("\n=== TNeGA ORCHESTRA — Supabase Migration ===\n")

    if not test_connection():
        exit(1)

    print("\n[1] Creating tables...")
    labels = [
        "user_profiles table",
        "user_documents table",
        "application_payloads table",
        "user_chat_history table",
        "Disable RLS: user_profiles",
        "Disable RLS: user_documents",
        "Disable RLS: application_payloads",
        "Disable RLS: user_chat_history",
    ]
    for sql, label in zip(SQL_STATEMENTS, labels):
        run_sql(sql, label)

    print("\n[2] Creating storage bucket...")
    create_storage_bucket()

    print("\n=== Migration complete! ===")
    print("→ If any table creation shows a warning, run the SQL manually in:")
    print(f"  https://supabase.com/dashboard/project/cifhffdgeouugiyxrykl/sql/new\n")
