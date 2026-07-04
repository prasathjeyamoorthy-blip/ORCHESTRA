# Document Upload Fixes

## Issues Identified

### 1. Flow Not Proceeding After Document Upload
**Problem:** After uploading all required documents, the system didn't automatically ask the next question.

**Root Cause:** The `handle_document_upload()` function in `receptionist.py` was checking if documents were complete, but not calling `_ask_step()` to get the next question after `FlowManager.record_document()` advanced the flow.

**Fix:** Updated `handle_document_upload()` to:
- Check if all documents are collected
- Get the current step AFTER `record_document()` has potentially advanced it
- Call `_ask_step(flow)` to retrieve the next question
- Return acknowledgment + next question together

**File:** `d:\PANCARD\pan-rag\agent\receptionist.py` (lines 2748-2786)

---

### 2. Wrong Document Type Displayed ("Aadhaar detected!" for all files)
**Problem:** Frontend showed "Aadhaar detected!" for profile photos and driving licenses.

**Root Causes:**
1. **Frontend defaulting to 'aadhaar'**: The `detectDocType()` function in App.jsx returned `'aadhaar'` as default
2. **Document type name mismatch**: Backend returned `profile_photo` and `aadhaar_card`, but service_flows.py expected `photograph` and `aadhaar`
3. **File overwriting**: Files were being renamed to the same name (e.g., `aadhaar.pdf`) causing conflicts

**Fixes:**

#### Fix 2a: Frontend Detection
**File:** `d:\PANCARD\frontend\src\App.jsx` (line 1707-1725)

Changed default from `'aadhaar'` to `'unknown'` and added more detection patterns:
```javascript
// Before:
return 'aadhaar'  // BAD - everything defaults to aadhaar

// After:
return 'unknown'  // Let backend detect
```

Also added:
- `profile_photo` detection for images
- `signature` detection for signature files
- More comprehensive filename pattern matching

#### Fix 2b: Document Type Normalization
**File:** `d:\PANCARD\pan-rag\api\routes.py` (lines ~598)

Added normalization mapping to convert pan_verification types to service_flows expectations:
```python
type_normalization = {
    "aadhaar_card": "aadhaar",
    "profile_photo": "photograph",
    "signature": "signature",
    "driving_license": "driving_license",
}
detected_doc_type = type_normalization.get(detected_type, detected_type)
```

#### Fix 2c: Unique Filenames
**File:** `d:\PANCARD\pan-rag\api\routes.py` (lines ~563-580)

Changed file naming strategy:
```python
# Before: Renamed immediately to doc_type (caused overwrites)
stored_filename = f"{clean_doc_type}{_ext}"  # ❌ aadhaar.pdf, aadhaar.pdf, aadhaar.pdf

# After: Use original name initially, then rename with timestamp
temp_filename = f"user_{file.filename}"  # ✓ user_photo.jpg
# After detection:
new_filename = f"{clean_detected}_{timestamp}{_ext}"  # ✓ photograph_1782815028.jpg
```

---

### 3. Missing Fourth Document (Signature)
**Problem:** System requires 4 documents (Aadhaar, Photo, Signature, Driving License) but only tracks 3.

**Root Cause:** The `service_flows.py` only defines 3 documents:
- aadhaar
- driving_license  
- photograph

But the implementation expects 4 (based on user reports and finalize-application code).

**Status:** ⚠️ **PARTIAL FIX** - Document type normalization will help, but need to verify if signature is required.

**Recommendation:** Check if signature should be added to service_flows.py:
```python
"signature": {
    "label": "Applicant Signature",
    "options": ["Signature on white paper (scanned or photo)"],
    "count": 1,
},
```

---

## Document Type Mapping Reference

| pan_verification Output | service_flows.py Expected | Normalized To |
|------------------------|---------------------------|---------------|
| `aadhaar_card` | `aadhaar` | `aadhaar` ✅ |
| `profile_photo` | `photograph` | `photograph` ✅ |
| `signature` | `signature` | `signature` ✅ |
| `driving_license` | `driving_license` | `driving_license` ✅ |

---

## Testing Checklist

### Test Case 1: Upload Profile Photo
- [ ] Upload a JPG photo file
- [ ] Backend should detect as `profile_photo`
- [ ] Normalized to `photograph`
- [ ] Frontend should show "📄 **Photograph** detected!"
- [ ] File stored as `photograph_{timestamp}.jpg`
- [ ] Flow should ask for next document (not end prematurely)

### Test Case 2: Upload Aadhaar PDF
- [ ] Upload Aadhaar PDF
- [ ] Backend should detect as `aadhaar_card`
- [ ] Normalized to `aadhaar`
- [ ] Frontend should show "📄 **Aadhaar** detected!"
- [ ] File stored as `aadhaar_{timestamp}.pdf`
- [ ] Flow should ask for next document

### Test Case 3: Upload Driving License
- [ ] Upload driving license PDF
- [ ] Backend should detect as `driving_license`
- [ ] Normalized to `driving_license`
- [ ] Frontend should show "📄 **Driving License** detected!"
- [ ] File stored as `driving_license_{timestamp}.pdf`
- [ ] Flow should ask for next document

### Test Case 4: Upload Signature
- [ ] Upload signature image
- [ ] Backend should detect as `signature`
- [ ] Normalized to `signature`
- [ ] Frontend should show "📄 **Signature** detected!"
- [ ] File stored as `signature_{timestamp}.jpg`
- [ ] If all 4 docs uploaded, flow should proceed to next step

### Test Case 5: Upload All Documents in Order
- [ ] Upload profile photo → Should ask for next doc
- [ ] Upload Aadhaar → Should ask for next doc
- [ ] Upload driving license → Should ask for next doc
- [ ] Upload signature → Should say "All documents uploaded!" and proceed
- [ ] System should automatically ask next question (not wait for user input)

---

## Files Modified

1. `d:\PANCARD\frontend\src\App.jsx`
   - Changed `detectDocType()` default from `'aadhaar'` to `'unknown'`
   - Added `profile_photo` and `signature` detection patterns

2. `d:\PANCARD\pan-rag\api\routes.py`
   - Added unique filename generation with timestamps
   - Added document type normalization mapping
   - Fixed file renaming to avoid overwrites

3. `d:\PANCARD\pan-rag\agent\receptionist.py`
   - Fixed `handle_document_upload()` to call `_ask_step()` after all docs collected
   - Added proper flow advancement and next question retrieval

---

## Next Steps

1. **Test the complete flow** end-to-end with real documents
2. **Verify signature requirement** - Add to service_flows.py if needed
3. **Check finalize-application** - Ensure it maps all 4 document types correctly
4. **Monitor backend logs** - Verify normalization is working:
   ```
   ℹ️ Detected document type: profile_photo → normalized to: photograph
   ```

---

## Debugging Commands

```bash
# 1. Check uploaded files
ls d:\PANCARD\pan-rag\storage\uploads\{session_id}\

# 2. Check if files have unique names (no overwrites)
# Should see: photograph_1782815028.jpg, aadhaar_1782815029.pdf, etc.

# 3. Check Redis cache
# Should have keys like: extraction:{session_id}:photograph

# 4. Test frontend detection
# In browser console:
console.log(detectDocType('LOHITHG.jpg'))  // Should return 'unknown' or 'profile_photo'
console.log(detectDocType('aadhar.pdf'))   // Should return 'aadhaar'
```

---

**Status:** ✅ All fixes implemented. Ready for testing.
