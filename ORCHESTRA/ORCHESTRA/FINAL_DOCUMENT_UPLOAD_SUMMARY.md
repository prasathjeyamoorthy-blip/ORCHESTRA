# Final Document Upload Implementation

## Complete Flow

### Documents Used (All from Frontend Upload)

| Document | Source | Format Handling | Document Number |
|----------|--------|-----------------|-----------------|
| **Photo** | `bulkData.saved_paths["Photo"]` | Auto-convert to image | ❌ Empty |
| **Self-Declaration** | User signs & uploads | Auto-convert to image | ❌ Empty |
| **Address Proof** | `bulkData.saved_paths["Driving License"]` (fallback: Aadhaar) | Auto-convert to image | ✅ User provides via modal |

## Step-by-Step Process

### 1. Photo Upload
```
Select "Photo" → Click "Add..." → Upload photo (auto-converted to image)
```
- Uses: `photo_path` from frontend
- Conversion: PDF → JPG (if needed)
- Document Number: Empty

### 2. Self-Declaration Form
```
Download blank form → User signs → Upload signed version
```
- Downloads blank form from portal
- Shows modal to user
- User downloads, prints, signs, scans
- User uploads signed version via modal
- Conversion: PDF → JPG (if needed)
- Document Number: Empty

### 3. Address Proof (Driving License)
```
Select "Current Address Proof" → Click "Add..." → Ask doc number → Upload driving license
```
- **Primary**: Uses `driving_license_path` from frontend
- **Fallback**: Uses `address_proof_path` if driving license not available
- Asks user for document number via modal
- Conversion: PDF → JPG (if needed)
- Document Number: User provides (e.g., Driving License number)

### 4. Final Submit
```
Click "Proceed" or "Submit" button
```
- Tries multiple button names
- Waits for page load
- Automation complete

## PDF to Image Conversion

### Function: `ensure_image_format(file_path)`

**Logic:**
1. Check if file is already an image (.jpg, .jpeg, .png, .gif) → Return as-is
2. If PDF → Convert first page to JPG (200 DPI, 95% quality)
3. If conversion fails → Try uploading PDF directly
4. Return converted image path

**Benefits:**
- ✅ Consistent image format across all documents
- ✅ High quality (200 DPI)
- ✅ Optimized file size (95% JPEG quality)
- ✅ Automatic fallback to PDF if conversion fails

## Payload Structure

### Frontend to Backend
```json
{
  "credentials": {
    "username": "string",
    "password": "string"
  },
  "applicant_details": {
    "can_number": "string",
    "aadhar_number": "string",
    "dob": "string",
    "ration_card_no": "string",
    "name": "string",
    "father_name": "string",
    "gender": "string",
    "religion": "string",
    "community": "string",
    "mobile_number": "string",
    "email": "string"
  },
  "address_details": {
    "state": "string",
    "district": "string",
    "village": "string",
    "area": "string",
    "building_no": "string",
    "street_name": "string",
    "pincode": "string",
    "from_date": "string",
    "to_date": "string"
  },
  "documents": {
    "photo_path": "/path/to/photo.jpg",
    "self_decl_path": "",
    "address_proof_path": "/path/to/aadhaar.pdf",
    "driving_license_path": "/path/to/driving_license.pdf",
    "address_doc_no": "string"
  }
}
```

## User Interactions

### 1. Continue to Upload
**Trigger:** After form submission
**Action:** User clicks "Continue" button
**Purpose:** Confirm ready to start document upload

### 2. Sign Self-Declaration
**Trigger:** After downloading blank form
**Modal:** SelfDeclarationModal
**Actions:**
- Download form
- Sign it manually
- Upload signed version
- OR Exit automation

### 3. Provide Document Number
**Trigger:** Before uploading address proof
**Modal:** DocumentNumberModal
**Action:** Enter driving license number (or other document number)

## Error Handling

### Photo Not Found
```
✗ WARNING: Photo file not found!
→ Continues to next step
```

### Driving License Not Found
```
✗ WARNING: Driving License or Address proof file not found!
→ Continues to next step
```

### PDF Conversion Fails
```
✗ WARNING: pdf2image not installed. Trying to upload PDF directly...
→ Uploads PDF instead of image
```

### Submit Button Not Found
```
⚠ WARNING: Could not find Submit/Proceed button. Please check manually.
→ Automation stops, user must proceed manually
```

## Success Logs

```
[STATUS] Starting Document Upload Process...

[STATUS] Step 1: Uploading Photo...
[STATUS] File is already in image format: /path/to/photo.jpg
[STATUS] ✓ Photo uploaded: /path/to/photo.jpg

[STATUS] Step 2: Handling Self-Declaration Form...
[STATUS] Downloading Self-Declaration Form from portal...
[STATUS] ✓ Self-Declaration Form downloaded: Self_Declaration_Form_To_Sign.pdf
[STATUS] Waiting for user to upload signed Self-Declaration Form...
[WebSocket] Received from frontend: {'type': 'USER_ANSWER', 'data': '/path/to/signed.pdf'}
[STATUS] Uploading signed Self-Declaration Form to portal...
[STATUS] Converting PDF to image: /path/to/signed.pdf
[STATUS] ✓ PDF converted to image: /path/to/signed_converted.jpg
[STATUS] ✓ Signed Self-Declaration uploaded: /path/to/signed_converted.jpg

[STATUS] Step 3: Uploading Current Address Proof (Driving License)...
[STATUS] Requesting document number from user...
[WebSocket] Received from frontend: {'type': 'USER_ANSWER', 'data': 'TN3120250006924'}
[STATUS] ✓ Document number filled: TN3120250006924
[STATUS] Using document: /path/to/driving_license.pdf
[STATUS] Converting PDF to image: /path/to/driving_license.pdf
[STATUS] ✓ PDF converted to image: /path/to/driving_license_converted.jpg
[STATUS] ✓ Address proof (Driving License) uploaded: /path/to/driving_license_converted.jpg

[STATUS] All documents uploaded! Looking for Submit/Proceed button...
[STATUS] ✓ Clicked 'Proceed' button
[STATUS] ✓ Form submitted successfully!
[STATUS] SUCCESS! Document upload process complete.
```

## Dependencies

### Python Packages
```bash
pip install pdf2image Pillow
```

### System Requirements
```bash
# Ubuntu/Debian
sudo apt-get install poppler-utils

# macOS
brew install poppler

# Windows
# Download poppler binaries from: https://github.com/oschwartz10612/poppler-windows/releases
# Add to PATH
```

## Key Features

✅ **All documents from frontend** - No manual file selection during automation
✅ **Automatic PDF conversion** - All documents converted to images
✅ **Driving license as address proof** - Primary choice for address verification
✅ **Fallback to Aadhaar** - If driving license not available
✅ **User-friendly modals** - Clear instructions for each interaction
✅ **Exit option** - User can stop automation at self-declaration step
✅ **Robust error handling** - Continues even if some steps fail
✅ **High-quality images** - 200 DPI, 95% JPEG quality

## Testing Checklist

- [ ] Photo uploads successfully (image format)
- [ ] Photo uploads successfully (PDF converted to image)
- [ ] Self-declaration downloads from portal
- [ ] User can download form from modal
- [ ] User can upload signed version
- [ ] Signed PDF converts to image
- [ ] Exit button stops automation
- [ ] Document number modal appears
- [ ] User can enter driving license number
- [ ] Driving license PDF converts to image
- [ ] Driving license image uploads successfully
- [ ] Fallback to Aadhaar if driving license missing
- [ ] Submit/Proceed button clicks successfully
- [ ] Automation completes without errors

## Troubleshooting

### "Address proof file not found"
**Cause:** Neither driving license nor Aadhaar uploaded in frontend
**Solution:** Ensure at least one address proof document is uploaded in the checklist

### "pdf2image not installed"
**Cause:** Missing pdf2image Python package
**Solution:** `pip install pdf2image` and install poppler

### "Could not find Submit/Proceed button"
**Cause:** Portal UI changed or button has different name
**Solution:** Check portal manually, update button names in code

### "Document number field not found"
**Cause:** Portal UI changed or field ID different
**Solution:** Inspect portal HTML, update field selector in code
