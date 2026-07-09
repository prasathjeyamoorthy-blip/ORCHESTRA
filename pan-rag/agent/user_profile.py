# agent/user_profile.py
"""
User profile management for storing and retrieving PAN application details.
Integrates with Supabase to persist user information across sessions.
"""
import os
import json
from typing import Optional, Dict, Any
from supabase import create_client, Client

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user profile from Supabase.
    
    Args:
        user_id: The Supabase auth user ID
        
    Returns:
        Dictionary containing user profile data, or None if not found
    """
    if not supabase or not user_id:
        print(f"[user_profile] Cannot fetch profile: supabase={bool(supabase)}, user_id={user_id}")
        return None
    
    try:
        print(f"[user_profile] Fetching profile from Supabase for user {user_id}")
        response = supabase.table("user_profiles").select("*").eq("user_id", user_id).execute()
        
        print(f"[user_profile] Supabase response: {response.data}")
        
        if response.data and len(response.data) > 0:
            profile = response.data[0]
            print(f"[user_profile] Found profile: full_name={profile.get('full_name')}, mother_name={profile.get('mother_name')}, annual_income={profile.get('annual_income')}")
            return profile
        
        print(f"[user_profile] No profile found in Supabase for user {user_id}")
        return None
    except Exception as e:
        print(f"[user_profile] Error fetching profile for {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_user_profile(user_id: str, profile_data: Dict[str, Any]) -> bool:
    """
    Save or update user profile in Supabase.
    
    Args:
        user_id: The Supabase auth user ID
        profile_data: Dictionary containing profile fields to save
        
    Returns:
        True if successful, False otherwise
    """
    if not supabase or not user_id:
        return False
    
    try:
        # Prepare data — use upsert so we don't need to check existence
        data = {
            "user_id": user_id,
            "updated_at": __import__('datetime').datetime.utcnow().isoformat(),
        }
        if profile_data.get("full_name"):    data["full_name"]    = profile_data["full_name"]
        if profile_data.get("mother_name"):  data["mother_name"]  = profile_data["mother_name"]
        if profile_data.get("email"):        data["email"]        = profile_data["email"]
        if profile_data.get("phone"):        data["phone"]        = profile_data["phone"]
        if profile_data.get("mobile"):       data["phone"]        = profile_data["mobile"]   # mobile → phone column
        if profile_data.get("title"):
            # Store title inside pan_preferences JSONB since there's no dedicated column
            pan_prefs = profile_data.get("pan_preferences") or {}
            if isinstance(pan_prefs, dict):
                pan_prefs["title"] = profile_data["title"]
            profile_data["pan_preferences"] = pan_prefs
        if profile_data.get("salary") or profile_data.get("annual_income"):
            data["annual_income"] = profile_data.get("salary") or profile_data.get("annual_income")

        # Always save pan_preferences if present (even if some values are False)
        pan_prefs = profile_data.get("pan_preferences")
        if pan_prefs:
            # Remove None values from pan_prefs but keep False booleans
            clean_prefs = {k: v for k, v in pan_prefs.items() if v is not None}
            if clean_prefs:
                data["pan_preferences"] = clean_prefs

        supabase.table("user_profiles").upsert(data, on_conflict="user_id").execute()
        print(f"[user_profile] Saved profile for user {user_id}: {list(data.keys())}")
        return True

    except Exception as e:
        print(f"[user_profile] Error saving profile for {user_id}: {e}")
        return False


def extract_pan_preferences(flow_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract PAN application preferences from flow state.
    
    Args:
        flow_state: The flow manager state dictionary
        
    Returns:
        Dictionary containing PAN preferences
    """
    return {
        "submission_mode": flow_state.get("submission_mode"),
        "delivery_mode": flow_state.get("delivery_mode"),
        "aadhaar_photo": flow_state.get("aadhaar_photo"),
        "source_of_income": flow_state.get("source_of_income"),
        "address_for_comm": flow_state.get("address_for_comm"),
        "residential_status": flow_state.get("residential_status"),
        "rep_assessee": flow_state.get("rep_assessee"),
        "applicant_type": flow_state.get("applicant_type"),
    }


def save_flow_to_profile(user_id: str, flow_state: Dict[str, Any]) -> bool:
    """
    Save flow state to user profile in Supabase.
    
    Args:
        user_id: The Supabase auth user ID
        flow_state: The complete flow state from FlowManager
        
    Returns:
        True if successful, False otherwise
    """
    profile_data = {
        "full_name": flow_state.get("full_name"),
        "mother_name": flow_state.get("mother_name"),
        "email": flow_state.get("email"),
        "phone": flow_state.get("mobile") or flow_state.get("phone"),
        "salary": flow_state.get("salary"),
        "pan_preferences": {
            **extract_pan_preferences(flow_state),
            "title": flow_state.get("title"),
        },
    }
    
    return save_user_profile(user_id, profile_data)


def prefill_flow_from_profile(user_id: str, flow_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prefill flow state with data from user profile.
    
    Args:
        user_id: The Supabase auth user ID
        flow_state: The current flow state to prefill
        
    Returns:
        Updated flow state with prefilled data
    """
    profile = get_user_profile(user_id)
    
    print(f"[user_profile] Loading profile for user {user_id}")
    print(f"[user_profile] Profile data: {profile}")
    
    if not profile:
        print(f"[user_profile] No profile found for user {user_id}")
        return flow_state
    
    # Prefill personal details only (not application preferences).
    # Prefilling submission_mode / delivery_mode / aadhaar_photo / etc. into an
    # active flow causes advance_step() to skip those questions and jump straight
    # to the documents step — the user never gets asked them.
    if not flow_state.get("full_name") and profile.get("full_name"):
        flow_state["full_name"] = profile["full_name"]
        print(f"[user_profile] Prefilled full_name: {profile['full_name']}")
    
    if not flow_state.get("mother_name") and profile.get("mother_name"):
        flow_state["mother_name"] = profile["mother_name"]
        print(f"[user_profile] Prefilled mother_name: {profile['mother_name']}")
    
    if not flow_state.get("grandfather_name") and profile.get("grandfather_name"):
        flow_state["grandfather_name"] = profile["grandfather_name"]
        print(f"[user_profile] Prefilled grandfather_name: {profile['grandfather_name']}")

    if not flow_state.get("email") and profile.get("email"):
        flow_state["email"] = profile["email"]
        flow_state["email_source"] = "profile"
        print(f"[user_profile] Prefilled email: {profile['email']}")
    
    if not flow_state.get("phone") and profile.get("phone"):
        flow_state["phone"] = profile["phone"]
        print(f"[user_profile] Prefilled phone: {profile['phone']}")

    if not flow_state.get("mobile") and profile.get("mobile"):
        flow_state["mobile"] = profile["mobile"]
        print(f"[user_profile] Prefilled mobile: {profile['mobile']}")

    if not flow_state.get("title") and profile.get("title"):
        flow_state["title"] = profile["title"]
        print(f"[user_profile] Prefilled title: {profile['title']}")
    
    if not flow_state.get("salary") and profile.get("annual_income"):
        flow_state["salary"] = profile["annual_income"]
        print(f"[user_profile] Prefilled salary: {profile['annual_income']}")

    # NOTE: pan_preferences (submission_mode, delivery_mode, aadhaar_photo, etc.)
    # are intentionally NOT prefilled here. They are asked explicitly each session
    # via the bulk-review / saved-preferences prompt so the user can change them.
    # Silently loading them would skip the questions and send the user to documents.

    return flow_state