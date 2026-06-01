"""
Test script to verify profile loading from Supabase.
Run this to check if the profile data exists and can be loaded.
"""

import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

print("=" * 60)
print("Profile Load Test")
print("=" * 60)

# Check environment variables
print(f"\n1. Environment Variables:")
print(f"   SUPABASE_URL: {SUPABASE_URL[:30]}..." if SUPABASE_URL else "   SUPABASE_URL: NOT SET")
print(f"   SUPABASE_KEY: {'SET' if SUPABASE_KEY else 'NOT SET'}")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("\n❌ ERROR: Supabase credentials not found in .env file")
    print("   Please add SUPABASE_URL and SUPABASE_SERVICE_KEY to pan-rag/.env")
    exit(1)

# Create Supabase client
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("\n2. Supabase Connection: ✅ Connected")
except Exception as e:
    print(f"\n2. Supabase Connection: ❌ Failed - {e}")
    exit(1)

# Get user ID from command line or use test ID
import sys
if len(sys.argv) > 1:
    user_id = sys.argv[1]
else:
    print("\n3. User ID: Not provided")
    print("   Usage: python test_profile_load.py <user_id>")
    print("   Listing all profiles instead...")
    
    try:
        response = supabase.table("user_profiles").select("user_id, full_name, mother_name, email, annual_income, updated_at").execute()
        
        if response.data:
            print(f"\n   Found {len(response.data)} profile(s):")
            for profile in response.data:
                print(f"\n   User ID: {profile.get('user_id')}")
                print(f"   Full name: {profile.get('full_name')}")
                print(f"   Mother name: {profile.get('mother_name')}")
                print(f"   Email: {profile.get('email')}")
                print(f"   Annual income: {profile.get('annual_income')}")
                print(f"   Updated: {profile.get('updated_at')}")
        else:
            print("\n   ❌ No profiles found in database")
    except Exception as e:
        print(f"\n   ❌ Error listing profiles: {e}")
    
    exit(0)

print(f"\n3. User ID: {user_id}")

# Fetch profile
try:
    print(f"\n4. Fetching profile from Supabase...")
    response = supabase.table("user_profiles").select("*").eq("user_id", user_id).execute()
    
    print(f"   Response data: {response.data}")
    
    if response.data and len(response.data) > 0:
        profile = response.data[0]
        print(f"\n✅ Profile found!")
        print(f"\n   Personal Details:")
        print(f"   - Full name: {profile.get('full_name')}")
        print(f"   - Mother name: {profile.get('mother_name')}")
        print(f"   - Email: {profile.get('email')}")
        print(f"   - Phone: {profile.get('phone')}")
        print(f"   - Annual income: {profile.get('annual_income')}")
        print(f"   - Date of birth: {profile.get('date_of_birth')}")
        
        pan_prefs = profile.get('pan_preferences', {})
        if pan_prefs:
            print(f"\n   PAN Preferences:")
            for key, value in pan_prefs.items():
                print(f"   - {key}: {value}")
        
        print(f"\n   Metadata:")
        print(f"   - Created: {profile.get('created_at')}")
        print(f"   - Updated: {profile.get('updated_at')}")
        
        # Test prefill logic
        print(f"\n5. Testing Prefill Logic:")
        flow_state = {}
        
        if profile.get("full_name"):
            flow_state["full_name"] = profile["full_name"]
            print(f"   ✅ Would prefill full_name: {profile['full_name']}")
        else:
            print(f"   ❌ full_name not in profile")
        
        if profile.get("mother_name"):
            flow_state["mother_name"] = profile["mother_name"]
            print(f"   ✅ Would prefill mother_name: {profile['mother_name']}")
        else:
            print(f"   ❌ mother_name not in profile")
        
        if profile.get("annual_income"):
            flow_state["salary"] = profile["annual_income"]
            print(f"   ✅ Would prefill salary: {profile['annual_income']}")
        else:
            print(f"   ❌ annual_income not in profile")
        
        if profile.get("email"):
            flow_state["email"] = profile["email"]
            print(f"   ✅ Would prefill email: {profile['email']}")
        else:
            print(f"   ❌ email not in profile")
        
        print(f"\n6. Result:")
        print(f"   Flow state after prefill: {flow_state}")
        
        if flow_state.get("full_name") and flow_state.get("mother_name") and flow_state.get("salary"):
            print(f"\n✅ SUCCESS: All required fields would be prefilled!")
            print(f"   Agent should NOT ask for these details in new session.")
        else:
            print(f"\n⚠️  WARNING: Some required fields missing!")
            print(f"   Agent will ask for missing fields.")
    else:
        print(f"\n❌ No profile found for user {user_id}")
        print(f"   This user has not saved any profile data yet.")
        print(f"   Agent will ask for all details.")
        
except Exception as e:
    print(f"\n❌ Error fetching profile: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
