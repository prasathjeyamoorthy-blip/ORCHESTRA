from fastapi import FastAPI, UploadFile, File
import shutil
import os

from extractor import extract_from_pdf
from face_validator import verify_human_photograph_local
from fastapi.middleware.cors import CORSMiddleware

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
