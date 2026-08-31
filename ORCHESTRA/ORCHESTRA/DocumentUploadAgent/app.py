from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
import shutil
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
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    content_bytes = await file.read()
    with open(file_path, "wb") as buffer:
        buffer.write(content_bytes)

    supabase_url = ""
    if upload_to_supabase_storage:
        c_type = file.content_type or "application/octet-stream"
        supabase_url = upload_to_supabase_storage(content_bytes, file.filename, content_type=c_type)

    print(f"\n📄 [UploadAgent] File received: {file.filename}")
    print("🔍 Running extraction...\n")

    results = extract_from_pdf(file_path)

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
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    content_bytes = await file.read()
    with open(file_path, "wb") as buffer:
        buffer.write(content_bytes)

    supabase_url = ""
    if upload_to_supabase_storage:
        c_type = file.content_type or "image/jpeg"
        supabase_url = upload_to_supabase_storage(content_bytes, file.filename, content_type=c_type)

    print(f"\n🔍 [UploadAgent] Checking image: {file.filename}")
    
    is_human = verify_human_photograph_local(file_path)
    
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
    print("\n🚀 [UploadAgent] Processing all documents in bulk...")
    
    saved_paths = {"Aadhaar": None, "Ration Card": None, "Driving License": None, "Photo": None}
    supabase_urls = {}
    
    # helper to save file to Playwright directory and Supabase Storage
    def _save_if_exists(file_obj, key):
        if file_obj:
            content_bytes = file_obj.file.read()
            # Save to Playwright directory for automation access
            playwright_path = os.path.join(PLAYWRIGHT_DIR, file_obj.filename)
            with open(playwright_path, "wb") as buffer:
                buffer.write(content_bytes)
            
            # Also save to local uploads for extraction processing
            local_path = os.path.join(UPLOAD_DIR, file_obj.filename)
            with open(local_path, "wb") as buffer:
                buffer.write(content_bytes)
            
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

            # Return absolute path to Playwright directory
            saved_paths[key] = os.path.abspath(playwright_path)
            print(f"✓ Saved {key} to: {saved_paths[key]}")
    
    _save_if_exists(aadhaar, "Aadhaar")
    _save_if_exists(ration, "Ration Card")
    _save_if_exists(driving, "Driving License")
    _save_if_exists(photo, "Photo")
    
    # Process using main.py logic (uses local uploads folder for extraction)
    local_aadhaar = os.path.join(UPLOAD_DIR, aadhaar.filename) if aadhaar else None
    local_ration = os.path.join(UPLOAD_DIR, ration.filename) if ration else None
    local_driving = os.path.join(UPLOAD_DIR, driving.filename) if driving else None

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
        aadhaar_pdf=local_aadhaar,
        ration_pdf=local_ration,
        address_pdf=local_driving,
        pre_aadhaar=parsed_pre_aadhaar,
        pre_ration=parsed_pre_ration,
        pre_address=parsed_pre_driving,
        pre_caste=parsed_pre_caste
    )

    is_human = False
    if saved_paths["Photo"]:
        print(f"\n🔍 [UploadAgent] Checking image: {saved_paths['Photo']}")
        is_human = verify_human_photograph_local(saved_paths["Photo"])

    print("\n✅ --- BULK EXTRACTION & VALIDATION RESULTS ---")
    print("\n[Validation Metrics]")
    print(f"Name Match: {result['validation']['name_match']} ({result['validation']['name_similarity']}%)")
    print(f"DOB Match: {result['validation']['dob_match']}")
    print(f"Confidence Score: {result['confidence_score']}%")
    print(f"Photo Valid: {is_human}")
    
    print("\n[Combined Data payload for Playwright]")
    for k, v in result['combined'].items():
        print(f"  {k}: {v}")
    print("----------------------------------------------\n")
    
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
    """Save the signed self-declaration form uploaded by user."""
    try:
        uploaded_docs_dir = os.path.join(os.path.dirname(__file__), "..", "ORCHESTRA", "Playwright", "uploaded_documents")
        os.makedirs(uploaded_docs_dir, exist_ok=True)

        save_path = os.path.join(uploaded_docs_dir, f"Signed_Self_Declaration_{file.filename}")

        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print(f"[INFO] Signed self-declaration saved: {save_path}")

        return {
            "status": "success",
            "message": "Signed declaration uploaded successfully",
            "file_path": os.path.abspath(save_path)
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
    Receives document files from the frontend and saves them to the
    Playwright uploaded_documents directory so the automation agent
    can read them by local path.
    """
    saved = {}
    for key, file_obj in [("aadhaar", aadhaar), ("ration", ration), ("driving", driving), ("photo", photo)]:
        if file_obj:
            dest = os.path.join(PLAYWRIGHT_DIR, file_obj.filename)
            with open(dest, "wb") as f:
                shutil.copyfileobj(file_obj.file, f)
            saved[key] = os.path.abspath(dest)
            print(f"[upload-documents] Saved {key} → {saved[key]}")

    return {"status": "success", "saved_paths": saved}
