# ⚡ Quick Test Checklist - Document Upload

## 🎯 What to Test

### ✅ Test 1: Correct Document Type Detection (2 min)
1. Upload photo JPG → Should say **"Photograph detected!"** (not "Aadhaar")
2. Upload Aadhaar PDF → Should say **"Aadhaar detected!"**
3. Upload signature JPG → Should say **"Signature detected!"**
4. Upload DL PDF → Should say **"Driving License detected!"**

**PASS:** ✅ Each document shows its correct type
**FAIL:** ❌ All show "Aadhaar detected!"

---

### ✅ Test 2: Unique File Names (1 min)
After uploading all documents, check:
```bash
dir d:\PANCARD\pan-rag\storage\uploads\{session_id}\
```

**PASS:** ✅ Files have timestamps (e.g., `photograph_1782815028.jpg`)
**FAIL:** ❌ Files overwrite each other (e.g., `aadhaar.pdf`, `aadhaar.pdf`)

---

### ✅ Test 3: Flow Auto-Progression (1 min)
Upload 3 required documents (Photo, Aadhaar, Signature)

**PASS:** ✅ After 3rd doc, system says "Optional: DL" or automatically asks next question
**FAIL:** ❌ Flow stuck, waits for user to say something

---

### ✅ Test 4: 4 Documents Tracked (1 min)
Upload documents one by one and watch messages

**PASS:** ✅ System asks for: Photo → Aadhaar → Signature → (Optional: DL)
**FAIL:** ❌ System only asks for 3 documents

---

### ✅ Test 5: Optional Document Handling (1 min)
After uploading Photo, Aadhaar, Signature:

Option A: Say "Continue" → Should proceed to next step
Option B: Upload DL → Should say "All docs uploaded" and proceed

**PASS:** ✅ Can proceed without DL OR upload DL and proceed
**FAIL:** ❌ Requires DL to proceed

---

## 🔍 Quick Verification

### Backend Logs Should Show:
```
Detected document type: profile_photo → normalized to: photograph
Renamed file to: photograph_1782815028.jpg
```

### Frontend Should Show:
```
📄 Photograph detected!
photograph_1782815028.jpg uploaded!
One more — I still need your Aadhaar Card.
```

### Files Should Be:
```
photograph_1782815028456.jpg   ✅ Unique timestamp
aadhaar_1782815029123.pdf      ✅ Different timestamp
signature_1782815030789.jpg    ✅ Different timestamp
```

---

## ⚡ 30-Second Smoke Test

1. **Upload photo** → See "Photograph detected!" ✅
2. **Check file** → Has timestamp in name ✅
3. **Upload 2 more required docs** → Flow proceeds automatically ✅

**If all 3 pass:** System is working correctly! 🎉

---

## 🚨 Red Flags

❌ **PROBLEM:** All docs show "Aadhaar detected!"
→ **FIX:** Restart pan-rag server, hard refresh browser

❌ **PROBLEM:** Files overwrite (same name)
→ **FIX:** Check routes.py line ~606, verify timestamp generation

❌ **PROBLEM:** Flow stuck after 3rd document
→ **FIX:** Check receptionist.py handle_document_upload calls _ask_step()

❌ **PROBLEM:** System asks for only 3 docs (no signature)
→ **FIX:** Check service_flows.py has signature document defined

---

## 🎯 Success Criteria

**All 5 tests pass** = ✅ Ready for production
**1-2 tests fail** = ⚠️ Need minor fixes
**3+ tests fail** = ❌ Code not updated correctly

---

## 📋 Quick Commands

```bash
# Restart backend
cd d:\PANCARD\pan-rag
# Ctrl+C to stop
uvicorn api.main:app --reload --port 8000

# Check files
dir d:\PANCARD\pan-rag\storage\uploads\{session_id}\

# Hard refresh browser
Ctrl + Shift + R
```

---

**Total Test Time: ~5 minutes**
**Files to Review:** 3 (Complete Fix Summary, Testing Guide, This Checklist)
