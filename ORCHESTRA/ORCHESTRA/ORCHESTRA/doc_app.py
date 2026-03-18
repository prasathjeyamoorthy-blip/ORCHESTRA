from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os

app = FastAPI(title="ORCHESTRA Document Agent", description="Document upload/download endpoints")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Playwright directory (relative to this file)
playwright_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "Playwright"))


# ================================
# CAPTCHA
# ================================
@app.get("/automation/captcha")
def get_captcha():
    captcha_path = os.path.join(playwright_dir, "backend_captcha.png")
    if os.path.exists(captcha_path):
        return FileResponse(
            captcha_path,
            media_type="image/png",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
            }
        )
    return JSONResponse(status_code=404, content={"error": "Captcha not found"})


@app.get("/automation/captcha-b64")
def get_captcha_b64():
    """Return captcha as base64 so the frontend can embed it directly."""
    import base64
    captcha_path = os.path.join(playwright_dir, "backend_captcha.png")
    if os.path.exists(captcha_path):
        with open(captcha_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        return {"image": f"data:image/png;base64,{data}"}
    return JSONResponse(status_code=404, content={"error": "Captcha not found"})


# ================================
# SELF-DECLARATION DOWNLOAD
# ================================
@app.get("/download-declaration")
def download_declaration():
    declaration_path = os.path.join(playwright_dir, "Self_Declaration_Form_To_Sign.pdf")
    if os.path.exists(declaration_path):
        return FileResponse(
            declaration_path,
            media_type="application/pdf",
            filename="Self_Declaration_Form.pdf"
        )
    return {"error": "Declaration form not found"}


# ================================
# SIGNED DECLARATION UPLOAD
# ================================
@app.post("/upload-signed-declaration")
async def upload_signed_declaration(file: UploadFile = File(...)):
    """Save the signed self-declaration form uploaded by user."""
    try:
        uploaded_docs_dir = os.path.join(playwright_dir, "uploaded_documents")
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


# ================================
# DOCUMENT UPLOADS (photo, aadhaar, ration, driving)
# ================================
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
    upload_dir = os.path.join(playwright_dir, "uploaded_documents")
    os.makedirs(upload_dir, exist_ok=True)

    saved = {}
    for key, file_obj in [("aadhaar", aadhaar), ("ration", ration), ("driving", driving), ("photo", photo)]:
        if file_obj:
            dest = os.path.join(upload_dir, file_obj.filename)
            with open(dest, "wb") as f:
                shutil.copyfileobj(file_obj.file, f)
            saved[key] = os.path.abspath(dest)
            print(f"[upload-documents] Saved {key} → {saved[key]}")

    return {"status": "success", "saved_paths": saved}
