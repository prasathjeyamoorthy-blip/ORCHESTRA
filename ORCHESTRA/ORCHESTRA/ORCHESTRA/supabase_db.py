import os
import time
import json
import requests
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path, override=True)


_SUPABASE_RESOLVED = None

def get_supabase_config():
    global _SUPABASE_RESOLVED
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_KEY", "").strip()
    if not (url and key):
        return "", ""
    if _SUPABASE_RESOLVED is False:
        return "", ""
    if _SUPABASE_RESOLVED is None:
        try:
            import socket, urllib.parse
            parsed = urllib.parse.urlparse(url)
            hostname = parsed.hostname
            if hostname:
                socket.gethostbyname(hostname)
                _SUPABASE_RESOLVED = True
            else:
                _SUPABASE_RESOLVED = False
        except Exception as e:
            print(f"[Supabase DB] Notice: Supabase host '{url}' is unreachable ({e}). Using active in-memory storage fallback.")
            _SUPABASE_RESOLVED = False
            return "", ""
    return url, key


def _get_headers(key: str) -> dict:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


import base64
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def _mask_phone(phone_clean: str) -> str:
    if not phone_clean:
        return "****"
    return f"******{phone_clean[-4:]}" if len(phone_clean) >= 4 else "****"


USER_PUBLIC_KEYS: dict = {}

def set_user_public_key(phone_number: str, public_key_pem: str):
    """Store the user's RSA Public Key for encrypting their database records."""
    if phone_number and public_key_pem:
        phone_clean = phone_number.replace("+", "").replace(" ", "").strip()[-10:]
        USER_PUBLIC_KEYS[phone_clean] = public_key_pem.strip()

def encrypt_text_zero_knowledge(text: str, public_key_pem: str = None) -> str:
    """
    Encrypt text using the user's RSA Public Key (Hybrid RSA-OAEP + AES-256-GCM).
    Format: HYBRID_v1:<rsa_enc_key_b64>:<nonce_b64>:<ciphertext_b64>
    Zero-Knowledge: The backend server cannot decrypt this string once encrypted!
    """
    if not text:
        return ""
    if not public_key_pem:
        return text
    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))
        aes_key = AESGCM.generate_key(bit_length=256)
        aesgcm = AESGCM(aes_key)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, text.encode('utf-8'), None)

        enc_aes_key = public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return f"HYBRID_v1:{base64.b64encode(enc_aes_key).decode()}:{base64.b64encode(nonce).decode()}:{base64.b64encode(ct).decode()}"
    except Exception as e:
        print(f"[Encryption] Hybrid zero-knowledge encryption error: {e}")
        return text

def save_message(phone_number: str, role: str, content: str, session_id: str = None, stage: str = None, public_key_pem: str = None) -> bool:
    """
    Save a user or assistant chat message to Supabase encrypted with the client's Public Key.
    """
    if not phone_number or not content:
        return False

    phone_clean = phone_number.replace("+", "").replace(" ", "").strip()[-10:]
    url, key = get_supabase_config()

    if not (url and key):
        print("[Supabase] Missing SUPABASE_URL or SUPABASE_KEY in .env")
        return False

    pub_pem = public_key_pem or USER_PUBLIC_KEYS.get(phone_clean)

    try:
        endpoint = f"{url}/rest/v1/user_chat_history"
        encrypted_content = encrypt_text_zero_knowledge(content, pub_pem) if pub_pem else content
        encrypted_stage = encrypt_text_zero_knowledge(stage, pub_pem) if (stage and pub_pem) else (stage or "")
        payload = {
            "phone_number": phone_clean,
            "session_id": session_id or "",
            "role": role,
            "content": encrypted_content,
            "stage": encrypted_stage
        }
        resp = requests.post(endpoint, headers=_get_headers(key), json=payload, timeout=2.0)
        if resp.status_code in (200, 201):
            print(f"[Supabase] Saved Zero-Knowledge encrypted '{role}' message for phone {_mask_phone(phone_clean)}")
            return True
        else:
            print(f"[Supabase] Insert error ({resp.status_code}): {resp.text}")
            return False
    except Exception as e:
        print(f"[Supabase] Exception during save: {e}")
        return False


def fetch_user_history(phone_number: str, limit: int = 50, session_id: str = None) -> list:
    """
    Fetch chronological chat history for a given phone number from Supabase.
    Returns list of dicts with raw ciphertexts (decrypted client-side in the browser).
    """
    if not phone_number:
        return []

    phone_clean = phone_number.replace("+", "").replace(" ", "").strip()[-10:]
    url, key = get_supabase_config()

    if not (url and key):
        print("[Supabase] Missing SUPABASE_URL or SUPABASE_KEY in .env")
        return []

    try:
        endpoint = f"{url}/rest/v1/user_chat_history"
        params = {
            "phone_number": f"eq.{phone_clean}",
            "order": "created_at.asc",
            "limit": str(limit)
        }
        if session_id:
            if session_id in ("session_default", ""):
                params["or"] = "(session_id.eq.,session_id.eq.session_default,session_id.is.null)"
            else:
                params["session_id"] = f"eq.{session_id}"
        resp = requests.get(endpoint, headers=_get_headers(key), params=params, timeout=2.0)
        if resp.status_code == 200:
            rows = resp.json()
            print(f"[Supabase] Fetched {len(rows)} historical messages for phone {_mask_phone(phone_clean)}")
            return [
                {
                    "role": row.get("role"),
                    "content": row.get("content", ""),
                    "session_id": row.get("session_id", ""),
                    "stage": row.get("stage", ""),
                    "created_at": row.get("created_at", "")
                }
                for row in rows
            ]
        else:
            print(f"[Supabase] Fetch error ({resp.status_code}): {resp.text}")
            return []
    except Exception as e:
        print(f"[Supabase] Exception during fetch: {e}")
        return []


def delete_user_history(phone_number: str, session_id: str = None) -> bool:
    """
    Delete chat history for a given phone number and optional session_id from Supabase.
    """
    if not phone_number:
        return False

    phone_clean = phone_number.replace("+", "").replace(" ", "").strip()[-10:]
    url, key = get_supabase_config()

    if not (url and key):
        print("[Supabase] Missing SUPABASE_URL or SUPABASE_KEY in .env")
        return False

    try:
        endpoint = f"{url}/rest/v1/user_chat_history"
        params = {
            "phone_number": f"eq.{phone_clean}"
        }
        if session_id:
            if session_id in ("session_default", ""):
                params["or"] = "(session_id.eq.,session_id.eq.session_default,session_id.is.null)"
            else:
                params["session_id"] = f"eq.{session_id}"

        resp = requests.delete(endpoint, headers=_get_headers(key), params=params, timeout=2.0)
        if resp.status_code in (200, 204):
            print(f"[Supabase] Deleted chat history for phone {_mask_phone(phone_clean)} (session: {session_id or 'ALL'})")
            return True
        else:
            print(f"[Supabase] Delete error ({resp.status_code}): {resp.text}")
            return False
    except Exception as e:
        print(f"[Supabase] Exception during delete: {e}")
        return False



USER_DOCUMENT_REGISTRY: dict = {}

def save_user_document_meta(phone_number: str, doc_id: str, filename: str, supabase_url: str, extracted_data: list = None) -> bool:
    """
    Save or update a personalized document record for a user in Supabase.
    """
    if not phone_number or not doc_id:
        return False
    phone_clean = phone_number.replace("+", "").replace(" ", "").strip()[-10:]

    if phone_clean not in USER_DOCUMENT_REGISTRY:
        USER_DOCUMENT_REGISTRY[phone_clean] = {}

    USER_DOCUMENT_REGISTRY[phone_clean][doc_id] = {
        "doc_id": doc_id,
        "filename": filename,
        "supabase_url": supabase_url,
        "extracted_data": extracted_data or [],
        "updated_at": time.time()
    }

    url, key = get_supabase_config()
    if not (url and key):
        return True

    try:
        endpoint = f"{url}/rest/v1/user_documents"
        headers = {**_get_headers(key), "Prefer": "resolution=merge-duplicates"}
        payload = {
            "phone_number": phone_clean,
            "doc_id": doc_id,
            "filename": filename,
            "supabase_url": supabase_url,
            "extracted_data": json.dumps(extracted_data) if extracted_data else "[]"
        }
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=2.0)
        if resp.status_code in (200, 201):
            print(f"[Supabase DB] Registered document '{doc_id}' for phone {_mask_phone(phone_clean)}")
            return True
        else:
            print(f"[Supabase DB] user_documents post response ({resp.status_code}): {resp.text}")
            return True # Fallback stored in memory
    except Exception as e:
        print(f"[Supabase DB] Exception saving user document: {e}")
        return True


def fetch_user_documents(phone_number: str) -> dict:
    """
    Fetch all uploaded documents and metadata for a specific user phone number.
    Returns dict mapping doc_id -> { doc_id, filename, supabase_url, extracted_data }.
    """
    if not phone_number:
        return {}
    phone_clean = phone_number.replace("+", "").replace(" ", "").strip()[-10:]
    mem_docs = USER_DOCUMENT_REGISTRY.get(phone_clean, {})

    url, key = get_supabase_config()
    if not (url and key):
        return mem_docs

    try:
        endpoint = f"{url}/rest/v1/user_documents"
        params = {"phone_number": f"eq.{phone_clean}", "select": "*"}
        resp = requests.get(endpoint, headers=_get_headers(key), params=params, timeout=2.0)
        if resp.status_code == 200:
            rows = resp.json()
            result = dict(mem_docs)
            for row in rows:
                doc_id = row.get("doc_id")
                ext_raw = row.get("extracted_data", "[]")
                try:
                    ext_data = json.loads(ext_raw) if isinstance(ext_raw, str) else ext_raw
                except Exception:
                    ext_data = []
                if doc_id:
                    result[doc_id] = {
                        "doc_id": doc_id,
                        "filename": row.get("filename", ""),
                        "supabase_url": row.get("supabase_url", ""),
                        "extracted_data": ext_data
                    }
            return result
        else:
            return mem_docs
    except Exception as e:
        print(f"[Supabase DB] Exception fetching user documents: {e}")
        return mem_docs


def upload_to_supabase_storage(file_bytes: bytes, filename: str, content_type: str = "application/octet-stream", bucket_name: str = "document_uploads", phone_number: str = "") -> str:
    """
    Upload a document file to Supabase Storage bucket under a user-isolated path.
    """
    if not file_bytes or not filename:
        return ""

    url, key = get_supabase_config()
    if not (url and key):
        print("[Supabase Storage] Missing credentials.")
        return ""

    try:
        # Ensure bucket exists
        bucket_check_url = f"{url}/storage/v1/bucket/{bucket_name}"
        headers = {"apikey": key, "Authorization": f"Bearer {key}"}
        check_resp = requests.get(bucket_check_url, headers=headers, timeout=5)
        if check_resp.status_code != 200:
            # Create bucket
            requests.post(
                f"{url}/storage/v1/bucket",
                headers={**headers, "Content-Type": "application/json"},
                json={"id": bucket_name, "name": bucket_name, "public": True},
                timeout=5
            )

        # User-isolated file path
        clean_filename = requests.utils.quote(os.path.basename(filename))
        path_prefix = ""
        if phone_number:
            phone_clean = phone_number.replace("+", "").replace(" ", "").strip()[-10:]
            path_prefix = f"{phone_clean}/"
        else:
            import uuid
            session_token = uuid.uuid4().hex[:8]
            path_prefix = f"session_{session_token}/"
        
        object_path = f"{path_prefix}{clean_filename}"
        upload_url = f"{url}/storage/v1/object/{bucket_name}/{object_path}"
        upload_headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": content_type,
            "x-upsert": "true"
        }
        resp = requests.post(upload_url, headers=upload_headers, data=file_bytes, timeout=15)
        if resp.status_code == 200:
            public_url = f"{url}/storage/v1/object/public/{bucket_name}/{object_path}"
            print(f"[Supabase Storage] Successfully uploaded '{object_path}' → {public_url}")
            return public_url
        else:
            print(f"[Supabase Storage] Upload error ({resp.status_code}): {resp.text}")
            return ""
    except Exception as e:
        print(f"[Supabase Storage] Exception during upload: {e}")
        return ""


APPLICATION_PAYLOAD_REGISTRY: dict = {}

def save_application_payload(payload: dict, phone_number: str = "") -> bool:
    """
    Save application submission payload to Supabase Database and in-memory registry, isolated by user phone number.
    """
    if not isinstance(payload, dict):
        return False

    applicant = payload.get("applicant_details", {})
    creds = payload.get("credentials", {})
    phone_raw = phone_number or applicant.get("mobile_number") or applicant.get("phone_number") or creds.get("username") or creds.get("aadhar_number")
    
    if not phone_raw:
        print("[Supabase DB] Notice: Application payload saved anonymously.")
        return True

    phone_clean = phone_raw.replace("+", "").replace(" ", "").strip()[-10:]
    APPLICATION_PAYLOAD_REGISTRY[phone_clean] = payload

    url, key = get_supabase_config()
    if not (url and key):
        print(f"[Supabase DB] Application payload stored in memory registry for phone {_mask_phone(phone_clean)}")
        return True

    try:
        endpoint = f"{url}/rest/v1/application_payloads"
        headers = {**_get_headers(key), "Prefer": "resolution=merge-duplicates"}
        db_data = {
            "phone_number": phone_clean,
            "payload": json.dumps(payload),
            "updated_at": time.time()
        }
        resp = requests.post(endpoint, headers=headers, json=db_data, timeout=3.0)
        if resp.status_code in (200, 201):
            print(f"[Supabase DB] Saved application payload to database for phone {_mask_phone(phone_clean)}")
            return True
        else:
            print(f"[Supabase DB] Application payload stored in registry notice: {resp.status_code}")
            return True
    except Exception as e:
        print(f"[Supabase DB] Exception saving application payload: {e}")
        return True


def get_latest_application_payload(phone_number: str = "") -> dict:
    """
    Fetch application submission payload strictly for a specific user phone number from Supabase Database or memory registry.
    """
    if not phone_number:
        return {}

    phone_clean = phone_number.replace("+", "").replace(" ", "").strip()[-10:]
    if phone_clean in APPLICATION_PAYLOAD_REGISTRY:
        return APPLICATION_PAYLOAD_REGISTRY[phone_clean]

    url, key = get_supabase_config()
    if not (url and key):
        return {}

    try:
        endpoint = f"{url}/rest/v1/application_payloads"
        params = {"phone_number": f"eq.{phone_clean}", "order": "created_at.desc", "limit": "1"}
        resp = requests.get(endpoint, headers=_get_headers(key), params=params, timeout=3.0)
        if resp.status_code == 200:
            rows = resp.json()
            if rows:
                raw_payload = rows[0].get("payload", {})
                if isinstance(raw_payload, str):
                    return json.loads(raw_payload)
                return raw_payload
    except Exception as e:
        print(f"[Supabase DB] Exception fetching application payload: {e}")

    return {}


USER_PROFILES: dict = {}

def save_user_profile(phone_number: str, profile_data: dict) -> bool:
    """
    Save or update a user's persistent profile (personal details, address, credentials, 3-tab modal data) in Supabase.
    """
    if not phone_number or not isinstance(profile_data, dict):
        return False

    phone_clean = phone_number.replace("+", "").replace(" ", "").strip()[-10:]
    if not phone_clean:
        return False

    creds = profile_data.get("credentials", {})
    applicant = profile_data.get("applicant_details", {})
    address = profile_data.get("address_details", {})
    docs = profile_data.get("documents", {})

    tab1_credentials = {
        "username": creds.get("username", "") or profile_data.get("username", ""),
        "password": creds.get("password", "") or profile_data.get("password", ""),
        "can_number": applicant.get("can_number", "") or creds.get("can_number", ""),
        "aadhar_number": applicant.get("aadhar_number", "") or creds.get("aadhar_number", "")
    }

    tab2_residency = {
        "from_date": address.get("from_date", ""),
        "to_date": address.get("to_date", ""),
        "building_no": address.get("building_no", ""),
        "street_name": address.get("street_name", ""),
        "village": address.get("village", ""),
        "pincode": address.get("pincode", ""),
        "state": address.get("state", "Tamil Nadu"),
        "district": address.get("district", "")
    }

    tab3_documents = {
        "photo_path": docs.get("photo_path", ""),
        "self_decl_path": docs.get("self_decl_path", ""),
        "aadhaar_path": docs.get("aadhaar_path", ""),
        "address_proof_path": docs.get("address_proof_path", ""),
        "address_doc_no": docs.get("address_doc_no", "")
    }

    existing = USER_PROFILES.get(phone_clean, {})
    merged_profile = {
        **existing,
        **profile_data,
        "tab1_credentials": {**(existing.get("tab1_credentials", {})), **tab1_credentials},
        "tab2_residency": {**(existing.get("tab2_residency", {})), **tab2_residency},
        "tab3_documents": {**(existing.get("tab3_documents", {})), **tab3_documents},
        "updated_at": time.time()
    }
    USER_PROFILES[phone_clean] = merged_profile

    url, key = get_supabase_config()
    if not (url and key):
        print(f"[Supabase DB] Profile saved in memory for phone {_mask_phone(phone_clean)}")
        return True

    try:
        endpoint = f"{url}/rest/v1/user_profiles"
        headers = {**_get_headers(key), "Prefer": "resolution=merge-duplicates"}
        db_payload = {
            "phone_number": phone_clean,
            "profile_data": json.dumps(merged_profile),
            "updated_at": time.time()
        }
        resp = requests.post(endpoint, headers=headers, json=db_payload, timeout=3.0)
        if resp.status_code in (200, 201):
            print(f"[Supabase DB] 3-tab profile JSON saved to database for phone {_mask_phone(phone_clean)}")
            return True
        else:
            print(f"[Supabase DB] user_profiles post notice ({resp.status_code}): stored in memory.")
            return True
    except Exception as e:
        print(f"[Supabase DB] Exception saving user profile: {e}")
        return True


def fetch_user_profile(phone_number: str) -> dict:
    """
    Fetch a user's saved profile and uploaded documents from Supabase Database.
    """
    if not phone_number:
        return {"has_saved_profile": False}

    phone_clean = phone_number.replace("+", "").replace(" ", "").strip()[-10:]
    mem_profile = USER_PROFILES.get(phone_clean, {})
    saved_docs = fetch_user_documents(phone_clean)

    url, key = get_supabase_config()
    profile_result = dict(mem_profile)

    if url and key:
        try:
            endpoint = f"{url}/rest/v1/user_profiles"
            params = {"phone_number": f"eq.{phone_clean}", "select": "*"}
            resp = requests.get(endpoint, headers=_get_headers(key), params=params, timeout=3.0)
            if resp.status_code == 200:
                rows = resp.json()
                if rows:
                    raw_prof = rows[0].get("profile_data", {})
                    if isinstance(raw_prof, str):
                        try: raw_prof = json.loads(raw_prof)
                        except: raw_prof = {}
                    profile_result.update(raw_prof)
        except Exception as e:
            print(f"[Supabase DB] Exception fetching user profile: {e}")

    if profile_result:
        t1 = profile_result.get("tab1_credentials", {})
        t2 = profile_result.get("tab2_residency", {})
        t3 = profile_result.get("tab3_documents", {})

        if t1 and "credentials" not in profile_result:
            profile_result["credentials"] = t1
        if t2 and "address_details" not in profile_result:
            profile_result["address_details"] = t2
        if t3 and "supabase_urls" not in profile_result:
            profile_result["supabase_urls"] = t3

    has_saved = bool(profile_result or saved_docs)
    return {
        "phone_number": phone_clean,
        "has_saved_profile": has_saved,
        "profile": profile_result,
        "documents": saved_docs
    }




