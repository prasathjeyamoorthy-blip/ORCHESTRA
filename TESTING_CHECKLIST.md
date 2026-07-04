# Testing Checklist - PAN Application Integration

## Pre-Testing Setup

### 1. Verify All Services Are Running

```bash
# Check pan_verification (Port 5000)
curl http://localhost:5000/
# Expected: HTML page or {"status": "ok"}

# Check pan-rag (Port 8000)
curl http://localhost:8000/api/health
# Expected: {"status": "ok"}

# Check auth backend (Port 4000)
curl http://localhost:4000/api/auth/health
# Expected: Health check response

# Check frontend (Port 5173)
# Open browser: http://localhost:5173
```

### 2. Verify Virtual Environments Exist

```bash
# automation_agent venv
dir automation_agent\.venv\Scripts\python.exe
# Should exist

# pan-rag venv
dir pan-rag\.venv\Scripts\python.exe
# Should exist

# pan_verification venv
dir pan_verification\.venv\Scripts\python.exe
# Should exist
```

### 3. Verify Environment Variables

Check these files have required vars:
- `auth-app/backend/.env` - RAG_URL, CLIENT_URL, SUPABASE_*
- `pan-rag/.env` - NVIDIA_META_90B, UPSTASH_*
- `pan_verification/.env` - NVIDIA_META_11B, POPPLER_PATH

## Test Scenario 1: Data Preparation Only

### Steps

1. **Login to app**
   - Go to http://localhost:5173
   - Login with test account

2. **Start PAN application**
   - Click "Apply for PAN Card"
   - Chat: "I want to apply for new PAN"

3. **Upload documents**
   - Upload Aadhaar PDF
   - Upload birth certificate PDF
   - Upload profile photo JPEG
   - Upload signature JPEG
   - Wait for extraction confirmations

4. **Fill details**
   - Provide full name
   - Provide email
   - Provide salary/income
   - Select residential status

5. **Confirm details**
   - Review confirmation panel
   - Click "Confirm"

6. **Call finalize endpoint** (using browser console or Postman)

```javascript
// In browser console
fetch('/api/finalize-application', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  },
  body: JSON.stringify({
    session_id: 'YOUR_SESSION_ID',  // Get from chat state
    trigger_automation: false  // Just prepare, don't run automation
  })
})
.then(r => r.json())
.then(console.log)
```

### Expected Results

✅ **Response:**
```json
{
  "status": "success",
  "message": "Application data prepared successfully!",
  "automation_triggered": false,
  "data_prepared": {
    "first_name": "BHUVANESHKUMAR",
    "last_name": "SIVAKUMAR",
    ...30 fields total...
  }
}
```

✅ **Files Created:**
- `automation_agent/data.json` exists
- Contains all 30 fields
- Non-empty fields match your uploaded data

✅ **Files Copied:**
```
automation_agent/docs/
  ├── jaadhar.pdf
  ├── jphoto.jpeg
  ├── jsign.jpeg
  └── jbirthcert.pdf
```

### Verification Commands

```bash
# Check data.json was created
cat automation_agent\data.json | python -m json.tool

# Check files were copied
ls automation_agent\docs\

# Verify field count
cat automation_agent\data.json | python -c "import json, sys; print(len(json.load(sys.stdin)))"
# Expected: 30
```

## Test Scenario 2: Full Automation (Prepare + Execute)

⚠️ **Warning:** This will open a browser and attempt to fill the NSDL form

### Steps

1-5: Same as Scenario 1

6. **Call finalize with automation**

```javascript
fetch('/api/finalize-application', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  },
  body: JSON.stringify({
    session_id: 'YOUR_SESSION_ID',
    trigger_automation: true  // Enable automation
  })
})
.then(r => r.json())
.then(console.log)
```

### Expected Results

✅ **Chrome browser opens**
- Navigates to NSDL portal
- Fills contact form
- Solves reCAPTCHA (may require manual help)
- Proceeds through all form pages

✅ **Response (after 2-5 minutes):**
```json
{
  "status": "success",
  "message": "Application finalized and automation completed!",
  "automation_triggered": true,
  "payment_info": {
    "payment_url": "https://onlineservices.tin.egov-nsdl.com/...",
    "screenshot": "payment_page.png",
    "timestamp": "2026-06-28T...",
    "applicant_name": "BHUVANESHKUMAR SIVAKUMAR"
  }
}
```

✅ **Files Created:**
- `automation_agent/payment_link.json`
- `automation_agent/payment_page.png` (screenshot)

### Verification

```bash
# Check payment link was captured
cat automation_agent\payment_link.json

# View screenshot
start automation_agent\payment_page.png
```

## Test Scenario 3: Birth Certificate DOB Priority

### Test Data
- **Aadhaar DOB:** 15/08/1995
- **Birth Certificate DOB:** 18/01/2008

### Expected Behavior
The `data.json` should use **18/01/2008** (birth certificate DOB)

### Verification

```bash
# Check DOB in generated data.json
cat automation_agent\data.json | python -c "import json, sys; print('DOB:', json.load(sys.stdin)['dob'])"
# Expected: DOB: 18/01/2008
```

## Test Scenario 4: Name Splitting

### Test Data
- **Full name entered:** "BHUVANESHKUMAR SIVAKUMAR"

### Expected Split
```json
{
  "first_name": "BHUVANESHKUMAR",
  "last_name": "SIVAKUMAR",
  "middle_name": ""
}
```

### Test with Middle Name
- **Full name:** "JOHN MICHAEL DOE"

### Expected Split
```json
{
  "first_name": "JOHN",
  "middle_name": "MICHAEL",
  "last_name": "DOE"
}
```

## Test Scenario 5: Missing Documents

### Steps
1. Upload only Aadhaar (no birth certificate)
2. Call finalize

### Expected
```json
{
  "birth_cert_pdf": ""
}
```
✅ Should still work (empty string for missing fields)

## Test Scenario 6: Error Handling

### Test 6.1: No Active Flow
Call finalize before completing chat flow

**Expected:**
```json
{
  "status": "error",
  "message": "No active flow found. Please complete the application steps first."
}
```

### Test 6.2: No Documents Uploaded
Complete chat but don't upload any documents

**Expected:**
```json
{
  "status": "error",
  "message": "No documents found. Please upload required documents first."
}
```

### Test 6.3: Automation Failure
Trigger automation but simulate failure (e.g., network down)

**Expected:**
```json
{
  "status": "partial",
  "message": "Data prepared but automation failed. Check logs.",
  "automation_error": "..."
}
```

## Redis Cache Verification

### Check Extraction Results Are Cached

```bash
# Using redis-cli (if you have Redis locally)
redis-cli
> KEYS extraction:*
# Should show: extraction:{session_id}:aadhaar, extraction:{session_id}:birth_certificate, etc.

> GET extraction:{session_id}:aadhaar
# Should show: JSON with extracted fields

> TTL extraction:{session_id}:aadhaar
# Should show: ~604800 (7 days in seconds)
```

### Test Cache Expiry
Wait 7 days (or manually delete keys) and try finalize
**Expected:** Should fail gracefully with message about re-uploading documents

## Performance Testing

### Measure Finalize Endpoint Time

```bash
# Without automation (should be < 500ms)
time curl -X POST http://localhost:4000/api/finalize-application \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"session_id":"YOUR_ID","trigger_automation":false}'

# With automation (2-5 minutes)
time curl -X POST http://localhost:4000/api/finalize-application \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"session_id":"YOUR_ID","trigger_automation":true}'
```

## Log Verification

### Check Pan-Rag Logs

Look for finalize execution logs:
```
================================================================================
FINALIZING APPLICATION - Session: abc-123
================================================================================

[1/7] ✓ Loaded FlowManager state
      Service: pan_application
      Current step: summary
      Documents collected: 4

[2/7] ✓ Found 4 uploaded files
      - user_aadhaar.pdf
      - user_profile_photo.jpg
      - user_signature.jpg
      - user_birth_certificate.pdf

[3/7] ✓ Loaded extraction data for 4 document types
      - aadhaar
      - birth_certificate
      - profile_photo
      - signature

[4/7] ⚙️  Merging data into automation_agent schema...
      ✓ Merged 28 non-empty fields

[5/7] 📁 Copying files to automation_agent/docs/...
      ✓ user_aadhaar.pdf → jaadhar.pdf
      ✓ user_profile_photo.jpg → jphoto.jpeg
      ✓ user_signature.jpg → jsign.jpeg
      ✓ user_birth_certificate.pdf → jbirthcert.pdf
      Total files copied: 4

[6/7] 💾 Writing automation_agent/data.json...
      ✓ Written to D:\PANCARD\automation_agent\data.json

[7/7] 🤖 Triggering automation_agent...
      ✓ Automation completed successfully
```

### Check Automation Agent Logs

```
================================================================================
PAN CARD APPLICATION AUTOMATION
================================================================================

[*] Applicant: BHUVANESHKUMAR SIVAKUMAR
[*] Email: bhuvaneshnowhere@gmail.com

[OTP Server] Listening on http://0.0.0.0:5055
=== Step 1: Contact Form ===
[Step1] Page loaded.
[Step1] Starting reCAPTCHA solve.
[CAPTCHA] Recognized: 'example text'
[CAPTCHA] Solved!
Step 1 done.

=== Step 2: Token ===
Token: 1234567890
Step 2 done.

...

[✓] Automation completed successfully!
================================================================================
```

## Troubleshooting Common Issues

### Issue: "Module 'memory.memory_manager' not found"
**Fix:** Check pan-rag has memory_manager.py in memory/ directory

### Issue: "FlowManager import failed"
**Fix:** Check pan-rag has flow_manager.py in agent/ directory

### Issue: "Cannot copy file: Permission denied"
**Fix:** Check automation_agent/docs/ is writable

### Issue: "Subprocess failed: python not found"
**Fix:** Create automation_agent venv: `cd automation_agent && uv venv`

### Issue: "Redis connection failed"
**Fix:** Check UPSTASH_REDIS_REST_URL in pan-rag/.env

### Issue: "Extraction results not found"
**Fix:** Re-upload documents (cache may have expired)

## Success Criteria

✅ **All tests pass:**
- [ ] Data preparation works
- [ ] Files are copied correctly
- [ ] data.json has all 30 fields
- [ ] Birth certificate DOB is preferred
- [ ] Name splitting works correctly
- [ ] Empty fields use ""
- [ ] Redis caching works
- [ ] Automation triggers successfully
- [ ] Payment URL is returned

✅ **No errors in logs:**
- [ ] pan-rag logs clean
- [ ] Node backend logs clean
- [ ] automation_agent logs clean

✅ **Files exist after finalize:**
- [ ] automation_agent/data.json
- [ ] automation_agent/docs/jaadhar.pdf
- [ ] automation_agent/docs/jphoto.jpeg
- [ ] automation_agent/docs/jsign.jpeg
- [ ] automation_agent/docs/jbirthcert.pdf
- [ ] automation_agent/payment_link.json (if automation ran)

## Final Integration Test

Run complete end-to-end flow:

1. Start all 5 services
2. Create new user account
3. Complete entire PAN application via chat
4. Upload all 4 documents
5. Confirm details
6. Trigger finalization with automation
7. Receive payment URL
8. Verify all files created

**Total Time:** ~10-15 minutes  
**Expected Outcome:** Payment URL displayed, ready for payment

---

**Ready to Test!** 🚀

Start with Scenario 1 (data preparation only) to verify the integration works before testing full automation.
