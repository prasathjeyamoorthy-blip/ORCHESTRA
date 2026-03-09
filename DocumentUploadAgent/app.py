from fastapi import FastAPI, UploadFile, File
import shutil
import os

from extractor import extract_from_pdf
from face_validator import verify_human_photograph_local
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from main import process_documents

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/extract")
async def extract_document(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    print(f"\n📄 [UploadAgent] File received: {file.filename}")
    print("🔍 Running extraction...\n")

    results = extract_from_pdf(file_path)

    print("\n✅ --- EXTRACTED JSON (Upload Agent) ---\n")
    for r in results:
        print(r)

    return {
        "filename": file.filename,
        "extracted_data": results
    }


@app.post("/verify/photo")
async def verify_photo_document(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    print(f"\n🔍 [UploadAgent] Checking image: {file.filename}")
    
    is_human = verify_human_photograph_local(file_path)
    
    return {
        "is_human_photo": is_human,
        "filename": file.filename
    }


@app.post("/process-all")
async def process_all_documents(
    aadhaar: Optional[UploadFile] = File(None),
    ration: Optional[UploadFile] = File(None),
    driving: Optional[UploadFile] = File(None),
    photo: Optional[UploadFile] = File(None)
):
    print("\n🚀 [UploadAgent] Processing all documents in bulk...")
    
    saved_paths = {"Aadhaar": None, "Ration Card": None, "Driving License": None, "Photo": None}
    
    # helper to save file
    def _save_if_exists(file_obj, key):
        if file_obj:
            file_path = os.path.join(UPLOAD_DIR, file_obj.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file_obj.file, buffer)
            saved_paths[key] = file_path
    
    _save_if_exists(aadhaar, "Aadhaar")
    _save_if_exists(ration, "Ration Card")
    _save_if_exists(driving, "Driving License")
    _save_if_exists(photo, "Photo")
    
    # Process using main.py logic
    # Note: process_documents expects (aadhaar, ration, address)
    # the frontend uses driving license as an alternative address/dob proof
    result = process_documents(
        aadhaar_pdf=saved_paths["Aadhaar"],
        ration_pdf=saved_paths["Ration Card"],
        address_pdf=saved_paths["Driving License"]  # treating driving license as the 3rd doc
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
        "saved_paths": saved_paths
    }
