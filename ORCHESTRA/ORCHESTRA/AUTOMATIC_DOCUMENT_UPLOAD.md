# Automatic Document Upload - Complete Implementation

## Overview
All documents uploaded in the frontend are automatically stored and uploaded during automation without any manual file selection.

## Document Storage

### Location
All documents are saved in: `ORCHESTRA/DocumentUploadAgent/uploads/`

### Storage Process
```python
# When user uploads in frontend
UPLOAD_DIR = "uploads"
file_path = os.path.join(UPLOAD_DIR, file.filename)

# Save file
with open(file_path, "wb") as buffer:
    shutil.copyfileobj(file.file, buffer)

# Convert to absolute path for Playwright
saved_paths[key] = os.path.abspath(file_path)
```

### Result
Files are saved with absolute paths:
```
C:/Users/Dev/ORCHESTRA/DocumentUploadAgent/uploads/photo.jpg
C:/Users/Dev/ORCHESTRA/DocumentUploadAgent/uploads/driving_license.pdf
C:/Users/Dev/ORCHESTRA/DocumentUploadAgent/uploads/aadhaar.pdf
```

## Automatic Upload Flow

### 1. Photo Upload (Automatic)
```
User uploads in frontend
    ↓
Saved to: uploads/photo.jpg
    ↓
Absolute path: C:/path/to/uploads/photo.jpg
    ↓
Sent in payload to Playwright
    ↓
Playwright automation:
    - Select "Photo" from dropdown
    - Click "Add..." button
    - Wait for file input to be ready
    - set_input_files(absolute_path)
    - NO DIALOG APPEARS
    - Photo uploads automatically
```

### 2. Self-Declaration (Semi-Automatic)
```
Automation downloads blank form from portal
    ↓
User downloads, signs, and re-uploads via modal
    ↓
Frontend uploads to backend: /upload-signed-declaration
    ↓
Backend saves to: uploads/Signed_Self_Declaration_xxx.pdf
    ↓
Absolute path returned to frontend
    ↓
Frontend sends path to Playwright via WebSocket
    ↓
Playwright automation:
    - Select "Self-Declaration of Applicant" from dropdown
    - Click "Add..." button
    - Wait for file input to be ready
    - set_input_files(absolute_path)
    - NO DIALOG APPEARS
    - Signed form uploads automatically
```

### 3. Driving License Upload (Automatic)
```
User uploads in frontend
    ↓
Saved to: uploads/driving_license.pdf
    ↓
Absolute path: C:/path/to/uploads/driving_license.pdf
    ↓
Sent in payload to Playwright
    ↓
User enters document number via modal
    ↓
Playwright automation:
    - Select "Current Address Proof" from dropdown
    - Click "Add..." button
    - Fill document number
    - Convert PDF to image (if needed)
    - Wait for file input to be ready
    - set_input_files(absolute_path)
    - NO DIALOG APPEARS
    - Driving license uploads automatically
```

## Key Features

### 1. Absolute Paths
✅ All files saved with absolute paths
✅ No path resolution issues
✅ Works across different working directories

### 2. No File Dialogs
✅ `set_input_files()` used instead of clicking file input
✅ Files set programmatically
✅ No user interaction required

### 3. Automatic PDF Conversion
✅ All PDFs converted to images automatically
✅ High quality (200 DPI, 95% JPEG)
✅ Portal-compatible format

### 4. Enhanced Logging
✅ Shows file paths in logs
✅ Indicates if file exists
✅ Shows which document is being used
✅ Helps debug issues

### 5. Fallback Logic
✅ Driving License → Aadhaar (if DL not available)
✅ Continues even if some files missing
✅ Clear error messages

## Payload Structure

### Frontend to Backend
```json
{
  "documents": {
    "photo_path": "C:/path/to/uploads/photo.jpg",
    "self_decl_path": "",
    "address_proof_path": "C:/path/to/uploads/aadhaar.pdf",
    "driving_license_path": "C:/path/to/uploads/driving_license.pdf",
    "address_doc_no": "607126530111"
  }
}
```

### All Paths Are:
- ✅ Absolute (not relative)
- ✅ Accessible from Playwright
- ✅ Verified to exist before upload
- ✅ Converted to image format if needed

## Success Logs

```
[STATUS] Step 1: Uploading Photo...
[STATUS] Photo path from payload: C:/path/to/uploads/photo.jpg
[STATUS] ✓ Selected 'Photo' from dropdown
[STATUS] ✓ Clicked 'Add...' button
[STATUS] File is already in image format: C:/path/to/uploads/photo.jpg
[STATUS] ✓ Photo uploaded: C:/path/to/uploads/photo.jpg

[STATUS] Step 2: Handling Self-Declaration Form...
[STATUS] ✓ Self-Declaration Form downloaded: Self_Declaration_Form_To_Sign.pdf
[STATUS] Waiting for user to upload signed Self-Declaration Form...
[WebSocket] Received: C:/path/to/uploads/Signed_Self_Declaration_form.pdf
[STATUS] ✓ Selected 'Self-Declaration of Applicant' from dropdown
[STATUS] ✓ Clicked 'Add...' button
[STATUS] Converting PDF to image: C:/path/to/uploads/Signed_Self_Declaration_form.pdf
[STATUS] ✓ PDF converted to image: C:/path/to/uploads/Signed_Self_Declaration_form_converted.jpg
[STATUS] ✓ Signed Self-Declaration uploaded: C:/path/to/uploads/Signed_Self_Declaration_form_converted.jpg

[STATUS] Step 3: Uploading Current Address Proof (Driving License)...
[STATUS] Driving License path from payload: C:/path/to/uploads/driving_license.pdf
[STATUS] ✓ Using Driving License: C:/path/to/uploads/driving_license.pdf
[STATUS] ✓ Selected 'Current Address Proof' from dropdown
[STATUS] ✓ Clicked 'Add...' button
[STATUS] ✓ Document number filled: TN3120250006924
[STATUS] Converting PDF to image: C:/path/to/uploads/driving_license.pdf
[STATUS] ✓ PDF converted to image: C:/path/to/uploads/driving_license_converted.jpg
[STATUS] ✓ Address proof uploaded: C:/path/to/uploads/driving_license_converted.jpg

[STATUS] All documents uploaded! Looking for Submit/Proceed button...
[STATUS] ✓ Clicked 'Proceed' button
[STATUS] ✓ Form submitted successfully!
[STATUS] SUCCESS! Document upload process complete.
```

## Error Handling

### File Not Found
```
[STATUS] Photo path from payload: uploads/photo.jpg
[STATUS] ✗ ERROR: Photo file does not exist at: uploads/photo.jpg
[STATUS] Available docs: {'photo_path': 'uploads/photo.jpg', ...}
```
**Solution:** Ensure absolute paths are used

### File Dialog Appears
**Cause:** File path is incorrect or file doesn't exist
**Solution:** Check logs for file path, verify file exists

### PDF Conversion Fails
```
[STATUS] ✗ WARNING: pdf2image not installed. Trying to upload PDF directly...
```
**Solution:** `pip install pdf2image` and install poppler

## Testing Checklist

### Photo Upload
- [ ] Photo uploads in frontend checklist
- [ ] Photo saves to `uploads/` with absolute path
- [ ] Absolute path sent in payload
- [ ] Playwright logs show correct path
- [ ] File exists check passes
- [ ] NO file dialog appears
- [ ] Photo uploads automatically
- [ ] Success message in logs

### Driving License Upload
- [ ] Driving license uploads in frontend checklist
- [ ] DL saves to `uploads/` with absolute path
- [ ] Absolute path sent in payload
- [ ] Playwright logs show correct path
- [ ] File exists check passes
- [ ] Document number modal appears
- [ ] User enters document number
- [ ] PDF converts to image
- [ ] NO file dialog appears
- [ ] DL uploads automatically
- [ ] Success message in logs

### Self-Declaration Upload
- [ ] Blank form downloads from portal
- [ ] Modal shows with download button
- [ ] User downloads form
- [ ] User signs form
- [ ] User uploads signed version
- [ ] Frontend uploads to backend
- [ ] Backend saves with absolute path
- [ ] Path sent to Playwright via WebSocket
- [ ] PDF converts to image
- [ ] NO file dialog appears
- [ ] Signed form uploads automatically
- [ ] Success message in logs

## Troubleshooting

### Issue: File dialog still appears
**Check:**
1. Is the file path absolute? (should start with C:/ or /)
2. Does the file exist at that path?
3. Is Playwright using the correct working directory?
4. Are file permissions correct?

**Debug:**
```python
print(f"File path: {photo_path}")
print(f"Is absolute: {os.path.isabs(photo_path)}")
print(f"File exists: {os.path.exists(photo_path)}")
print(f"Current dir: {os.getcwd()}")
```

### Issue: File not found
**Check:**
1. Did DocumentUploadAgent save the file?
2. Is the path in the payload correct?
3. Is the file in the `uploads/` directory?

**Debug:**
```python
import os
uploads_dir = "uploads"
files = os.listdir(uploads_dir)
print(f"Files in uploads/: {files}")
```

### Issue: PDF not converting
**Check:**
1. Is `pdf2image` installed?
2. Is `poppler` installed on system?
3. Is the PDF file valid?

**Debug:**
```python
from pdf2image import convert_from_path
images = convert_from_path(pdf_path, first_page=1, last_page=1)
print(f"Converted pages: {len(images)}")
```

## Benefits

✅ **Zero Manual Intervention** - All documents upload automatically
✅ **Stored Centrally** - All files in one `uploads/` directory
✅ **Absolute Paths** - No path resolution issues
✅ **Automatic Conversion** - PDFs → Images seamlessly
✅ **Clear Logging** - Easy to debug issues
✅ **Fallback Logic** - Continues even if some files missing
✅ **No Dialogs** - Completely automated upload process

## Summary

All documents uploaded in the frontend are:
1. ✅ Saved to `uploads/` directory with absolute paths
2. ✅ Sent to Playwright in payload
3. ✅ Automatically converted to images if needed
4. ✅ Uploaded without any file dialogs
5. ✅ No manual file selection required

The only user interaction needed is:
- Entering CAPTCHA
- Entering OTP
- Signing and re-uploading self-declaration
- Entering document number for address proof

Everything else is fully automated!
