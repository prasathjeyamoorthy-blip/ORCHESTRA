# Testing Document Upload Flow - Complete Guide

## What Was Fixed

### ✅ Issue 1: Flow Not Advancing After Document Upload
**Before:** After uploading all documents, system just showed summary and waited for user input
**After:** System automatically proceeds to next question after all required documents are uploaded

### ✅ Issue 2: Wrong Document Type Displayed
**Before:** Everything showed "Aadhaar detected!" regardless of actual document type
**After:** Shows correct type: "Photograph detected!", "Driving License detected!", etc.

### ✅ Issue 3: File Overwriting
**Before:** All files renamed to same name (aadhaar.pdf, aadhaar.pdf) causing overwrites
**After:** Unique filenames with timestamps (photograph_1782815028.jpg, aadhaar_1782815029.pdf)

### ✅ Issue 4: Document Type Mismatch
**Before:** Backend returned `profile_photo` but flow expected `photograph`
**After:** Automatic normalization: `profile_photo` → `photograph`, `aadhaar_card` → `aadhaar`

### ✅ Issue 5: Missing Signature Document
**Before:** Only 3 documents tracked (Aadhaar, Photo, Driving License)
**After:** 4 documents now tracked:
1. **Aadhaar** (required)
2. **Photograph** (required)  
3. **Signature** (required)
4. **Driving License** (optional - age proof)

---

## Required Documents

| Document | Status | Used For | File Types |
|----------|--------|----------|------------|
| **Aadhaar Card** | Required | Identity, Address, DOB | PDF |
| **Profile Photo** | Required | PAN card photo | JPG, JPEG |
| **Signature** | Required | PAN card signature | JPG, JPEG |
| **Driving License** | Optional | Age proof (alternative to birth certificate) | PDF |

---

## Testing Steps

### Test 1: Upload Documents in Correct Order

1. **Start Application**
   ```bash
   # Terminal 1: pan_verification
   cd d:\PANCARD\pan_verification
   .venv\Scripts\activate
   python app.py
   
   # Terminal 2: pan-rag
   cd d:\PANCARD\pan-rag
   .venv\Scripts\activate
   uvicorn api.main:app --reload --port 8000
   
   # Terminal 3: auth backend
   cd d:\PANCARD\auth-app\backend
   npm run dev
   
   # Terminal 4: frontend
   cd d:\PANCARD\frontend
   npm run dev
   ```

2. **Open Browser**
   - Go to http://localhost:5173
   - Login/Create account
   - Start PAN application chat

3. **Complete Initial Questions**
   - Answer all questions until you reach "Upload documents"
   - You should see: "I need your Aadhaar Card, Photograph, Signature, and optionally Driving License"

4. **Upload Photograph First**
   - Click paperclip icon
   - Select a JPG photo (e.g., `LOHITHG.jpg`)
   - Enter password
   - **Expected Result:**
     ```
     📄 Photograph detected!
     
     photograph_{timestamp}.jpg uploaded!
     
     One more — I still need your Aadhaar Card.
     ```

5. **Upload Aadhaar**
   - Click paperclip icon
   - Select Aadhaar PDF
   - Enter password
   - **Expected Result:**
     ```
     📄 Aadhaar detected!
     
     aadhaar_{timestamp}.pdf uploaded!
     
     One more — I still need your Signature.
     ```

6. **Upload Signature**
   - Click paperclip icon
   - Select signature image
   - Enter password
   - **Expected Result:**
     ```
     📄 Signature detected!
     
     signature_{timestamp}.jpg uploaded!
     
     Optional: I can also accept your Driving License for age proof.
     Or say "Continue" to proceed without it.
     ```

7. **Upload Driving License (Optional)**
   - Click paperclip icon
   - Select driving license PDF
   - Enter password
   - **Expected Result:**
     ```
     📄 Driving License detected!
     
     driving_license_{timestamp}.pdf uploaded!
     
     ✅ All documents uploaded successfully.
     
     [Automatically proceeds to next step - e.g., confirmation or summary]
     ```

---

### Test 2: Upload in Random Order

Upload documents in any order (e.g., Aadhaar first, then photo, then signature). System should:
- Correctly identify each document type
- Track which ones are still missing
- Show appropriate "One more — I still need your X" messages
- Automatically proceed when all required docs are uploaded

---

### Test 3: Verify File Storage

After uploading all documents, check the storage directory:

```bash
cd d:\PANCARD\pan-rag\storage\uploads
dir {your_session_id}
```

**Expected Files:**
```
photograph_1782815028123.jpg
aadhaar_1782815029456.pdf
signature_1782815030789.jpg
driving_license_1782815031012.pdf  (if uploaded)
```

**Each file should:**
- Have a unique timestamp
- NOT overwrite previous files
- Match the detected document type (not user-provided type)

---

### Test 4: Verify Redis Cache

Check that extraction results are cached with correct keys:

**Expected Redis Keys:**
```
extraction:{session_id}:aadhaar
extraction:{session_id}:photograph
extraction:{session_id}:signature
extraction:{session_id}:driving_license
```

---

### Test 5: Check Backend Logs

Monitor pan-rag terminal output. You should see:

```
✅ Extraction result for [unknown] session [xyz...]
      ℹ️ Detected document type: profile_photo → normalized to: photograph (user said: unknown)
      ✓ Renamed file to: photograph_1782815028123.jpg
      ✓ Extraction result cached in Redis with key: extraction:xyz:photograph
```

**Key Points:**
- User might say "unknown" (because frontend detection failed)
- Backend correctly detects actual type (e.g., `profile_photo`)
- System normalizes to expected type (e.g., `photograph`)
- File renamed with unique timestamp
- Cached with normalized type as key

---

## Common Issues & Solutions

### Issue: Still shows "Aadhaar detected!" for photos

**Cause:** Old code cached in browser or backend not restarted

**Solution:**
1. Hard refresh frontend: `Ctrl + Shift + R`
2. Restart pan-rag server:
   ```bash
   cd d:\PANCARD\pan-rag
   # Press Ctrl+C to stop
   uvicorn api.main:app --reload --port 8000
   ```

### Issue: Flow doesn't proceed after last document

**Cause:** FlowManager not advancing or `_ask_step()` not being called

**Solution:**
1. Check receptionist.py line 2748-2786
2. Verify `handle_document_upload()` calls `_ask_step(flow)`
3. Check service_flows.py has all 4 documents defined

### Issue: Files overwriting each other

**Cause:** Timestamp not being generated or files renamed without timestamp

**Solution:**
1. Check routes.py line ~606 - should use `timestamp = int(time.time() * 1000)`
2. Verify filename format: `{doc_type}_{timestamp}.{ext}`

### Issue: Documents not recognized by flow

**Cause:** Document type mismatch - normalization not working

**Solution:**
1. Check routes.py has `type_normalization` mapping
2. Verify backend logs show: "profile_photo → normalized to: photograph"
3. Check service_flows.py document keys match normalized types

---

## Verification Checklist

After uploading all documents, verify:

- [ ] Each document shows correct type in detection message
- [ ] Files stored with unique names (no overwrites)
- [ ] Flow automatically asks next question after all docs uploaded
- [ ] Extraction results cached in Redis with correct keys
- [ ] Backend logs show normalization working
- [ ] No "Aadhaar detected!" for non-Aadhaar documents
- [ ] System tracks 4 documents (not just 3)
- [ ] Driving license marked as optional

---

## Expected Full Flow

```
User: I want to apply for PAN
Bot: [Asks submission mode, delivery mode, etc.]
Bot: Now upload your documents...

User: [Uploads photo.jpg]
Bot: 📄 Photograph detected!
     photograph_1234.jpg uploaded!
     One more — I still need your Aadhaar Card.

User: [Uploads aadhar.pdf]
Bot: 📄 Aadhaar detected!
     aadhaar_5678.pdf uploaded!
     One more — I still need your Signature.

User: [Uploads sign.jpg]
Bot: 📄 Signature detected!
     signature_9012.jpg uploaded!
     Optional: Upload Driving License or say "Continue"

User: Continue
Bot: ✅ All documents uploaded successfully.
     
     [Shows confirmation panel with all collected info]
     OR
     [Asks next question automatically]
```

---

## Debug Commands

```bash
# Check uploaded files
ls d:\PANCARD\pan-rag\storage\uploads\{session_id}\

# Count files (should be 3 or 4)
(Get-ChildItem d:\PANCARD\pan-rag\storage\uploads\{session_id}\).Count

# Check if files have unique timestamps
Get-ChildItem d:\PANCARD\pan-rag\storage\uploads\{session_id}\ | Select-Object Name

# View pan-rag logs
cd d:\PANCARD\pan-rag
# Check terminal output for "Detected document type" messages

# Test document type detection in frontend
# Open browser console on localhost:5173
detectDocType('photo.jpg')        // Should return 'unknown' or 'profile_photo'
detectDocType('aadhar.pdf')       // Should return 'aadhaar'
detectDocType('driving_license.pdf') // Should return 'driving_license'
```

---

## Success Criteria

✅ **PASS** if:
1. Each document type correctly detected and displayed
2. Files stored with unique names (no overwrites)
3. Flow automatically proceeds after all required docs uploaded
4. 4 documents tracked (Aadhaar, Photo, Signature, DL)
5. Driving License optional, others required
6. Backend logs show normalization working
7. No "Aadhaar detected!" for non-Aadhaar files

❌ **FAIL** if:
1. All documents show "Aadhaar detected!"
2. Files overwrite each other
3. Flow stuck after uploading all documents
4. Only 3 documents tracked
5. Normalization not happening (backend logs don't show it)

---

## Files to Monitor

1. **Frontend:** `d:\PANCARD\frontend\src\App.jsx`
   - Watch browser console for errors
   - Check localStorage for session_id

2. **Backend:** `d:\PANCARD\pan-rag\api\routes.py`
   - Watch terminal for extraction results
   - Look for "Detected document type" messages

3. **Flow Manager:** `d:\PANCARD\pan-rag\agent\receptionist.py`
   - Watch for "handle_document_upload" calls
   - Check if "_ask_step()" is being called

4. **Document Verification:** `d:\PANCARD\pan_verification\app.py`
   - Watch for "Detecting document type" messages
   - Verify VLM detection responses

---

**Ready to test!** Follow the steps above and report any issues. 🚀
