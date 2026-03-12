# Photo Upload Fix - Automatic Upload Without Dialog

## Problem
When uploading photo during automation, a file browser dialog appears asking user to select the file manually.

## Root Cause
The photo file path from the frontend might be:
1. Relative path instead of absolute path
2. Not accessible from Playwright's working directory
3. File input not ready when `set_input_files()` is called

## Solution

### 1. Enhanced Logging
Added detailed logging to debug the issue:
```python
photo_path = self.docs.get("photo_path")
self.log(f"Photo path from payload: {photo_path}")

if not photo_path:
    self.log("✗ ERROR: No photo path provided in payload!")
    self.log(f"Available docs: {self.docs}")
elif not os.path.exists(photo_path):
    self.log(f"✗ ERROR: Photo file does not exist at: {photo_path}")
```

### 2. Wait for File Input
Ensure file input element is ready before setting files:
```python
file_input = page_form.locator("input[type='file']").last
file_input.wait_for(state="attached", timeout=5000)
file_input.set_input_files(photo_image)
```

### 3. Use Absolute Paths
The DocumentUploadAgent saves files to `uploads/` directory:
```python
UPLOAD_DIR = "uploads"
file_path = os.path.join(UPLOAD_DIR, file.filename)
# Saves as: uploads/photo.jpg (relative path)
```

**Fix:** Convert to absolute path before sending to Playwright:
```python
# In DocumentUploadAgent/app.py
file_path = os.path.abspath(os.path.join(UPLOAD_DIR, file.filename))
# Now: /full/path/to/uploads/photo.jpg (absolute path)
```

## Implementation Steps

### Step 1: Update DocumentUploadAgent to Use Absolute Paths

File: `ORCHESTRA/DocumentUploadAgent/app.py`

```python
def _save_if_exists(file_obj, key):
    if file_obj:
        file_path = os.path.join(UPLOAD_DIR, file_obj.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file_obj.file, buffer)
        # Convert to absolute path
        saved_paths[key] = os.path.abspath(file_path)
```

### Step 2: Verify Paths in Payload

The payload sent to Playwright should contain absolute paths:
```json
{
  "documents": {
    "photo_path": "C:/Users/Dev/ORCHESTRA/DocumentUploadAgent/uploads/photo.jpg",
    "driving_license_path": "C:/Users/Dev/ORCHESTRA/DocumentUploadAgent/uploads/dl.pdf",
    "address_proof_path": "C:/Users/Dev/ORCHESTRA/DocumentUploadAgent/uploads/aadhaar.pdf"
  }
}
```

### Step 3: Enhanced Error Handling in Playwright

```python
# Check if path exists
if not os.path.exists(photo_path):
    self.log(f"✗ ERROR: Photo file does not exist at: {photo_path}")
    self.log(f"Current working directory: {os.getcwd()}")
    self.log(f"Trying relative path from CWD...")
    
    # Try relative path from current directory
    relative_path = os.path.join(os.getcwd(), photo_path)
    if os.path.exists(relative_path):
        photo_path = relative_path
        self.log(f"✓ Found photo at: {photo_path}")
```

## Testing

### Test 1: Check Photo Path in Logs
Look for this in Playwright logs:
```
[STATUS] Photo path from payload: C:/full/path/to/uploads/photo.jpg
[STATUS] ✓ Photo uploaded: C:/full/path/to/uploads/photo_converted.jpg
```

### Test 2: Verify No Dialog Appears
- File browser dialog should NOT appear
- Photo should upload automatically
- No user interaction required

### Test 3: Check File Exists
```python
# In Playwright
if os.path.exists(photo_path):
    print(f"✓ Photo file exists: {photo_path}")
else:
    print(f"✗ Photo file NOT found: {photo_path}")
```

## Common Issues

### Issue 1: Relative Path
**Symptom:** File not found error
**Solution:** Use `os.path.abspath()` when saving files

### Issue 2: Wrong Working Directory
**Symptom:** File exists but Playwright can't find it
**Solution:** Use absolute paths, not relative

### Issue 3: File Input Not Ready
**Symptom:** Dialog appears even with correct path
**Solution:** Wait for file input to be attached before setting files

### Issue 4: File Permissions
**Symptom:** File exists but can't be read
**Solution:** Check file permissions, ensure Playwright has read access

## Verification Checklist

- [ ] Photo saves to `uploads/` directory with absolute path
- [ ] Absolute path is sent in payload to Playwright
- [ ] Playwright logs show correct absolute path
- [ ] File exists check passes
- [ ] File input waits for attachment
- [ ] `set_input_files()` is called with absolute path
- [ ] No file browser dialog appears
- [ ] Photo uploads successfully
- [ ] Automation continues without user interaction

## Expected Flow

```
1. User uploads photo in frontend checklist
   ↓
2. Frontend sends photo to DocumentUploadAgent
   ↓
3. DocumentUploadAgent saves to: uploads/photo.jpg
   ↓
4. DocumentUploadAgent converts to absolute path
   ↓
5. Absolute path sent in payload: C:/path/to/uploads/photo.jpg
   ↓
6. Playwright receives absolute path
   ↓
7. Playwright checks file exists: ✓
   ↓
8. Playwright converts to image (if needed)
   ↓
9. Playwright waits for file input to be ready
   ↓
10. Playwright calls: set_input_files(absolute_path)
    ↓
11. Photo uploads automatically (NO DIALOG)
    ↓
12. Success!
```

## Debug Commands

### Check if file exists from Playwright directory:
```python
import os
print(f"Current directory: {os.getcwd()}")
print(f"Photo path: {photo_path}")
print(f"File exists: {os.path.exists(photo_path)}")
print(f"Absolute path: {os.path.abspath(photo_path)}")
```

### List files in uploads directory:
```python
import os
uploads_dir = "uploads"
if os.path.exists(uploads_dir):
    files = os.listdir(uploads_dir)
    print(f"Files in uploads/: {files}")
```

### Check file permissions:
```python
import os
import stat
st = os.stat(photo_path)
print(f"File permissions: {oct(st.st_mode)}")
print(f"Readable: {os.access(photo_path, os.R_OK)}")
```
