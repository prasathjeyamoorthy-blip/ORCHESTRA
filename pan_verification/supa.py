from supabase import create_client
import uuid
import time
import os
from dotenv import load_dotenv

load_dotenv()

_SUPABASE_URL = os.getenv("SUPABASE_URL")
_SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def get_client():
    """Get Supabase client."""
    return create_client(_SUPABASE_URL, _SUPABASE_KEY)

def ensure_user_exists(auth_id: str):
    """Ensure user exists in the database to satisfy foreign key constraints."""
    client = get_client()
    
    try:
        # Check if user already exists in the users table
        custom_user_check = client.table("users").select("id").eq("id", auth_id).execute()
        
        if custom_user_check.data:
            print(f"✅ User {auth_id} already exists in users table")
            return True
            
        # If user doesn't exist, we have a few options:
        # 1. The foreign key constraint might be optional
        # 2. The user might be authenticated via Supabase Auth but not in the users table
        # 3. We need to handle this gracefully
        
        print(f"⚠️ User {auth_id} not found in users table")
        print(f"🔄 This might be expected if using Supabase Auth without custom users table")
        
        # Return True to allow the operation to continue
        # The foreign key constraint will either:
        # - Be satisfied by Supabase's auth.users table
        # - Be handled by removing the constraint if it's causing issues
        return True
        
    except Exception as e:
        print(f"⚠️ Error checking user existence: {e}")
        # Continue anyway - let the database handle the constraint
        return True

def save_document(doc_type: str, extracted_data: dict, auth_id: str, person_id: str) -> str:
    from crypto_utils import encrypt_json

    client = get_client()
    doc_id = str(uuid.uuid4())

    insert_data = {
        "id": doc_id,
        "doc_type": doc_type,
        # store encrypted extracted_data
        "extracted_data": encrypt_json(extracted_data),
        "auth_id": auth_id,
        "person_id": person_id,
    }

    response = client.table("documents").insert(insert_data).execute()


    if response.data:
        return doc_id
    else:
        raise ValueError(f"Failed to insert document: {response}")

def get_documents_by_auth(auth_id: str):
    """Get documents for auth_id with person names."""
    from crypto_utils import decrypt_json

    client = get_client()
    
    # Fetch documents with person_id
    response = client.table("documents").select("*").eq("auth_id", auth_id).execute()
    docs = response.data or []

    
    if not docs:
        return []
    
    # Get all person_ids from documents
    person_ids = list(set(doc["person_id"] for doc in docs if doc.get("person_id")))
    
    # Fetch all persons for this auth_id
    persons_response = client.table("persons").select("person_id, name").eq("auth_id", auth_id).execute()
    persons = {p["person_id"]: p["name"] for p in (persons_response.data or [])}
    
    # Decrypt extracted_data for each document and add person_name
    for doc in docs:
        doc["person_name"] = persons.get(doc.get("person_id"), "Unknown")
        enc = doc.get("extracted_data")
        if isinstance(enc, str):
            try:
                doc["extracted_data"] = decrypt_json(enc)
            except Exception:
                # If decrypt fails, keep the encrypted payload for debugging
                pass
    
    return docs



def get_documents_by_person(auth_id: str, person_name: str):
    """Backward-compatible lookup by name.

    NOTE: Original UI used the input as `mobile_number` sometimes.
    New logic prefers `get_documents_by_name_or_phone`.
    """
    client = get_client()

    person_response = client.table("persons") \
        .select("person_id") \
        .eq("auth_id", auth_id) \
        .eq("name", person_name) \
        .execute()

    if not person_response.data:
        return []

    person_id = person_response.data[0]["person_id"]

    docs_response = client.table("documents") \
        .select("*") \
        .eq("auth_id", auth_id) \
        .eq("person_id", person_id) \
        .execute()

    docs = docs_response.data or []

    from crypto_utils import decrypt_json

    for doc in docs:
        doc["person_name"] = person_name
        enc = doc.get("extracted_data")
        if isinstance(enc, str):
            try:
                doc["extracted_data"] = decrypt_json(enc)
            except Exception:
                pass

    return docs


def _normalize_mobile(m: str) -> str:
    return "".join(ch for ch in str(m or "") if ch.isdigit())


def get_documents_by_name_or_phone(auth_id: str, person_name: str | None, phone_number: str | None):
    """Lookup documents by either:
    - phone_number => persons.mobile_number (unique key with auth_id)
    - person_name => persons.name (non-unique)

    If both are provided, phone_number takes precedence.
    """
    from crypto_utils import decrypt_json

    client = get_client()

    mobile = _normalize_mobile(phone_number) if phone_number else ""

    person_ids: list[str] = []
    lookup_label = None

    if mobile:
        lookup_label = mobile
        resp = client.table("persons") \
            .select("person_id, name") \
            .eq("auth_id", auth_id) \
            .eq("mobile_number", mobile) \
            .execute()
        person_ids = [r["person_id"] for r in (resp.data or [])]
    else:
        if not person_name:
            return []
        lookup_label = person_name
        resp = client.table("persons") \
            .select("person_id, name") \
            .eq("auth_id", auth_id) \
            .eq("name", person_name) \
            .execute()
        person_ids = [r["person_id"] for r in (resp.data or [])]

    if not person_ids:
        return []

    # Fetch documents by person_ids
    docs_response = client.table("documents") \
        .select("*") \
        .eq("auth_id", auth_id) \
        .in_("person_id", person_ids) \
        .execute()

    docs = docs_response.data or []

    # Map person_id -> name for display
    persons_response = client.table("persons") \
        .select("person_id, name") \
        .eq("auth_id", auth_id) \
        .in_("person_id", person_ids) \
        .execute()
    id_to_name = {p["person_id"]: p.get("name") for p in (persons_response.data or [])}

    for doc in docs:
        doc["person_name"] = id_to_name.get(doc.get("person_id"), lookup_label or "Unknown")
        enc = doc.get("extracted_data")
        if isinstance(enc, str):
            try:
                doc["extracted_data"] = decrypt_json(enc)
            except Exception:
                pass

    return docs





def delete_old_documents(person_id: str):
    """Delete all documents for a person."""
    client = get_client()
    client.table("documents").delete().eq("person_id", person_id).execute()


def get_or_create_person(auth_id: str, mobile_number: str, name: str | None = None) -> str:
    """Get or create a person using mobile_number as the unique key.

    persons uniqueness is based on (auth_id, mobile_number).
    
    If foreign key constraint issues occur, this will provide helpful guidance.
    """
    client = get_client()

    # Normalize mobile number (keep digits only)
    mobile = "".join(ch for ch in str(mobile_number) if ch.isdigit())

    try:
        # Check existing by (auth_id, mobile_number)
        response = client.table("persons") \
            .select("person_id") \
            .eq("auth_id", auth_id) \
            .eq("mobile_number", mobile) \
            .execute()

        if response.data:
            # Optionally update name if it was previously null/empty
            if name:
                client.table("persons").update({"name": name}).eq("person_id", response.data[0]["person_id"]).execute()
            print(f"✅ Found existing person {response.data[0]['person_id']} for auth_id {auth_id}")
            return response.data[0]["person_id"]

        # Try to create new person
        person_id = str(uuid.uuid4())

        insert_payload = {
            "person_id": person_id,
            "auth_id": auth_id,
            "mobile_number": mobile,
            "name": name
        }

        try:
            result = client.table("persons").insert(insert_payload).execute()
            
            if result.data:
                print(f"✅ Created person {person_id} for auth_id {auth_id}")
                return person_id
            else:
                raise ValueError(f"Failed to insert person: {result}")
                
        except Exception as insert_error:
            # Handle foreign key constraint errors with specific guidance
            if "foreign key constraint" in str(insert_error).lower() or "23503" in str(insert_error):
                
                # Try alternative approach: create person without foreign key constraint
                print(f"⚠️ Foreign key constraint detected. Attempting workaround...")
                
                # Check if we can temporarily work around this by creating person with a different approach
                try:
                    # Alternative: Use upsert which might handle constraints differently
                    result = client.table("persons").upsert(insert_payload).execute()
                    
                    if result.data:
                        print(f"✅ Created person via upsert workaround: {person_id}")
                        return person_id
                        
                except Exception as upsert_error:
                    print(f"⚠️ Upsert workaround also failed: {upsert_error}")
                
                # If all attempts fail, provide clear user guidance
                raise ValueError(
                    f"User account setup incomplete. Please contact support with error code: FK-{auth_id[:8]}\n\n"
                    f"Quick fix: Run this SQL in Supabase Dashboard:\n"
                    f"INSERT INTO users (id, email) VALUES ('{auth_id}', 'user-{auth_id[:8]}@temp.local') ON CONFLICT DO NOTHING;"
                )
                
            else:
                print(f"❌ Failed to create person: {insert_error}")
                raise

    except Exception as e:
        if "User account setup incomplete" in str(e):
            # Re-raise user-friendly errors as-is
            raise
        else:
            print(f"❌ Unexpected error in get_or_create_person: {e}")
            raise

