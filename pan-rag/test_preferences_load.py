"""
Test script to verify PAN preferences are being saved and loaded correctly.
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from agent.user_profile import get_user_profile, prefill_flow_from_profile

print("=" * 70)
print("PAN Preferences Load Test")
print("=" * 70)

# Get user ID from command line
if len(sys.argv) < 2:
    print("\nUsage: python test_preferences_load.py <user_id>")
    print("\nTo find your user_id, check the Python RAG agent logs when you send a message.")
    print("Look for: [DEBUG] Loading profile for user <user_id>")
    exit(1)

user_id = sys.argv[1]
print(f"\nTesting for user: {user_id}")

# Step 1: Load profile from Supabase
print("\n" + "─" * 70)
print("Step 1: Loading profile from Supabase")
print("─" * 70)

profile = get_user_profile(user_id)

if not profile:
    print("❌ No profile found in Supabase")
    print("   This user hasn't saved any data yet.")
    exit(1)

print("✅ Profile found!")

# Step 2: Check personal details
print("\n" + "─" * 70)
print("Step 2: Personal Details")
print("─" * 70)

personal_fields = ["full_name", "mother_name", "email", "phone", "annual_income", "date_of_birth"]
for field in personal_fields:
    value = profile.get(field)
    if value:
        print(f"  ✅ {field}: {value}")
    else:
        print(f"  ❌ {field}: NOT SET")

# Step 3: Check PAN preferences
print("\n" + "─" * 70)
print("Step 3: PAN Preferences (from pan_preferences JSONB)")
print("─" * 70)

pan_prefs = profile.get("pan_preferences", {})
if isinstance(pan_prefs, str):
    import json
    try:
        pan_prefs = json.loads(pan_prefs)
    except:
        pan_prefs = {}

if not pan_prefs:
    print("❌ No PAN preferences found")
    print("   User hasn't completed a PAN application yet.")
else:
    print(f"✅ Found {len(pan_prefs)} preference(s):")
    
    pref_fields = [
        "applicant_type",
        "submission_mode",
        "delivery_mode",
        "aadhaar_photo",
        "source_of_income",
        "address_for_comm",
        "residential_status",
        "rep_assessee",
    ]
    
    for field in pref_fields:
        value = pan_prefs.get(field)
        if value is not None:
            print(f"  ✅ {field}: {value}")
        else:
            print(f"  ❌ {field}: NOT SET")

# Step 4: Test prefill logic
print("\n" + "─" * 70)
print("Step 4: Testing Prefill Logic")
print("─" * 70)

flow_state = {}
flow_state = prefill_flow_from_profile(user_id, flow_state)

print(f"\nFlow state after prefill:")
print(f"  Personal details:")
print(f"    - full_name: {flow_state.get('full_name')}")
print(f"    - mother_name: {flow_state.get('mother_name')}")
print(f"    - email: {flow_state.get('email')}")
print(f"    - salary: {flow_state.get('salary')}")

print(f"\n  PAN preferences:")
print(f"    - applicant_type: {flow_state.get('applicant_type')}")
print(f"    - submission_mode: {flow_state.get('submission_mode')}")
print(f"    - delivery_mode: {flow_state.get('delivery_mode')}")
print(f"    - aadhaar_photo: {flow_state.get('aadhaar_photo')}")
print(f"    - source_of_income: {flow_state.get('source_of_income')}")
print(f"    - address_for_comm: {flow_state.get('address_for_comm')}")
print(f"    - residential_status: {flow_state.get('residential_status')}")
print(f"    - rep_assessee: {flow_state.get('rep_assessee')}")

# Step 5: Check what would be asked
print("\n" + "─" * 70)
print("Step 5: What Questions Would Be Asked?")
print("─" * 70)

missing_prefs = []
if not flow_state.get("applicant_type"):
    missing_prefs.append("Applicant type")
if not flow_state.get("submission_mode"):
    missing_prefs.append("Submission mode")
if not flow_state.get("delivery_mode"):
    missing_prefs.append("Delivery mode")
if flow_state.get("aadhaar_photo") is None:
    missing_prefs.append("Aadhaar photo on PAN")
if not flow_state.get("source_of_income"):
    missing_prefs.append("Source of income")
if not flow_state.get("address_for_comm"):
    missing_prefs.append("Address for communication")
if not flow_state.get("residential_status"):
    missing_prefs.append("Residential status")
if flow_state.get("rep_assessee") is None:
    missing_prefs.append("Representative Assessee")

if missing_prefs:
    print(f"❌ Agent will ask for {len(missing_prefs)} preference(s):")
    for pref in missing_prefs:
        print(f"   - {pref}")
else:
    print("✅ All preferences loaded! Agent should skip all preference questions.")

# Step 6: Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

if not pan_prefs:
    print("\n❌ PROBLEM: No PAN preferences in database")
    print("   CAUSE: User hasn't completed a PAN application yet, OR")
    print("          Preferences aren't being saved properly")
    print("\n   SOLUTION: Complete one PAN application and check again")
elif missing_prefs:
    print(f"\n⚠️  PROBLEM: Some preferences missing ({len(missing_prefs)}/{len(pref_fields)})")
    print("   CAUSE: Preferences in database but not being loaded correctly")
    print("\n   SOLUTION: Check prefill_flow_from_profile() logic")
else:
    print("\n✅ SUCCESS: All preferences loaded correctly!")
    print("   Agent should skip all preference questions in new applications")

print("\n" + "=" * 70)
