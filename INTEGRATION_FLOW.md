# PAN Card Application - Complete Integration Flow

## Architecture Overview

```
┌──────────────┐
│   Frontend   │ (React - Port 5173)
│   (Vite)     │
└──────┬───────┘
       │
       ↓ HTTP REST API
┌──────────────────────────────────────────────────────────────────┐
│  Auth Backend (Node.js/Express - Port 4000)                      │
│  • Authentication & Authorization                                │
│  • Request validation                                            │
│  • Route proxying to microservices                               │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ↓
┌──────────────────────────────────────────────────────────────────┐
│  pan-rag (FastAPI - Port 8000)                                   │
│  • AI Chat Assistant (RAG + LLM)                                 │
│  • FlowManager (conversation state tracking)                     │
│  • Document upload orchestration                                 │
│  • **INTEGRATION ORCHESTRATOR** (finalize-application)           │
└──────┬──────────────────────────┬────────────────────────────────┘
       │                          │
       ↓                          ↓
┌──────────────────┐    ┌─────────────────────────┐
│ pan_verification │    │  voice-agent (Port 8002)│
│  (Flask - 5000)  │    │  • STT/TTS              │
│  • OCR/VLM       │    │  • Multi-language       │
│  • Extraction    │    └─────────────────────────┘
│  • Validation    │
└──────────────────┘
       │
       ↓
┌──────────────────────────────────────────────────────────────────┐
│  automation_agent (Playwright)                                   │
│  • Browser automation for NSDL portal                            │
│  • Form filling                                                  │
│  • Payment URL extraction                                        │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow - Complete Journey

### Phase 1: User Interaction & Document Upload

1. **User opens app** → Frontend loads
2. **User authenticates** → JWT token issued by Node backend
3. **User starts PAN application chat** → pan-rag creates session
4. **FlowManager starts guided flow:**
   - Applicant type selection
   - Submission mode (Aadhaar-based eKYC)
   - Delivery mode (Physical/Soft copy)
   - Personal details collection (name, email, income, etc.)
   - Document upload request

5. **User uploads documents:**
   ```
   Frontend → Node Backend → pan-rag /upload
                              ↓
                         pan_verification /api/verify
                              ↓
                         NVIDIA VLM extraction
                              ↓
                         Returns extracted fields
                              ↓
                         pan-rag stores in Redis
   ```

### Phase 2: Confirmation & Validation

6. **pan-rag shows confirmation panel** with all collected data
7. **User reviews and confirms** details
8. **FlowManager marks flow as complete**

### Phase 3: Finalization & Automation (NEW!)

9. **User clicks "Submit Application"**
10. **Frontend calls:** `POST /api/finalize-application`
    ```json
    {
      "session_id": "uuid",
      "trigger_automation": true
    }
    ```

11. **Node Backend → pan-rag `/api/finalize-application`**

12. **pan-rag Integration Orchestrator executes:**

    **Step 1:** Load FlowManager state
    ```python
    fm = FlowManager(session_id, user_id)
    state = fm.state
    # Contains: full_name, email, salary, residential_status, 
    #           submission_mode, delivery_mode, etc.
    ```

    **Step 2:** Load document extraction results from Redis
    ```python
    extraction_data = {
        "aadhaar": {...extracted fields...},
        "birth_certificate": {...extracted fields...},
        "profile_photo": {...metadata...},
        "signature": {...metadata...}
    }
    ```

    **Step 3:** Merge into automation_agent schema (30 fields)
    ```python
    automation_data = {
        "first_name": from FlowManager or Aadhaar,
        "last_name": from FlowManager or Aadhaar,
        "dob": from birth_cert or Aadhaar,
        "email": from FlowManager,
        "aadhaar_first_8": from Aadhaar extraction,
        "aadhaar_last_4": from Aadhaar extraction,
        # ... all 30 fields mapped
    }
    ```

    **Step 4:** Copy uploaded files to automation_agent/docs/
    ```
    storage/uploads/{session_id}/user_aadhaar.pdf
        → automation_agent/docs/jaadhar.pdf
    
    storage/uploads/{session_id}/user_photo.jpg
        → automation_agent/docs/jphoto.jpeg
    
    storage/uploads/{session_id}/user_signature.jpg
        → automation_agent/docs/jsign.jpeg
    
    storage/uploads/{session_id}/user_birthcert.pdf
        → automation_agent/docs/jbirthcert.pdf
    ```

    **Step 5:** Write automation_agent/data.json
    ```json
    {
      "first_name": "BHUVANESHKUMAR",
      "last_name": "SIVAKUMAR",
      ...all 30 fields...
      "photo_file": "docs/jphoto.jpeg",
      "aadhaar_pdf": "docs/jaadhar.pdf",
      "birth_cert_pdf": "docs/jbirthcert.pdf"
    }
    ```

    **Step 6:** Trigger automation_agent/main.py
    ```bash
    cd automation_agent
    .venv/Scripts/python.exe main.py
    ```

    **Step 7:** automation_agent executes:
    - Opens Chrome with Playwright
    - Navigates to NSDL portal
    - Fills all form fields from data.json
    - Uploads documents
    - Solves reCAPTCHA
    - Submits application
    - Captures payment URL
    - Returns payment_link.json

13. **pan-rag returns result to Node backend**
14. **Node backend returns to Frontend**
    ```json
    {
      "status": "success",
      "message": "Application submitted successfully!",
      "payment_info": {
        "payment_url": "https://...",
        "screenshot": "payment_page.png",
        "applicant_name": "BHUVANESHKUMAR SIVAKUMAR"
      }
    }
    ```

15. **Frontend shows payment link** to user

## API Endpoints

### Frontend → Node Backend

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat/messages` | POST | Send chat message |
| `/api/files/upload` | POST | Upload document |
| `/api/finalize-application` | POST | **Trigger complete integration** |

### Node Backend → pan-rag

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/ask` | POST | Process chat message |
| `/api/upload` | POST | Upload & extract document |
| `/api/finalize-application` | POST | **Integration orchestrator** |

### pan-rag → pan_verification

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/verify` | POST | Extract document fields |

## Data Schema Mapping

### FlowManager State → automation_agent data.json

| automation_agent field | Source | Priority |
|------------------------|--------|----------|
| `first_name` | FlowManager `full_name` (split) OR Aadhaar `first_name` | FlowManager preferred |
| `last_name` | FlowManager `full_name` (split) OR Aadhaar `last_name` | FlowManager preferred |
| `middle_name` | Aadhaar `middle_name` | |
| `dob` | Birth Certificate `dob` OR Aadhaar `dob` | Birth cert preferred |
| `email` | FlowManager `email` | Required from user |
| `phone` | Aadhaar `phone` OR `mobile_number` | |
| `aadhaar_first_8` | Aadhaar `aadhar_number[:8]` | |
| `aadhaar_last_4` | Aadhaar `aadhar_number[-4:]` | |
| `name_on_aadhaar` | Aadhaar `name` | Full name from card |
| `gender` | Aadhaar `gender` | |
| `father_first_name` | Aadhaar `father_name` (split) | |
| `father_last_name` | Aadhaar `father_name` (split) | |
| `mother_first_name` | FlowManager `mother_name` (split) OR Aadhaar | User preferred |
| `mother_middle_name` | Aadhaar `mother_middle_name` | |
| `mother_last_name` | FlowManager `mother_name` (split) | |
| `residential_status` | FlowManager `residential_status` | Required selection |
| `flat_room_door` | Aadhaar `flat_room_door` | Address field 1 |
| `building_village` | Aadhaar `building_village` | Address field 2 |
| `road_street_post` | Aadhaar `road_street_post` | Address field 3 |
| `area_locality` | Aadhaar `area_locality` | Address field 4 |
| `country` | Aadhaar `country` (default "INDIA") | |
| `state` | Aadhaar `state` | |
| `pin_code` | Aadhaar `pincode` | 6 digits |
| `verifier_place` | *(Not yet collected)* | TODO: Add to flow |
| `verifier_designation` | *(Not yet collected)* | TODO: Add to flow |
| `delivery_option` | FlowManager `delivery_mode` mapped | "physical" or "soft" |
| `photo_file` | Uploaded profile_photo → `docs/jphoto.jpeg` | |
| `signature_file` | Uploaded signature → `docs/jsign.jpeg` | |
| `aadhaar_pdf` | Uploaded aadhaar → `docs/jaadhar.pdf` | |
| `birth_cert_pdf` | Uploaded birth_certificate → `docs/jbirthcert.pdf` | |

## File Storage Locations

### During Upload Phase
```
pan-rag/storage/uploads/{session_id}/
  ├── user_aadhaar.pdf
  ├── user_profile_photo.jpg
  ├── user_signature.jpg
  └── user_birth_certificate.pdf
```

### After Finalization
```
automation_agent/docs/
  ├── jaadhar.pdf          (Aadhaar card)
  ├── jphoto.jpeg          (Profile photo)
  ├── jsign.jpeg           (Signature)
  └── jbirthcert.pdf       (Birth certificate)

automation_agent/data.json  (Complete 30-field schema)
```

## Running the Complete System

### Start All Services

```bash
# Terminal 1: pan_verification (Flask - Port 5000)
cd pan_verification
.venv\Scripts\activate
python app.py

# Terminal 2: pan-rag (FastAPI - Port 8000)
cd pan-rag
.venv\Scripts\activate
uvicorn api.main:app --reload --port 8000

# Terminal 3: voice-agent (FastAPI - Port 8002)
cd voice-agent
.venv\Scripts\activate
uvicorn main:app --reload --port 8002

# Terminal 4: auth-app backend (Node.js - Port 4000)
cd auth-app\backend
npm run dev

# Terminal 5: frontend (Vite - Port 5173)
cd frontend
npm run dev
```

### Test the Integration

1. Open http://localhost:5173
2. Create account / Login
3. Start PAN application chat
4. Upload documents (Aadhaar, birth certificate, photo, signature)
5. Confirm details
6. Click "Submit Application"
7. Wait for automation to complete
8. Receive payment URL

## Birth Certificate Handling

Birth certificates are fully supported:

1. **Upload:** User uploads birth certificate PDF/image
2. **Extraction:** pan_verification extracts:
   - `document_type`: "birth_certificate"
   - `name`: Child's name
   - `dob`: Date of birth (DD/MM/YYYY)
   - `doc_number`: Birth certificate number
   - `raw_fields`: Additional fields

3. **Storage:** Cached in Redis: `extraction:{session_id}:birth_certificate`
4. **Usage:** DOB from birth certificate is preferred over Aadhaar DOB
5. **File Copy:** Copied to `automation_agent/docs/jbirthcert.pdf`

## Missing Fields (TODO)

These fields are not yet collected by FlowManager but are required by automation_agent:

- `verifier_place` (e.g., "PUDUCHERRY")
- `verifier_designation` (e.g., "STUDENT", "SALARIED", etc.)

**Solution:** Add these fields to `details_collection` step in FlowManager.

## Troubleshooting

### Finalization fails with "No documents found"
- **Cause:** Documents not uploaded or session_id mismatch
- **Fix:** Ensure documents are uploaded before calling finalize

### Automation agent fails with "venv not found"
- **Cause:** Virtual environment not created
- **Fix:** Run `cd automation_agent && uv venv && uv pip install -r requirements.txt`

### Extraction results not found in Redis
- **Cause:** Redis not running or extraction failed
- **Fix:** Check pan_verification logs, ensure NVIDIA API key is set

### Files not copied to automation_agent/docs/
- **Cause:** Filename doesn't match expected patterns
- **Fix:** Check file_mapping in finalize-application endpoint

## Future Enhancements

1. **Orchestra Integration:** Replace simple merging with multi-document cross-validation
2. **Async Automation:** Run automation_agent as background task, poll for status
3. **Progress Updates:** WebSocket/SSE for real-time automation progress
4. **Error Recovery:** Retry failed automation steps
5. **Payment Integration:** Handle payment flow directly in app

## Security Notes

- All API calls require JWT authentication (except health checks)
- Document files are stored per-session with user isolation
- Redis keys include user_id to prevent cross-user access
- Uploaded files are validated for type and size
- automation_agent runs in isolated environment

## Testing Checklist

- [ ] User can upload Aadhaar PDF
- [ ] User can upload birth certificate PDF
- [ ] User can upload profile photo (JPEG)
- [ ] User can upload signature (JPEG)
- [ ] Extraction results are shown in chat
- [ ] Confirmation panel shows all details
- [ ] Finalize endpoint returns success
- [ ] data.json is created with all 30 fields
- [ ] Files are copied to automation_agent/docs/
- [ ] automation_agent executes successfully
- [ ] Payment URL is returned to frontend
- [ ] Payment link modal is shown to user

---

**Status:** ✅ Complete integration flow implemented  
**Last Updated:** 2026-06-28  
**Version:** 1.0
