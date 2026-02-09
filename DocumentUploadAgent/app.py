from fastapi import FastAPI, UploadFile, File
import shutil
import os

from nim_vlm_inc import extract_from_pdf

app = FastAPI()

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
