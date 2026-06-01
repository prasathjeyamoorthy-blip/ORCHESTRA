#!/usr/bin/env python3
"""
Test Supabase connection and user_profiles table access.
Run this to diagnose profile persistence issues.
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

print("=" * 70)
print("SUPABASE CONNECTION TEST")
print("=" * 70)

# Check environment variables
print("\n1. Checking environment variables...")
if not SUPABASE_URL:
    print("❌ SUPABASE_URL not found in .env")
    sys.exit(1)
if not SUPABASE_SERVICE_KEY:
    print("❌ SUPABASE_SERVICE_KEY not found in .env")
    sys.exit(1)

print(f"✅ SUPABASE_URL: {SUPABASE_URL}")
print(f"✅ SUPABASE_SERVICE_KEY: {SUPABASE_SERVICE_KEY[:30]}...")

# Create Supabase client
print("\n2. Creating Supabase client...")
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    print("✅ Supabase client created")
except Exception as e:
    print(f"❌ Failed to create client: {e}")
    sys.exit(1)

# Test table access
print("\n3. Testing user_profiles table access...")
try:
    response = supabase.table("user_profiles").select("*").limit(1).execute()
    print(f"✅ Table access successful")
    print(f"   Rows returned: {len(response.data)}")
    if response.data:
        print(f"   Sample row keys: {list(response.data[0].keys())}")
except Exception as e:
    print(f"❌ Table access failed: {e}")
    print("\n   Possible causes:")
    print("   - Table doesn't exist (run migrations)")
    print("   - RLS policies blocking access")
    print("   - Wrong credentials")

# Test schema
print("\n4. Checking table schema...")
try:
    # Try to get column info by attempting an insert with all expected columns
    test_user_id = "00000000-0000-0000-0000-000000000000"
    test_data = {
        "user_id": test_user_id,
        "full_name": "Schema Test",
        "mother_name": "Test Mother",
        "email": "test@example.com",
        "phone": "+1234567890",
        "annual_income": "₹100,000",
        "pan_preferences": {"test": True}
    }
    
    response = supabase.table("user_profiles").upsert(test_data, on_conflict="user_id").execute()
    print("✅ All expected columns exist:")
    print("   - user_id")
    print("   - full_name")
    print("   - mother_name")
    print("   - email")
    print("   - phone")
    print("   - annual_income ✓")
    print("   - pan_preferences")
    
    # Clean up test data
    supabase.table("user_profiles").delete().eq("user_id", test_user_id).execute()
    print("✅ Test data cleaned up")
    
except Exception as e:
    print(f"❌ Schema check failed: {e}")
    error_str = str(e)
    if "annual_income" in error_str:
        print("\n   ⚠️  CRITICAL: 'annual_income' column is missing!")
        print("   Run this SQL in Supabase dashboard:")
        print("   ALTER TABLE public.user_profiles ADD COLUMN annual_income TEXT;")
    elif "user_profiles" in error_str and "does not exist" in error_str:
        print("\n   ⚠️  CRITICAL: 'user_profiles' table doesn't exist!")
        print("   Run the migration: supabase/migrations/20240104000000_add_user_profiles.sql")

# Test with actual user ID
print("\n5. Testing with your actual user ID...")
actual_user_id = "4d31252d-2e59-45b2-9788-5b8b16a5072b"
try:
    response = supabase.table("user_profiles").select("*").eq("user_id", actual_user_id).execute()
    if response.data:
        print(f"✅ Found profile for user {actual_user_id[:8]}...")
        profile = response.data[0]
        print(f"   full_name: {profile.get('full_name')}")
        print(f"   mother_name: {profile.get('mother_name')}")
        print(f"   email: {profile.get('email')}")
        print(f"   annual_income: {profile.get('annual_income')}")
        print(f"   pan_preferences: {profile.get('pan_preferences')}")
    else:
        print(f"⚠️  No profile found for user {actual_user_id[:8]}...")
        print("   This is expected if you haven't completed a PAN application yet")
except Exception as e:
    print(f"❌ Query failed: {e}")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
print("\nNext steps:")
print("1. If 'annual_income' column is missing, add it to the database")
print("2. If table doesn't exist, run the migration SQL")
print("3. If RLS is blocking, check policies or temporarily disable RLS")
print("4. Restart RAG server after fixing database issues")
print("=" * 70)
