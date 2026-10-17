# Complete Automation Flow - Final Implementation

## Overview
End-to-end automation for TNeGA Residence Certificate application with user interaction at key points.

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: LOGIN & NAVIGATION                                     │
└─────────────────────────────────────────────────────────────────┘
1. Check connectivity (infinite retry every 5s)
2. Launch browser
3. Navigate to portal
4. Click "English Version"
5. Click "Citizen Login"
6. Fill username & password
7. ⏸️ PAUSE: Show CAPTCHA → User enters code
8. Click Login
9. Navigate to Revenue Department
10. Click Residence Certificate
11. Click Proceed

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: APPLICANT DETAILS                                      │
└─────────────────────────────────────────────────────────────────┘
12. Search CAN number
13. Fill Aadhaar number
14. Inject DOB
15. ⏸️ PAUSE: Generate OTP → User enters OTP
16. Click Confirm OTP
17. Click Proceed

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: ADDRESS FORM FILLING                                   │
└─────────────────────────────────────────────────────────────────┘
18. Fill all form fields (only if empty):
    - Applicant Name
    - Father Name
    - Gender (dropdown)
    - Religion (dropdown, wait 2s)
    - Community (dropdown, wait 2s)
    - State (dropdown, wait 3s)
    - District (dropdown, wait 3s)
    - Revenue Village (dropdown, uses area field)
    - Building No
    - Street Name
    - Pincode
    - From Date
    - To Date
    - Ration Card Number
19. Verify Revenue Village is selected
20. Click "Add" button
21. Click "Submit" button
22. ✓ Auto-click "OK" on warning dialog

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 4: DOCUMENT UPLOAD                                        │
└─────────────────────────────────────────────────────────────────┘

STEP 1: PHOTO
23. Select "Photo" from dropdown
24. Click "Add..." button
25. Upload photo (from frontend, auto-convert to image)
26. ✓ Photo uploaded

STEP 2: SELF-DECLARATION (INTERACTIVE)
27. Download blank form from portal
28. Save as: Self_Declaration_Form_To_Sign.pdf
29. ⏸️ PAUSE: Show modal to user
    - Download button (user downloads form)
    - User prints form
    - User signs form manually
    - User scans/photographs signed form
    - User uploads signed version via modal
    - OR user clicks Exit to stop automation
30. Frontend uploads signed file to backend
31. Backend saves file and returns path
32. Select "Self-Declaration of Applicant" from dropdown
33. Click "Add..." button
34. Upload signed form (auto-convert to image)
35. ✓ Signed declaration uploaded

STEP 3: ADDRESS PROOF (DRIVING LICENSE)
36. Select "Current Address Proof" from dropdown
37. Click "Add..." button
38. ⏸️ PAUSE: Ask for document number via modal
39. Fill document number
40. Upload driving license (from frontend, auto-convert to image)
41. ✓ Driving license uploaded

FINAL STEP
42. Click "Proceed" or "Submit" button
43. Wait for page load
44. ✓ Automation complete!

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 5: COMPLETION                                             │
└─────────────────────────────────────────────────────────────────┘
45. Browser closes
46. User completes payment manually (if required)
```

## User Interaction Points

### 1. CAPTCHA Entry
**When:** After entering credentials
**Modal:** AutomationModal
**Action:** User views CAPTCHA image and enters code
**Timeout:** None (waits indefinitely)

### 2. OTP Entry
**When:** After Aadhaar verification
**Modal:** AutomationModal
**Action:** User enters OTP received on mobile
**Timeout:** None (waits indefinitely)

### 3. Self-Declaration Signing
**When:** After form submission, on document upload page
**Modal:** SelfDeclarationModal
**Actions:**
- User clicks "Download Self-Declaration Form"
- User prints and signs the form
- User scans/photographs signed form
- User uploads signed version
- User clicks "Submit Signed Form" OR "Exit"
**Timeout:** None (waits indefinitely)
**Exit Option:** Yes (stops automation)

### 4. Document Number Entry
**When:** Before uploading address proof
**Modal:** DocumentNumberModal
**Action:** User enters driving license number
**Timeout:** None (waits indefinitely)

## Document Handling

### Documents from Frontend (Pre-uploaded)
| Document | Source | Usage |
|----------|--------|-------|
| Photo | `bulkData.saved_paths["Photo"]` | Uploaded in Step 1 |
| Driving License | `bulkData.saved_paths["Driving License"]` | Uploaded in Step 3 |

### Documents Generated During Automation
| Document | Source | Usage |
|----------|--------|-------|
| Self-Declaration | Downloaded from portal | User signs, re-uploads in Step 2 |

### Automatic PDF to Image Conversion
All documents are automatically converted to image format:
- **Method:** `ensure_image_format(file_path)`
- **Quality:** 200 DPI, 95% JPEG quality
- **Fallback:** If conversion fails, uploads PDF directly

## Key Features

### 1. Smart Field Filling
- ✅ Only fills empty fields (preserves pre-filled data)
- ✅ Checks dropdown state before selection
- ✅ Multiple fallback strategies for dropdown matching

### 2. Revenue Village Handling
- ✅ Uses `area` field as primary source
- ✅ Falls back to `village` if area not available
- ✅ Selects first available option if no match
- ✅ Final verification before clicking Add

### 3. Connectivity Resilience
- ✅ Infinite retry every 5 seconds
- ✅ Never gives up on connection
- ✅ Clear logging of each attempt

### 4. Dialog Handling
- ✅ Auto-accepts JavaScript dialogs
- ✅ Auto-clicks "OK" button on warning popups
- ✅ Handles both dialog types seamlessly

### 5. Self-Declaration Flow
- ✅ Always downloads from portal (fresh form)
- ✅ Shows downloadable link to user
- ✅ Waits for user to sign and re-upload
- ✅ Saves uploaded file to system
- ✅ Uses saved file for portal upload
- ✅ Converts to image automatically

## Error Handling

### Non-Critical Errors (Continue)
- Photo file not found
- Driving license not found (uses Aadhaar fallback)
- PDF conversion fails (uploads PDF directly)
- Mobile number field not found
- Email field not found

### Critical Errors (Stop)
- Connectivity check fails after max retries (if configured)
- User clicks "Exit" on self-declaration modal
- Submit/Proceed button not found after document upload

## Success Indicators

### Logs to Watch For
```
[STATUS] ✓ Portal is reachable!
[STATUS] ✓ Selected Revenue Village: Gundu Uppalavadi
[STATUS] Clicking Add button to submit address details...
[STATUS] Clicking Submit button to proceed to document upload page...
[STATUS] Found OK button on dialog, clicking it...
[STATUS] ✓ Form submitted successfully! Now on document upload page.
[STATUS] ✓ Photo uploaded: /path/to/photo.jpg
[STATUS] ✓ Self-Declaration Form downloaded: Self_Declaration_Form_To_Sign.pdf
[STATUS] ✓ Selected 'Self-Declaration of Applicant' from dropdown
[STATUS] ✓ Clicked 'Add...' button
[STATUS] ✓ Signed Self-Declaration uploaded: /path/to/signed_converted.jpg
[STATUS] ✓ Document number filled: TN3120250006924
[STATUS] ✓ Address proof (Driving License) uploaded: /path/to/dl_converted.jpg
[STATUS] ✓ Clicked 'Proceed' button
[STATUS] ✓ Form submitted successfully!
[STATUS] SUCCESS! Document upload process complete.
```

## Dependencies

### Python Packages
```bash
pip install playwright pdf2image Pillow fastapi uvicorn python-multipart
playwright install chromium
```

### System Requirements
```bash
# Ubuntu/Debian
sudo apt-get install poppler-utils

# macOS
brew install poppler

# Windows
# Download from: https://github.com/oschwartz10612/poppler-windows/releases
# Add to PATH
```

### Frontend Dependencies
```bash
cd ORCHESTRA/frontend
npm install
```

## API Endpoints

### Backend (Port 8000)

#### 1. Submit Application
```
POST /submit-application
Body: {
  credentials: {...},
  applicant_details: {...},
  address_details: {...},
  documents: {...}
}
```

#### 2. Download Declaration
```
GET /download-declaration
Returns: Self_Declaration_Form_To_Sign.pdf
```

#### 3. Upload Signed Declaration
```
POST /upload-signed-declaration
Body: FormData with file
Returns: { file_path: "/path/to/saved/file.pdf" }
```

#### 4. Get CAPTCHA
```
GET /automation/captcha
Returns: backend_captcha.png
```

#### 5. WebSocket
```
WS /ws/automation
Events: REQUEST_CAPTCHA, REQUEST_OTP, SELF_DECLARATION_DOWNLOADED, REQUEST_SIGNED_DECLARATION, REQUEST_DOCUMENT_NUMBER
```

## Testing Checklist

- [ ] Connectivity retry works
- [ ] CAPTCHA modal appears and accepts input
- [ ] OTP modal appears and accepts input
- [ ] All form fields fill correctly
- [ ] Revenue Village dropdown selects correctly
- [ ] Add button clicks successfully
- [ ] Submit button clicks successfully
- [ ] OK dialog auto-clicks
- [ ] Photo uploads (image format)
- [ ] Self-declaration downloads
- [ ] Self-declaration modal shows
- [ ] User can download form
- [ ] User can upload signed version
- [ ] Signed form saves to backend
- [ ] Signed form uploads to portal (image format)
- [ ] Document number modal appears
- [ ] Driving license uploads (image format)
- [ ] PDF to image conversion works
- [ ] Final submit button clicks
- [ ] Automation completes successfully

## Troubleshooting

### "Revenue Village is still on SELECT"
**Solution:** Automation will auto-select first available option before clicking Add

### "Address proof file not found"
**Solution:** Ensure driving license is uploaded in frontend checklist

### "Could not find Submit/Proceed button"
**Solution:** Check portal UI, button name may have changed

### "pdf2image not installed"
**Solution:** `pip install pdf2image` and install poppler

### "Signed declaration not uploading"
**Solution:** Check backend logs, ensure file was saved correctly

## Performance Notes

- Average completion time: 3-5 minutes (excluding user interaction time)
- CAPTCHA wait: User-dependent
- OTP wait: User-dependent
- Self-declaration signing: User-dependent (typically 2-5 minutes)
- Document number entry: ~10 seconds
- PDF conversion: ~2-3 seconds per document

## Security Considerations

- ✅ Credentials sent over HTTPS (in production)
- ✅ Files saved in secure Playwright directory
- ✅ WebSocket connection authenticated
- ✅ No sensitive data logged
- ✅ Temporary files cleaned up after automation
