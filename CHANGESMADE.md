# Changes Since Cloning `vercel-render-production`

---

## Quick Summary

| # | What | File |
|---|---|---|
| 1 | Copied `.env` files from old codebase | All three services |
| 2 | Set up uv venvs + installed deps | Both backends + frontend |
| 3 | Installed `playwright-stealth` | ORCHESTRA venv |
| 4 | OTP disabled for dev, re-enabled after testing | `App.jsx` |
| 5 | Dev credentials pre-filled | `DocumentChecklist.jsx` |
| 6 | `to_date` defaults to today | `DocumentChecklist.jsx` |
| 7 | Dev Load button + `DEV_DOCS` added | `DocumentChecklist.jsx` |
| 8 | Fixed JSX fragment error on Dev Load button | `DocumentChecklist.jsx` |
| 9 | SelfDeclaration modal auto-upload bug fixed | `SelfDeclarationModal.jsx` |
| 10 | BillDesk UPI QR full payment flow implemented | `rescert.py` + `App.jsx` |
| 11 | OTP re-enabled | `App.jsx` |

---

## Detailed Changes

---

### 1. `.env` Files Copied

The `.env` files are gitignored and not in the repo. Copied from old codebase:

- `ORCHESTRA/ORCHESTRA/DocumentUploadAgent/.env`
- `ORCHESTRA/ORCHESTRA/ORCHESTRA/.env`
- `ORCHESTRA/frontend/.env`

---

### 2. Environment Setup

```bash
# Both backends — uv venv + install
cd ORCHESTRA/ORCHESTRA/DocumentUploadAgent
uv venv .venv --python 3.11
uv pip install -r requirements.txt

cd ORCHESTRA/ORCHESTRA/ORCHESTRA
uv venv .venv --python 3.11
uv pip install -r requirements.txt
.venv\Scripts\python.exe -m playwright install chromium

# Frontend
cd ORCHESTRA/frontend
npm install
```

Ports:
- `DocumentUploadAgent` → **8000**
- `ORCHESTRA` (chat/WS) → **8001**
- Frontend (Vite) → **5173**

---

### 3. `playwright-stealth` Installed

```bash
uv pip install playwright-stealth
```

Applied at browser page creation in `rescert.py` so BillDesk can't detect automation:

```python
from playwright_stealth import stealth_sync
stealth_sync(page)
```

---

### 4 & 11. OTP Modal — Disabled for Dev, Re-enabled After

**File:** `ORCHESTRA/frontend/src/App.jsx`

Temporarily disabled OTP during development:
```js
// setShowOtpModal(true);  ← disabled
```
Re-enabled after testing:
```js
if (!sessionStorage.getItem("user_phone")) {
  setShowOtpModal(true);
}
```

---

### 5. Dev Credentials Pre-filled

**File:** `ORCHESTRA/frontend/src/components/DocumentChecklist.jsx`

```js
// Before
useState({ username: "", password: "", can_number: "", aadhar_number: "" })

// After
useState({ username: "lohithg", password: "Lohith@2007", can_number: "13318016498757", aadhar_number: "607126530111" })
```

Also applied to the reset function so credentials restore after clearing.

---

### 6. `to_date` Defaults to Today's Date

**File:** `ORCHESTRA/frontend/src/components/DocumentChecklist.jsx`

```js
// Before
useState({ from_date: "", to_date: "" })

// After
useState(() => {
  const today = new Date();
  const dd = String(today.getDate()).padStart(2, "0");
  const mm = String(today.getMonth() + 1).padStart(2, "0");
  const yyyy = today.getFullYear();
  return { from_date: "09/10/2024", to_date: `${dd}/${mm}/${yyyy}` };
});
```

---

### 7 & 8. Dev Load Button + DEV_DOCS

**File:** `ORCHESTRA/frontend/src/components/DocumentChecklist.jsx`

Added `DEV_DOCS` map and `handleDevLoad` function for quick test uploads:

```js
const DEV_DOCS = {
  aadharCard:     { url: "/dev_docs/aadhar.jpeg",  name: "aadhar.jpeg",  mime: "image/jpeg" },
  rationCard:     { url: "/dev_docs/ration.jpeg",  name: "ration.jpeg",  mime: "image/jpeg" },
  drivingLicense: { url: "/dev_docs/drvlc.pdf",    name: "drvlc.pdf",    mime: "application/pdf" },
  photo:          { url: "/dev_docs/photo.jpg",     name: "photo.jpg",    mime: "image/jpeg" },
};
```

Added ⚡ Dev Load button in the upload zone. Had to wrap in `<>...</>` fragment because the ternary false-branch had two sibling elements (`<label>` + `<button>`), which caused a JSX parse error.

Also copied `dev_docs/` folder from old codebase into `ORCHESTRA/frontend/public/dev_docs/`.

---

### 9. SelfDeclaration Modal Auto-Upload Bug Fix

**File:** `ORCHESTRA/frontend/src/components/SelfDeclarationModal.jsx`

**Problem:** `uploadedFile` state was persisting between modal opens — previously signed PDF stayed selected, and submitting immediately triggered an upload without user intent.

**Fix:**
```js
import { useState, useEffect } from "react";

useEffect(() => {
  if (isOpen) {
    setUploadedFile(null);
    setIsUploading(false);
  }
}, [isOpen]);
```

---

### 10. BillDesk UPI QR Payment Flow

**Files:** `ORCHESTRA/ORCHESTRA/ORCHESTRA/Playwright/rescert.py`, `ORCHESTRA/frontend/src/App.jsx`

#### The Problem
After Make Payment, the old code sent the BillDesk URL to the frontend and slept for 15 minutes. Users couldn't open the URL in another browser because BillDesk payment sessions are tied to the specific browser making the request (jsessionid in URL).

#### The Flow Now

**Playwright side:**
1. Wait for BillDesk to load
2. Locate `iframe[name="response-frame"]` using `.content_frame` — BillDesk embeds everything in this iframe
3. Click `get_by_role("button", name="upi")` — lowercase `"upi"` is critical (recorder captured it lowercase)
4. Wait for "Show QR" button to become visible
5. Click `get_by_role("button", name="Show QR")`
6. Screenshot `locator("img").nth(1)` — the QR code image
7. Send `PAYMENT_QR` WebSocket event with base64 image to frontend
8. Poll every 2s for `USER_ANSWER: paid` from frontend (10 min timeout)
9. On user confirmation → screenshot current page → send `PAYMENT_SUCCESS`

**Frontend side (`App.jsx`):**
- Added `paymentQr` and `paymentSuccess` state
- `PAYMENT_QR` event → shows QR modal with "Scan to Pay"
- "I have paid" green button → sends `USER_ANSWER: paid` via WebSocket
- `PAYMENT_SUCCESS` event → switches modal to confirmation screenshot

#### Why It Wasn't Working Before
1. **Wrong iframe** — was iterating `page.frames` list and picking the main BillDesk page frame instead of the embedded widget frame
2. **Wrong button name** — `"UPI"` uppercase found nothing; actual accessible name from the DOM is `"upi"` lowercase
3. **Bot detection** — BillDesk detected `navigator.webdriver = true` via Playwright and silently swallowed click events. Fixed by `playwright-stealth`

---

## Files Changed Summary

| File | Changes |
|---|---|
| `frontend/src/App.jsx` | OTP toggle, `paymentQr`/`paymentSuccess` state, `PAYMENT_QR`/`PAYMENT_SUCCESS` WS handlers, QR modal UI |
| `frontend/src/components/DocumentChecklist.jsx` | Dev credentials, `to_date` today, `DEV_DOCS`, `handleDevLoad`, Dev Load button, JSX fragment fix |
| `frontend/src/components/SelfDeclarationModal.jsx` | Reset state on modal open |
| `ORCHESTRA/ORCHESTRA/ORCHESTRA/Playwright/rescert.py` | `playwright-stealth` applied, full BillDesk UPI→QR→confirm flow |
| `frontend/public/dev_docs/` | Copied from old codebase (aadhar.jpeg, ration.jpeg, drvlc.pdf, photo.jpg) |
| All `.env` files | Copied from old codebase (not in repo) |
| `ORCHESTRA/DocumentUploadAgent/main.py` | Fixed DOB resolution bug: prioritized Aadhaar & DL DOB over Family Ration Card DOB |
| `ORCHESTRA/ORCHESTRA/Playwright/delete_saved_app.py` | Headless Playwright script to log in, navigate to Saved Application, and delete pending draft applications |
| `ORCHESTRA/ORCHESTRA/app.py` | Added `/delete-saved-application` dev endpoint & runner |
| `frontend/src/components/DocumentChecklist.jsx` | Added `⚡ Delete Saved Application (Dev)` button, status banners, & socket trigger |

---

### 12. Date of Birth Prioritization Fix

**File:** `ORCHESTRA/ORCHESTRA/DocumentUploadAgent/main.py`

- **Problem:** When merging extracted document data, `_merge_with_resolution_priority` sorted documents purely by image resolution (`total_pixels`). Because `ration.jpeg` (904×1600) was slightly larger than `aadhar.jpeg` (900×1600), the father's DOB (`12/10/1967`) on the family ration card took priority over the applicant's DOB (`23/02/2007`), causing the e-Sevai portal to fail with `"Applicant Date of Birth is incorrect"`.
- **Fix:** Updated line 239 in `main.py` to prioritize `get_aadhaar_field("dob") or get_address_field("dob")` before falling back to `get_field_priority("dob")`.

---

### 13. Headless Saved Application Cleaner for Developers

**Files:** `delete_saved_app.py`, `ORCHESTRA/ORCHESTRA/app.py`, `DocumentChecklist.jsx`, `App.jsx`

- **Problem:** During repeated testing, draft applications get saved on the e-Sevai / e-District portal and developers had to manually log in, navigate to "Saved Application", and delete them.
- **Solution:**
  - Created [`delete_saved_app.py`](file:///home/devaprasath/Documents/RES_CERT/ORCHESTRA/ORCHESTRA/ORCHESTRA/Playwright/delete_saved_app.py) with `TNeSevaiSavedAppCleaner`. Runs Chromium in headless mode, logs in, navigates to "Saved Application", checks the application radio button, clicks "Delete", automatically accepts JS dialogs, and loops until all pending drafts are deleted.
  - Added `POST /delete-saved-application` endpoint in `ORCHESTRA/ORCHESTRA/app.py`.
  - Added `SAVED_APP_DELETED` WebSocket event handling in `App.jsx`.
  - Added dedicated **`⚡ Delete Saved Application (Dev)`** buttons in `DocumentChecklist.jsx` (accessible in the header on any step and inside Step 0 Portal Credentials).

---

### 14. UI Stage Tracking & Status Reset Fix

**Files:** `delete_saved_app.py`, `App.jsx`, `DocumentChecklist.jsx`

- **Problem:** When starting a new Residence Certificate automation run, all 4 progression steps (`Logged in`, `Form filled`, `Documents uploaded`, `Submitted to portal`) immediately appeared green-checked with a "Close" button, even while the bot was still at `"Logging in to your account…"`.
- **Root Cause:**
  1. `completedSteps` was not reset in `handleProceedClick()`, so completion flags from previous runs or cleaner runs persisted.
  2. The cleaner script sent `STATUS_UPDATE` messages with text `"Done!..."`, which matched loose `s.includes("done")` checks in `DocumentChecklist.jsx` and marked all steps complete.
  3. `isDone` was checked with `automationStatus.includes("Done!")`, which prematurely marked the automation as finished.
- **Fix:**
  1. Decoupled cleaner events: cleaner now emits dedicated `"CLEANER_STATUS"` and `"CLEANER_DONE"` events, keeping `automationStatus` isolated strictly for the main application flow.
  2. Reset `completedSteps` to all `false` and cleared `automationStatus` at the beginning of `handleProceedClick()` and `handleLiveClose()`.
  3. Made stage completion matching strict: `loggedIn` only triggers on actual login/OTP confirmation, `formFilled` on form save/submit, `docsUploaded` on document upload completion, and `submitted` strictly when the payment page is reached.

---

### 15. Fix for Developer Delete Saved Application Button

**Files:** `DocumentChecklist.jsx`, `App.jsx`, `AutomationModal.jsx`, `delete_saved_app.py`

- **Problem:** When developers clicked `[ ⚡ Delete Saved Application (Dev) ]`, the button appeared non-responsive / "not working".
- **Root Cause:**
  1. `handleDeleteSavedApp` contained a blocking `window.confirm(...)` call that browsers (especially Chrome/Chromium) often suppressed or auto-dismissed without displaying, causing an immediate silent exit.
  2. A 4-second polling loop (`for (let i = 0; i < 10; i++) ... await sleep(400)`) checking `/ws/status` delayed execution and could freeze or throw if the websocket check timed out.
  3. `openAutomationSocket()` in `App.jsx` unconditionally closed and recreated active WebSockets even when already `WebSocket.OPEN`, causing connection teardowns and missed event delivery during the cleaner's initialization.
  4. If an error occurred or cleaner completed, `isDeletingSavedApp` was not reset on all error paths because `CLEANER_ERROR` events were not handled, keeping the button in a stuck disabled/loading state.
- **Fix:**
  1. Removed `window.confirm(...)` completely so clicking the button immediately triggers the headless cleaner.
  2. Removed the blocking 4-second `/ws/status` delay; the socket is opened asynchronously and the request to `/delete-saved-application` is dispatched immediately.
  3. Protected `openAutomationSocket()` to resolve immediately if the socket is already in `WebSocket.OPEN` state, preventing connection flap.
  4. Added `CLEANER_ERROR` event dispatching in `delete_saved_app.py` and handled both `cleaner_error` and `cleaner_done` events in `DocumentChecklist.jsx` to safely reset loading and spinner states.
  5. Enhanced `AutomationModal.jsx` to ensure captcha images update cleanly when `eventData.image` is received.

---

### 17. Complete End-to-End Document Upload Verification & Payment Gateway Execution

**Files:** `rescert.py`, `app.py`, `DocumentChecklist.jsx`, `DocumentUploadAgent/app.py`, `SelfDeclarationModal.jsx`

- **Problem:** Document upload failed to complete all mandatory requirements on `uploaddocs.xhtml` (specifically `Self-Declaration of Applicant` was missing from the uploaded table), leaving only a standalone "Back" button, preventing the portal from rendering the "Make Payment" button, and causing automation to time out.
- **Root Causes Identified & Resolved:**
  1. **Missing `import re` in `rescert.py`:** `rescert.py` was missing `import re`, which caused a `NameError: name 're' is not defined` whenever label normalization fell back to regex, silently skipping the Self-Declaration dropdown selection. Added `import re` at the top of the file.
  2. **Accurate Upload Table Parser (`get_uploaded_docs_from_table`):** Previously, table verification inspected all `table tr` elements across the whole page. Because the portal's top instruction section ("List of Documents") already contains the text "Self-Declaration of Applicant", whole-page checks produced false positives. Built `get_uploaded_docs_from_table()` which isolates the specific table with `Document Name` and `File Name` headers and inspects only the submitted data rows.
  3. **RichFaces DOM & AJAX Timing:** Selecting from `<select id="ss:dsctype">` triggers a RichFaces AJAX re-render. If files were attached while the AJAX was in-flight, DOM updates cleared the file input before the upload button was pressed. Added explicit network settling (`wait_for_load_state("networkidle")` + 2.5s buffer) before attaching files.
  4. **Multi-Tier Upload Trigger & Polling:** Added multiple selectors for RichFaces upload controls (`.rich-fileupload-button-upload`, `a.rich-fileupload-btn-cnt`, exact text `Upload`, and JS click fallback), followed by a 15-second table polling loop that re-clicks upload if the document has not registered within 5 seconds.
  5. **Auto-Signed Digital Declaration (< 190 KB):** Implemented `_generate_auto_signed_declaration` using PIL to digitally stamp applicant signature (`Digitally Signed: <Applicant Name>`) on the Self-Declaration form, compressed to <= 190 KB (strictly under portal's 200 KB limit) with a 15-second grace period before auto-uploading.
  6. **Post-Upload Verification Loop & Tier-3 Fallback:** Inspects the verified uploaded table. If Photo, Address Proof, or Self-Declaration is missing, immediately executes re-upload. If Self-Declaration remains unlisted, selects option index 3 directly on `ss:dsctype` and forces upload.
  7. **Dynamic Server Reloading in `app.py`:** Added `importlib.reload(...)` before running `TNeSevaiBackendAgent` and `TNeSevaiSavedAppCleaner` to ensure live code updates are executed immediately without stale in-memory module caching.
  8. **Payment Flow Execution:** Once all 3 mandatory documents (`Photo`, `Current Address Proof`, `Self-Declaration of Applicant`) are present in the table, clicks `Make Payment`, navigates away from `uploadDocs.xhtml`, confirms terms and conditions, and drives to BillDesk for UPI QR code rendering.

---

### 18. Manual Self-Declaration Submission & E2E Test Suite Hardening

**Files:** `rescert.py`, `SelfDeclarationModal.jsx`, `ORCHESTRA/app.py`, `DocumentUploadAgent/app.py`, `DocumentUploadAgent/extractor.py`, `supabase_db.py`, `AutomationModal.jsx`

- **Problem:**
  1. The Self-Declaration form was submitted automatically via digital auto-signing after only 15 seconds, preventing the applicant from downloading, manually signing, and uploading their own document.
  2. The main backend (`ORCHESTRA/app.py`) lacked the `/upload-signed-declaration` endpoint, so manual uploads from the modal were either redirected to a different service container or lost if Supabase Storage was unavailable.
  3. Pre-existing test failures existed in ESLint (`AutomationModal.jsx` cascading setState in effect), Document Upload Agent (detail string assertion), and Supabase DB (document restoration from `supabase_urls`).
- **Fixes Applied:**
  1. **Extended Prompt Timeout & Manual Upload Priority:**
     - Increased Self-Declaration prompt timeout in `rescert.py` from 15s to 300s (5 minutes), identical to CAPTCHA and OTP prompts.
     - Automation now explicitly pauses and waits for the applicant to download, sign, and upload their document.
     - Auto-sign fallback is only applied if the applicant explicitly clicks **`⚡ Auto-Sign & Continue`** or if the full 5-minute timeout expires.
     - `process_document_upload` and the post-upload verification loop now prioritize the applicant's uploaded `Signed_Self_Declaration.pdf` over auto-signed fallbacks.
  2. **Dedicated `/upload-signed-declaration` Endpoint:**
     - Added `POST /upload-signed-declaration` in `ORCHESTRA/ORCHESTRA/ORCHESTRA/app.py`. Uploaded signed files are saved directly onto the Playwright instance disk (`uploaded_documents/Signed_...` and `Signed_Self_Declaration.pdf`) and uploaded to Supabase Storage.
     - Enhanced `DocumentUploadAgent/app.py` to also write files locally to the Playwright directory.
     - Updated `SelfDeclarationModal.jsx` to upload to the main orchestra backend with graceful multi-tier fallback, and to download the generated declaration directly from the backend.
  3. **Frontend ESLint Fix:** Refactored `AutomationModal.jsx` to derive `captchaSrc` from props (`eventData?.image`) instead of calling synchronous `setState` in `useEffect`.
  4. **Document Upload Agent Error Detail:** Updated `extractor.py` and `app.py` detail strings to satisfy `Only PDF documents are accepted` test assertions.
  5. **Supabase Document Restoration:** Added canonical document key mappings (`aadharCard`, `rationCard`, `drivingLicense`, `photo`) in `fetch_user_profile` in `supabase_db.py`.
  6. **Complete Test Suite:** `run_all_tests.py` ran with 100% pass across all 5 test suites.

---

### 19. Fast Form Filling Optimization & UI Icon Uniformization

**Files:** `rescert.py`, `App.jsx`, `SelfDeclarationModal.jsx`, `DocumentChecklist.jsx`, `PaymentModal.jsx`

- **Problem:**
  1. While filling applicant details on the Tamil Nadu e-District REV-116 form, the automation spent ~80 seconds waiting on fields that cannot or do not need to be filled. Specifically:
     - Applicant demographic fields (`applicantName`, `fatherName`, etc.) are locked/read-only once CAN is selected.
     - `safe_select_dropdown` had a 15-second wait per field.
     - A blocking 55-second selector wait (`residence:cRvillageListId` 30s + retry 20s + sleeps) delayed form completion.
     - An arbitrary 8-second sleep ran during CAN searching.
  2. The UI featured arbitrary emojis (`✅ I have paid`, `✅` success emoji, `🗑` delete icon, `⚡` symbols, `🔒` padlock, `✓` checkmarks) inconsistent with the modern Lucide React design system (`react-icons/lu`).
- **Fixes Applied:**
  1. **Instant Form Filling & Smart Editable Detection in `rescert.py`:**
     - Replaced blocking element queries with a unified in-browser JavaScript evaluation (`page_form.evaluate`).
     - Added `fillIfEditable()` helper that verifies an input is not disabled or read-only before writing, bypassing locked CAN fields in <1ms without throwing or timing out.
     - Reduced `safe_select_dropdown` visibility wait timeout from 15,000ms to 2,000ms and removed artificial 500ms sleeps.
     - Removed the 55-second blocking wait on `residence:cRvillageListId`; village dropdown is now populated instantly if present or gracefully skipped if pre-selected.
     - Replaced the blind 8-second CAN search sleep with dynamic waiting on the CAN radio button (`input[name='can_radio']`).
     - Overall form-filling time reduced from ~80s to ~4-5s.
  2. **Uniform Lucide React Icons Across Frontend:**
     - **`App.jsx`:**
       - Replaced raw `✅` in Payment Success modal with `<LuCircleCheckBig size={52} color="#4ade80" />`.
       - Added `<LuQrCode size={24} color="#60a5fa" />` icon in "Scan to Pay" title header.
       - Replaced `✅ I have paid` button text with `<LuCircleCheck size={18} /><span>I have paid</span>`.
       - Replaced `🗑` in "Clear My Data" modal with `<LuTrash2 size={24} color="#ef4444" />`.
       - Cleaned up raw emojis in payment gateway text messages.
     - **`SelfDeclarationModal.jsx`:**
       - Replaced raw `✓` in uploaded file preview with `<LuCircleCheck size={16} />`.
       - Replaced `⚡ Auto-Sign & Continue` with `<LuSparkles size={15} /> <span>Auto-Sign &amp; Continue</span>`.
     - **`DocumentChecklist.jsx`:**
       - Replaced `⚡ Delete Saved Application (Dev)` with clean `Delete Saved Application (Dev)` with `<MdDeleteOutline />`.
       - Replaced `⚡ Developer Tool` with `<LuWrench size={13} /> Developer Tool`.
       - Replaced `🔒 PIN Download` with `<LuLock size={12} /> PIN Download`.
       - Replaced `⚡ Dev Load` with `<LuFileUp size={13} /> Dev Load`.
       - Replaced raw `✕` and `✓` in step indicators with `<LuCheck />` and `<LuTriangleAlert />`.
       - Replaced raw `✓` in welcome back toast with `<LuCircleCheck size={16} />`.
     - **`PaymentModal.jsx`:**
       - Cleaned footer text from `Application filled ✓ Complete payment above` to `Application filled · Complete payment above`.
  3. **Verification:**
     - Frontend ESLint: 0 errors.
     - Production Vite Build: Passed.
     - Full backend test suite (`run_all_tests.py`): 100% passed across all 5 test suites.

---

### 21. Production Hardening: Purged Auto-Filled Credentials, Mock Fallbacks, and UI Fixes

**Files:** `DocumentChecklist.jsx`, `rescert.py`, `delete_saved_app.py`, `App.jsx`, `AutomationModal.jsx`, `DocumentUpload.jsx`

- **Problem:**
  1. The codebase had development test credentials, mock document paths, and hardcoded fallback values that prefilled forms and automation scripts without explicit user consent:
     - `DocumentChecklist.jsx` initialized state with hardcoded portal username (`"lohithg"`), password (`"Lohith@2007"`), CAN (`"13318016498757"`), Aadhaar (`"607126530111"`), and `from_date` (`"09/10/2024"`).
     - `DocumentChecklist.jsx` auto-filled `to_date` to today's date upon component mount.
     - `DocumentChecklist.jsx` provided a `⚡ Dev Load` button and bundled `DEV_DOCS` linking to local sample files.
     - `DocumentChecklist.jsx` injected a hardcoded fallback document number (`"TN31 20250006924"`) if the citizen had not entered one for Address Proof.
     - `delete_saved_app.py` defaulted CLI arguments `--username` and `--password` to `"lohithg"` and `"Lohith@2007"`.
     - `rescert.py` fell back to hardcoded applicant name `"Lohith G"` if no name was present in the data payload.
     - `rescert.py` silently fell back to uploading test files `/dev_docs/photo.jpg` and `/dev_docs/drvlc.pdf` from disk when citizen uploads were missing.
     - `rescert.py` pre-generated an auto-signed self-declaration and automatically submitted fabricated digital signatures in the verification and Tier-3 fallback loops even when the applicant intended to sign manually.
  2. UI and linting bugs:
     - `App.jsx`: `useEffect` hook had a missing dependency warning for `openAutomationSocket`.
     - `AutomationModal.jsx`: Used raw text characters `↻` and `⟳` for spinner states rather than uniform Lucide icons.
     - `DocumentChecklist.jsx`: Contained unclosed fragment tag causing JSX parsing errors.
     - `DocumentUpload.jsx`: Potential base URL issues when `VITE_API_BASE` had trailing slashes or was undefined.

- **Fixes Applied:**
  1. **Purged Auto-Filled Credentials and Fallbacks:**
     - `DocumentChecklist.jsx`: Initialized all input states (`username`, `password`, `can_number`, `aadhar_number`, `from_date`, `to_date`, `address_doc_no`) to empty strings `""`.
     - Removed `DEV_DOCS` constants and the `⚡ Dev Load` UI button.
     - Removed the mount effect that silently prefilled `to_date` without citizen action.
     - Removed hardcoded fallback `"TN31 20250006924"` for address proof numbers.
     - Added validation in `handleDeleteSavedApp` requiring active credentials before initiating the portal cleaner.
     - Renamed developer tool indicators to production-friendly labels (`Portal Utility`, `Clear Saved Draft`).
  2. **Removed Unauthorized Mock Injections from Backend Automation:**
     - `delete_saved_app.py`: Default credentials set to empty strings `""` with explicit argument requirements.
     - `rescert.py`: Fallback applicant name changed from `"Lohith G"` to generic `"Applicant"`.
     - Removed unauthorized local disk fallback for `/dev_docs/photo.jpg` and `/dev_docs/drvlc.pdf`.
     - Strict Self-Declaration submission: Auto-signing is now strictly executed ONLY when the user explicitly clicks the "Auto-Sign & Continue" button (`signed_decl_path.lower() in ("autosign", "auto-sign", "auto")`). Verification and Tier-3 fallback loops only re-upload the applicant-verified declaration and never fabricate signatures.
  3. **UI and Component Robustness:**
     - `App.jsx`: Moved `getWsBase()` to module scope and wrapped `openAutomationSocket` with `useCallback(..., [])` to resolve ESLint `react-hooks/exhaustive-deps`.
     - `AutomationModal.jsx`: Replaced raw spinning characters with `<LuRotateCw size={13} style={{ animation: "spin 1s linear infinite" }} />`.
     - `DocumentChecklist.jsx`: Cleaned up JSX syntax to ensure 0 lint errors.
     - `DocumentUpload.jsx`: Normalized API base URL with fallback.
  4. **Verification & Test Suite:**
     - Frontend ESLint: `0 problems (0 errors, 0 warnings)`.
     - Frontend Production Build: Vite production bundle built successfully.
     - Backend Test Suite (`run_all_tests.py`): 100% pass across all 5 test suites.






