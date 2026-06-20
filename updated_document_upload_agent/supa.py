from supabase import create_client
import uuid

url = "https://vnaeznlgijnarwqrwdtz.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZuYWV6bmxnaWpuYXJ3cXJ3ZHR6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY1Mjk4OTQsImV4cCI6MjA5MjEwNTg5NH0.kw8jhS-YErCJgDVkSDj6zBrJK3ytLnFS-2f0YR9D6hw"  # backend use

def get_client():
    """Get Supabase client."""
    return create_client(url, key)

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
    """
    client = get_client()

    # Normalize mobile number (keep digits only)
    mobile = "".join(ch for ch in str(mobile_number) if ch.isdigit())

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
        return response.data[0]["person_id"]

    # Create new
    person_id = str(uuid.uuid4())

    insert_payload = {
        "person_id": person_id,
        "auth_id": auth_id,
        "mobile_number": mobile,
        "name": name
    }

    client.table("persons").insert(insert_payload).execute()

    return person_id

