from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import RedirectResponse
import os
import json

from extractor import extract_from_pdf
from face_validator import verify_human_photograph_local
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from main import process_documents
import sys
import os

# In production (Docker), supabase_db.py is copied into this directory.
# In local dev, fall back to the sibling ORCHESTRA service.
try:
    from supabase_db import upload_to_supabase_storage
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ORCHESTRA")))
    try:
        from supabase_db import upload_to_supabase_storage
    except Exception as e:
        print(f"[UploadAgent] Warning: Could not import supabase_db: {e}")
        upload_to_supabase_storage = None
except Exception as e:
    print(f"[UploadAgent] Warning: Could not import supabase_db: {e}")
    upload_to_supabase_storage = None

app = FastAPI()

allowed_origins_env = os.getenv("ALLOWED_ORIGINS")
if allowed_origins_env:
    if allowed_origins_env.strip() == "*":
        ALLOWED_ORIGINS = ["*"]
    else:
        ALLOWED_ORIGINS = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
else:
    ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=True if ALLOWED_ORIGINS != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@app.head("/")
def health_check():
    return {"status": "online", "service": "Document Upload Agent"}

# Server-side cache for extracted document data to avoid re-running VLM extraction in bulk
EXTRACTED_CACHE = {}


@app.post("/clear-cache")
def clear_extracted_cache():
    EXTRACTED_CACHE.clear()
    return {"status": "success", "message": "Extraction cache cleared"}


@app.post("/upload-encrypted-doc")
async def upload_encrypted_document(file: UploadFile = File(...), phone_number: str = Form("")):
    """
    Upload a client-side Zero-Knowledge encrypted document blob directly to Supabase Storage.
    """
    content_bytes = await file.read()
    supabase_url = ""
    if upload_to_supabase_storage:
        supabase_url = upload_to_supabase_storage(
            content_bytes, file.filename,
            content_type="application/octet-stream",
            phone_number=phone_number
        )

    masked_phone = f"******{phone_number[-4:]}" if len(phone_number) >= 4 else "****"
    print(f"[Supabase Storage] Uploaded ZK Encrypted Document '{file.filename}' (phone: {masked_phone}) -> {supabase_url}")

    return {
        "filename": file.filename,
        "supabase_url": supabase_url,
        "is_encrypted": True
    }


@app.post("/extract")
async def extract_document(file: UploadFile = File(...)):
    content_bytes = await file.read()
    supabase_url = ""
    if upload_to_supabase_storage:
        c_type = file.content_type or "application/octet-stream"
        supabase_url = upload_to_supabase_storage(content_bytes, file.filename, content_type=c_type)

    print(f"\n📄 [UploadAgent] File received: {file.filename}")
    print("🔍 Running extraction in-memory...\n")

    results = extract_from_pdf(content_bytes)

    if file.filename:
        EXTRACTED_CACHE[file.filename] = results
    for r in results:
        cert_type = (r.get("certificate_type") or "").lower()
        if cert_type:
            EXTRACTED_CACHE[cert_type] = r
            if "aadhaar" in cert_type:       EXTRACTED_CACHE["aadhaar"] = r
            elif "ration" in cert_type:      EXTRACTED_CACHE["ration"] = r
            elif "driving" in cert_type or "dl" in cert_type or "address" in cert_type:
                                             EXTRACTED_CACHE["driving"] = r
            elif "caste" in cert_type:       EXTRACTED_CACHE["caste"] = r

    print("\n✅ --- EXTRACTED JSON (Upload Agent) ---\n")
    for r in results:
        print(r)

    return {
        "filename": file.filename,
        "extracted_data": results,
        "supabase_url": supabase_url
    }


@app.post("/verify/photo")
async def verify_photo_document(file: UploadFile = File(...)):
    content_bytes = await file.read()
    supabase_url = ""
    if upload_to_supabase_storage:
        c_type = file.content_type or "image/jpeg"
        supabase_url = upload_to_supabase_storage(content_bytes, file.filename, content_type=c_type)

    print(f"\n🔍 [UploadAgent] Checking image face validation: {file.filename}")
    is_human = verify_human_photograph_local(content_bytes)

    return {
        "is_human_photo": is_human,
        "filename": file.filename,
        "supabase_url": supabase_url
    }


@app.post("/process-all")
async def process_all_documents(
    aadhaar:      Optional[UploadFile] = File(None),
    ration:       Optional[UploadFile] = File(None),
    driving:      Optional[UploadFile] = File(None),
    photo:        Optional[UploadFile] = File(None),
    pre_aadhaar:  Optional[str] = Form(None),
    pre_ration:   Optional[str] = Form(None),
    pre_driving:  Optional[str] = Form(None),
    pre_caste:    Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
):
    print("\n🚀 [UploadAgent] Processing all documents in bulk (Supabase Storage)...")

    saved_paths   = {"Aadhaar": None, "Ration Card": None, "Driving License": None, "Photo": None}
    supabase_urls = {}
    file_bytes_map = {}

    def _save_if_exists(file_obj, key):
        if file_obj:
            content_bytes = file_obj.file.read()
            file_bytes_map[key] = content_bytes
            s_url = ""
            if upload_to_supabase_storage:
                try:
                    c_type = getattr(file_obj, "content_type", "application/octet-stream") or "application/octet-stream"
                    s_url = upload_to_supabase_storage(content_bytes, file_obj.filename, content_type=c_type)
                    if s_url:
                        supabase_urls[key] = s_url
                        print(f"✓ Uploaded {key} to Supabase Storage: {s_url}")
                except Exception as se:
                    print(f"⚠️ Supabase Storage upload error for {key}: {se}")
            saved_paths[key] = s_url or file_obj.filename

    _save_if_exists(aadhaar, "Aadhaar")
    _save_if_exists(ration,  "Ration Card")
    _save_if_exists(driving, "Driving License")
    _save_if_exists(photo,   "Photo")

    def _parse_pre(json_str):
        if not json_str:
            return None
        try:
            return json.loads(json_str)
        except Exception as e:
            print(f"[UploadAgent] Failed to parse pre-extracted JSON: {e}")
            return None

    parsed_pre_aadhaar = _parse_pre(pre_aadhaar) or EXTRACTED_CACHE.get("aadhaar") or (EXTRACTED_CACHE.get(aadhaar.filename) if aadhaar else None)
    parsed_pre_ration  = _parse_pre(pre_ration)  or EXTRACTED_CACHE.get("ration")  or (EXTRACTED_CACHE.get(ration.filename)  if ration  else None)
    parsed_pre_driving = _parse_pre(pre_driving) or EXTRACTED_CACHE.get("driving") or (EXTRACTED_CACHE.get(driving.filename) if driving else None)
    parsed_pre_caste   = _parse_pre(pre_caste)   or EXTRACTED_CACHE.get("caste")

    result = process_documents(
        aadhaar_pdf=file_bytes_map.get("Aadhaar")        or supabase_urls.get("Aadhaar"),
        ration_pdf=file_bytes_map.get("Ration Card")     or supabase_urls.get("Ration Card"),
        address_pdf=file_bytes_map.get("Driving License") or supabase_urls.get("Driving License"),
        pre_aadhaar=parsed_pre_aadhaar,
        pre_ration=parsed_pre_ration,
        pre_address=parsed_pre_driving,
        pre_caste=parsed_pre_caste
    )

    is_human = False
    photo_input = file_bytes_map.get("Photo") or supabase_urls.get("Photo")
    if photo_input:
        is_human = verify_human_photograph_local(photo_input)

    print(f"\n✅ Confidence Score: {result['confidence_score']}%  |  Photo Valid: {is_human}")

    try:
        from supabase_db import save_user_document_meta, save_user_profile
        combined_data = result.get("combined", {})
        user_phone = (phone_number or "").strip() or combined_data.get("phone_number") or ""
        if user_phone:
            for doc_name, s_url in supabase_urls.items():
                if s_url:
                    save_user_document_meta(user_phone, doc_name, doc_name, s_url)
            save_user_profile(user_phone, {
                "applicant_details": combined_data,
                "supabase_urls": supabase_urls
            })
            print(f"✓ Auto-saved profile to Supabase for user: ****{user_phone[-4:]}")
        else:
            print("[UploadAgent] No phone number — profile auto-save skipped.")
    except Exception as spe:
        print(f"[UploadAgent] Profile auto-save notice: {spe}")

    return {
        "status": "success",
        "result": result,
        "is_human_photo": is_human,
        "saved_paths": saved_paths,
        "supabase_urls": supabase_urls
    }


@app.get("/download-declaration")
def download_declaration():
    """
    Serve the self-declaration PDF.
    Checks S3_DECLARATION_URL env var first (production), falls back to bundled file.
    """
    s3_url = os.getenv("S3_DECLARATION_URL", "").strip()
    if s3_url:
        return RedirectResponse(url=s3_url)

    # Fallback: bundled PDF inside container
    declaration_path = os.path.join(
        os.path.dirname(__file__), "..", "ORCHESTRA", "Playwright", "Self_Declaration_Form_To_Sign.pdf"
    )
    if os.path.exists(declaration_path):
        from fastapi.responses import FileResponse
        return FileResponse(declaration_path, media_type="application/pdf", filename="Self_Declaration_Form.pdf")

    return {"error": "Declaration form not found"}


@app.post("/upload-signed-declaration")
async def upload_signed_declaration(file: UploadFile = File(...)):
    """Save the signed self-declaration form to Supabase Storage."""
    try:
        content_bytes = await file.read()
        s_url = ""
        if upload_to_supabase_storage:
            c_type = getattr(file, "content_type", "application/pdf") or "application/pdf"
            s_url = upload_to_supabase_storage(content_bytes, f"Signed_{file.filename}", content_type=c_type)

        print(f"[INFO] Signed self-declaration uploaded: {s_url}")
        return {
            "status": "success",
            "message": "Signed declaration uploaded successfully",
            "file_path": s_url or file.filename,
            "supabase_url": s_url
        }
    except Exception as e:
        print(f"[ERROR] Failed to save signed declaration: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/upload-documents")
async def upload_documents(
    aadhaar: UploadFile = File(None),
    ration:  UploadFile = File(None),
    driving: UploadFile = File(None),
    photo:   UploadFile = File(None),
):
    """Upload document files to Supabase Storage and return public URLs."""
    saved = {}
    for key, file_obj in [("aadhaar", aadhaar), ("ration", ration), ("driving", driving), ("photo", photo)]:
        if file_obj:
            content_bytes = await file_obj.read()
            s_url = ""
            if upload_to_supabase_storage:
                c_type = getattr(file_obj, "content_type", "application/octet-stream") or "application/octet-stream"
                s_url = upload_to_supabase_storage(content_bytes, file_obj.filename, content_type=c_type)
            saved[key] = s_url or file_obj.filename
            print(f"[upload-documents] Uploaded {key} → {saved[key]}")

    return {"status": "success", "saved_paths": saved}
