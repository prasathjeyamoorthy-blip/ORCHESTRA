from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
import os
import json

from extractor import extract_from_pdf
from face_validator import verify_human_photograph_local
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from main import process_documents
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ORCHESTRA")))
try:
    from supabase_db import upload_to_supabase_storage
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

# Store files in Playwright directory for automation access
PLAYWRIGHT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ORCHESTRA", "Playwright", "uploaded_documents"))
os.makedirs(PLAYWRIGHT_DIR, exist_ok=True)

# Keep local uploads folder for backward compatibility
UPLOAD_DIR = "uploads"
@app.post("/upload-encrypted-doc")
async def upload_encrypted_document(file: UploadFile = File(...), phone_number: str = Form("")):
    """
    Upload a client-side Zero-Knowledge encrypted document blob (ZK_DOC_v1 ciphertext) directly to Supabase Storage under a user-isolated path.
    """
    content_bytes = await file.read()
    supabase_url = ""
    if upload_to_supabase_storage:
        c_type = "application/octet-stream"
        supabase_url = upload_to_supabase_storage(content_bytes, file.filename, content_type=c_type, phone_number=phone_number)

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
    aadhaar: Optional[UploadFile] = File(None),
    ration: Optional[UploadFile] = File(None),
    driving: Optional[UploadFile] = File(None),
    photo: Optional[UploadFile] = File(None),
    pre_aadhaar: Optional[str] = Form(None),
    pre_ration: Optional[str] = Form(None),
    pre_driving: Optional[str] = Form(None),
    pre_caste: Optional[str] = Form(None),
):
    print("\n🚀 [UploadAgent] Processing all documents in bulk (Supabase Storage)...")
    
    saved_paths = {"Aadhaar": None, "Ration Card": None, "Driving License": None, "Photo": None}
    supabase_urls = {}
    file_bytes_map = {}
    
    # Helper to upload file directly to Supabase Storage
    def _save_if_exists(file_obj, key):
        if file_obj:
            content_bytes = file_obj.file.read()
            file_bytes_map[key] = content_bytes
            s_url = ""
            
            # Upload to Supabase Storage bucket
            if upload_to_supabase_storage:
                try:
                    c_type = getattr(file_obj, "content_type", "application/octet-stream") or "application/octet-stream"
                    s_url = upload_to_supabase_storage(content_bytes, file_obj.filename, content_type=c_type)
                    if s_url:
                        supabase_urls[key] = s_url
                        print(f"✓ Uploaded {key} to Supabase Storage: {s_url}")
                except Exception as se:
                    print(f"⚠️ Supabase Storage upload error for {key}: {se}")

            # Set saved_paths to Supabase URL (or fallback filename)
            saved_paths[key] = s_url or file_obj.filename
            print(f"✓ Document {key} Supabase URL: {saved_paths[key]}")
    
    _save_if_exists(aadhaar, "Aadhaar")
    _save_if_exists(ration, "Ration Card")
    _save_if_exists(driving, "Driving License")
    _save_if_exists(photo, "Photo")
    
    def _parse_pre(json_str):
        if not json_str:
            return None
        try:
            return json.loads(json_str)
        except Exception as e:
            print(f"[UploadAgent] Failed to parse pre-extracted JSON string: {e}")
            return None

    parsed_pre_aadhaar = _parse_pre(pre_aadhaar)
    parsed_pre_ration  = _parse_pre(pre_ration)
    parsed_pre_driving = _parse_pre(pre_driving)
    parsed_pre_caste   = _parse_pre(pre_caste)
    
    result = process_documents(
        aadhaar_pdf=file_bytes_map.get("Aadhaar") or supabase_urls.get("Aadhaar"),
        ration_pdf=file_bytes_map.get("Ration Card") or supabase_urls.get("Ration Card"),
        address_pdf=file_bytes_map.get("Driving License") or supabase_urls.get("Driving License"),
        pre_aadhaar=parsed_pre_aadhaar,
        pre_ration=parsed_pre_ration,
        pre_address=parsed_pre_driving,
        pre_caste=parsed_pre_caste
    )

    is_human = False
    photo_input = file_bytes_map.get("Photo") or supabase_urls.get("Photo")
    if photo_input:
        print(f"\n🔍 [UploadAgent] Checking face in uploaded photo...")
        is_human = verify_human_photograph_local(photo_input)

    print("\n✅ --- BULK EXTRACTION & VALIDATION RESULTS ---")
    print(f"Confidence Score: {result['confidence_score']}%")
    print(f"Photo Valid: {is_human}")
    
    # Auto-save user profile & document metadata to Supabase DB for returning user recognition
    try:
        from supabase_db import save_user_document_meta, save_user_profile
        combined_data = result.get("combined", {})
        user_phone = combined_data.get("phone_number") or ""
        if user_phone:
            for doc_name, s_url in supabase_urls.items():
                if s_url:
                    save_user_document_meta(user_phone, doc_name, doc_name, s_url)
            save_user_profile(user_phone, {
                "applicant_details": combined_data,
                "supabase_urls": supabase_urls
            })
            print(f"✓ Auto-saved extracted profile & documents to Supabase for user: {user_phone}")
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
    declaration_path = os.path.join(os.path.dirname(__file__), "..", "ORCHESTRA", "Playwright", "Self_Declaration_Form_To_Sign.pdf")
    if os.path.exists(declaration_path):
        return FileResponse(
            declaration_path,
            media_type="application/pdf",
            filename="Self_Declaration_Form.pdf"
        )
    return {"error": "Declaration form not found"}

@app.post("/upload-signed-declaration")
async def upload_signed_declaration(file: UploadFile = File(...)):
    """Save the signed self-declaration form directly to Supabase Storage."""
    try:
        content_bytes = await file.read()
        s_url = ""
        if upload_to_supabase_storage:
            c_type = getattr(file, "content_type", "application/pdf") or "application/pdf"
            s_url = upload_to_supabase_storage(content_bytes, f"Signed_{file.filename}", content_type=c_type)

        print(f"[INFO] Signed self-declaration uploaded to Supabase: {s_url}")

        return {
            "status": "success",
            "message": "Signed declaration uploaded successfully",
            "file_path": s_url or file.filename,
            "supabase_url": s_url
        }
    except Exception as e:
        print(f"[ERROR] Failed to save signed declaration: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/upload-documents")
async def upload_documents(
    aadhaar: UploadFile = File(None),
    ration:  UploadFile = File(None),
    driving: UploadFile = File(None),
    photo:   UploadFile = File(None),
):
    """
    Uploads document files to Supabase Storage and returns public URLs.
    """
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
