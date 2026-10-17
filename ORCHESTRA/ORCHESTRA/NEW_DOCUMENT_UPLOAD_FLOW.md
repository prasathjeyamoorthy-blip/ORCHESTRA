# New Document Upload Flow - Complete Implementation

## Overview
Completely redesigned document upload process with user interaction at each step, following the exact portal workflow.

## New Flow Diagram

```
Form Submitted Successfully
         ↓
User Clicks "Continue" (WebSocket Prompt)
         ↓
┌────────────────────────────────────────────────────────────┐
│ STEP 1: PHOTO UPLOAD                                       │
├────────────────────────────────────────────────────────────┤
│ 1. Select "Photo" from dropdown                            │
│ 2. Click "Add..." button                                   │
│ 3. Upload photo file (from payload)                        │
│ 4. Wait 3 seconds                                          │
└────────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────────┐
│ STEP 2: SELF-DECLARATION FORM                              │
├────────────────────────────────────────────────────────────┤
│ 1. Select "Self-Declaration of Applicant" from dropdown    │
│ 2. Click "Add..." button                                   │
│ 3. Download the blank form from portal                     │
│ 4. Save as: Self_Declaration_Form_To_Sign.pdf              │
│ 5. Send WebSocket event to frontend                        │
│ 6. Show modal with:                                        │
│    - Download button                                       │
│    - Upload signed form field                              │
│    - Exit button (optional)                                │
│ 7. ⏸️ WAIT for user to:                                    │
│    a. Download form                                        │
│    b. Print and sign it                                    │
│    c. Scan/photograph signed version                       │
│    d. Upload signed file                                   │
│    e. Click "Submit" OR "Exit"                             │
│ 8. If user exits → Stop automation                         │
│ 9. If user submits → Upload signed file to portal          │
│ 10. Document number field: LEAVE EMPTY                     │
└────────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────────┐
│ STEP 3: CURRENT ADDRESS PROOF                              │
├────────────────────────────────────────────────────────────┤
│ 1. Select "Current Address Proof" from dropdown            │
│ 2. Click "Add..." button                                   │
│ 3. Show modal asking for Document Number                   │
│ 4. ⏸️ WAIT for user to enter document number              │
│    (e.g., Aadhaar number)                                  │
│ 5. Fill document number in portal                          │
│ 6. Check file format:                                      │
│    - If PDF → Convert to JPG/PNG                           │
│    - If Image → Use directly                               │
│ 7. Upload the image file                                   │
│ 8. Wait 3 seconds                                          │
└────────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────────┐
│ FINAL STEP: SUBMIT                                         │
├────────────────────────────────────────────────────────────┤
│ 1. Look for button: "Proceed" / "Submit" / "Make Payment"  │
│ 2. Click the button                                        │
│ 3. Wait for page load                                      │
│ 4. ✓ SUCCESS - Automation Complete                        │
└────────────────────────────────────────────────────────────┘
```

## Key Changes from Old Flow

### Old Flow (Removed)
```python
def process_document_upload(doc_label, filepath, doc_no=None):
    # Select dropdown
    # Fill doc number if provided
    # Upload file
    # Click "Upload" button

# Upload all 3 documents in sequence
process_document_upload("Photo", photo_path)
process_document_upload("Self-Declaration", decl_path)
process_document_upload("Address Proof", addr_path, doc_no)
```

### New Flow (Implemented)
```python
# STEP 1: Photo
- Select "Photo" → Click "Add..." → Upload file

# STEP 2: Self-Declaration (Interactive)
- Select "Self-Declaration" → Click "Add..."
- Download blank form from portal
- Send to frontend for user to sign
- Wait for signed version upload
- Allow user to exit if needed
- Document number: EMPTY

# STEP 3: Address Proof (Interactive)
- Select "Current Address Proof" → Click "Add..."
- Ask user for document number via modal
- Convert PDF to image if needed
- Upload image file

# FINAL: Submit
- Click "Proceed" or "Submit" button
```

## Document Number Handling

| Document Type | Document Number Field |
|---------------|----------------------|
| Photo | ❌ EMPTY (not filled) |
| Self-Declaration of Applicant | ❌ EMPTY (not filled) |
| Current Address Proof | ✅ FILLED (user provides via modal) |

## PDF to Image Conversion

### Why?
Portal may only accept image formats for address proof.

### How?
```python
from pdf2image import convert_from_path

if address_proof_path.lower().endswith('.pdf'):
    images = convert_from_path(address_proof_path, first_page=1, last_page=1)
    image_path = address_proof_path.replace('.pdf', '_converted.jpg')
    images[0].save(image_path, 'JPEG')
    address_proof_path = image_path
```

### Fallback
If `pdf2image` not installed or conversion fails, tries to upload PDF directly.

## Frontend Components Created

### 1. SelfDeclarationModal.jsx
**Purpose:** Handle self-declaration download, signing, and upload

**Features:**
- Download button for blank form
- File upload for signed version
- Exit button (stops automation)
- Submit button (continues automation)
- File validation (PDF, JPG, PNG, max 200KB)

**Props:**
```jsx
<SelfDeclarationModal
  isOpen={boolean}
  downloadPath={string}
  onSubmit={(filePath) => void}
  onExit={() => void}
/>
```

### 2. DocumentNumberModal.jsx
**Purpose:** Request document number from user

**Features:**
- Text input for document number
- Enter key support
- Validation (required field)
- Auto-focus on input

**Props:**
```jsx
<DocumentNumberModal
  isOpen={boolean}
  onSubmit={(docNumber) => void}
/>
```

## WebSocket Events

### New Event Types

#### 1. SELF_DECLARATION_DOWNLOADED
```json
{
  "type": "SELF_DECLARATION_DOWNLOADED",
  "message": "Self-Declaration Form downloaded. Please download, sign it, and upload the signed version.",
  "file_path": "/path/to/Self_Declaration_Form_To_Sign.pdf"
}
```

#### 2. REQUEST_SIGNED_DECLARATION
```json
{
  "type": "REQUEST_SIGNED_DECLARATION",
  "message": "Please download the Self-Declaration Form, sign it, and upload the signed version. You can also exit if needed.",
  "download_path": "/path/to/form.pdf",
  "allow_exit": true
}
```

#### 3. REQUEST_DOCUMENT_NUMBER
```json
{
  "type": "REQUEST_DOCUMENT_NUMBER",
  "message": "Please enter the Document Number for Current Address Proof (e.g., Aadhaar number):"
}
```

### User Response Format
```json
{
  "type": "USER_ANSWER",
  "data": "user_input_value"
}
```

Special responses:
- `"data": "exit"` → User wants to exit automation
- `"data": "/path/to/signed.pdf"` → Signed form file path
- `"data": "607126530111"` → Document number

## Backend Endpoints

### New Endpoint: Download Declaration
```python
@app.get("/download-declaration")
def download_declaration():
    declaration_path = os.path.join(playwright_dir, "Self_Declaration_Form_To_Sign.pdf")
    return FileResponse(
        declaration_path,
        media_type="application/pdf",
        filename="Self_Declaration_Form.pdf"
    )
```

**Usage:** Frontend calls this to download the form for user

## Error Handling

### Photo Upload Fails
```python
if not os.path.exists(photo_path):
    self.log("✗ WARNING: Photo file not found!")
    # Continues to next step
```

### Self-Declaration Download Fails
```python
except Exception as e:
    self.log(f"✗ ERROR with Self-Declaration download/upload: {e}")
    # Continues to next step
```

### PDF Conversion Fails
```python
except ImportError:
    self.log("✗ WARNING: pdf2image not installed. Trying to upload PDF directly...")
except Exception as e:
    self.log(f"✗ WARNING: PDF conversion failed: {e}. Trying to upload PDF directly...")
```

### Submit Button Not Found
```python
if not button_clicked:
    self.log("⚠ WARNING: Could not find Submit/Proceed button. Please check manually.")
```

## User Experience Flow

### 1. User Perspective - Self-Declaration
```
1. Modal appears: "Self-Declaration Form"
2. User clicks "Download Self-Declaration Form" button
3. PDF downloads to user's computer
4. User prints the PDF
5. User signs it manually
6. User scans/photographs the signed document
7. User clicks "Choose File" and selects signed version
8. User clicks "Submit Signed Form"
   OR
   User clicks "Exit" to stop automation
```

### 2. User Perspective - Document Number
```
1. Modal appears: "Document Number Required"
2. User sees message: "Please enter the Document Number for your Current Address Proof"
3. User types Aadhaar number (or other document number)
4. User clicks "Submit" or presses Enter
5. Modal closes, automation continues
```

## Dependencies

### Python
```bash
pip install pdf2image
```

### System (for pdf2image)
```bash
# Ubuntu/Debian
sudo apt-get install poppler-utils

# macOS
brew install poppler

# Windows
# Download poppler binaries and add to PATH
```

## Testing Checklist

- [ ] Photo uploads successfully
- [ ] Self-declaration form downloads
- [ ] Frontend modal shows download button
- [ ] User can download form from modal
- [ ] User can upload signed version
- [ ] Exit button stops automation
- [ ] Document number modal appears
- [ ] User can enter document number
- [ ] PDF converts to image successfully
- [ ] Image uploads successfully
- [ ] Submit/Proceed button clicks
- [ ] Automation completes successfully

## Success Logs

```
[STATUS] Starting Document Upload Process...
[STATUS] Step 1: Uploading Photo...
[STATUS] ✓ Photo uploaded: /path/to/photo.jpg
[STATUS] Step 2: Handling Self-Declaration Form...
[STATUS] Downloading Self-Declaration Form for user to sign...
[STATUS] ✓ Self-Declaration Form downloaded: /path/to/form.pdf
[STATUS] Waiting for user to upload signed Self-Declaration Form...
[STATUS] ✓ Signed Self-Declaration uploaded: /path/to/signed.pdf
[STATUS] Step 3: Uploading Current Address Proof...
[STATUS] Requesting document number from user...
[STATUS] ✓ Document number filled: 607126530111
[STATUS] Address proof is PDF, converting to image...
[STATUS] ✓ PDF converted to image: /path/to/proof_converted.jpg
[STATUS] ✓ Address proof uploaded: /path/to/proof_converted.jpg
[STATUS] All documents uploaded! Looking for Submit/Proceed button...
[STATUS] ✓ Clicked 'Proceed' button
[STATUS] ✓ Form submitted successfully!
[STATUS] SUCCESS! Document upload process complete.
```

## Benefits

✅ Follows exact portal workflow (Select → Add → Upload)
✅ User can review and sign declaration form
✅ User can exit at any point if needed
✅ Handles PDF to image conversion automatically
✅ Only asks for document number when needed (address proof only)
✅ Clear user feedback at each step
✅ Robust error handling
✅ Flexible button detection (Proceed/Submit/Make Payment)
