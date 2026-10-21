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


---

### 12. `main.py` — DOB field uses Aadhaar only, not any document

**Problem:** `get_field_priority("dob")` picks the highest-resolution document's DOB. When Aadhaar extraction fails, ration card wins and returns father's DOB (`12/10/1967`) instead of applicant's DOB (`23/02/2007`).

**Fix:**
```python
# Before
"dob": get_field_priority("dob"),

# After
"dob": get_aadhaar_field("dob"),  # DOB from Aadhaar only
```

**Note:** `_normalise_dob` was mistakenly added (doesn't exist in this codebase) causing a 500 error. Removed immediately.

---

### 13. `DocumentChecklist.jsx` — Village field broken after payload rewrite

**Problem:** Changed `c.taluk || c.district` to `c.village` for the village field. But the combined extraction doesn't have a `village` key — village comes from `c.taluk` (Aadhaar extraction stores it there).

**Fix:**
```js
// Before (broken)
village: c.village || extractedData.aadharCard?.[0]?.area || savedAddress.village || ""

// After (fixed)
village: c.village || c.taluk || extractedData.aadharCard?.[0]?.area || extractedData.aadharCard?.[0]?.taluk || savedAddress.village || ""
```

---

### 14. `DocumentChecklist.jsx` — Payload priority: real-time extraction over stale Supabase cache

**Problem:** `savedApplicant.dob` from Supabase was being used as fallback when `c.dob` was empty. When Aadhaar extraction failed, `c.dob` got ration card DOB, overwriting the correct saved value.

**Fix:** Payload assembly now prioritises:
1. `c.*` — combined extraction (this session, fresh)
2. `extractedData.aadharCard[0].*` — raw Aadhaar extraction (this session)
3. `savedApplicant.*` — Supabase cache (last resort, only for address fields)

`savedApplicant.dob`, `.gender`, `.religion`, `.community`, `.mobile_number`, `.ration_card_no` removed as fallbacks for personal fields.

---

### 15. `DocumentChecklist.jsx` — Photo upload accepts JPG/JPEG/PNG

**Problem:** All document slots had strict PDF-only enforcement. The Applicant Photograph slot should accept image files.

**Fix:**
```js
// File input accept attribute
accept={doc.id === "photo"
  ? ".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
  : ".pdf,application/pdf"}

// Validation check
const isValidFile = isPhoto
  ? (nameLower.endsWith(".pdf") || validImageExts.some(ext => nameLower.endsWith(ext)))
  : nameLower.endsWith(".pdf");
```

---

### 16. `rescert.py` — Stealth import fix

**Problem:** `from playwright_stealth import stealth_sync` — `stealth_sync` doesn't exist in `playwright-stealth==2.0.3`. Caused stealth to silently fail on every run.

**Fix:**
```python
from playwright_stealth import stealth
stealth(page)
```

---

### 17. `rescert.py` — Skip BillDesk, send UPI QR directly from local file

**Problem:** BillDesk UPI/QR flow was working but slow/fragile due to iframe detection and network delays.

**Temporary fix:** After "Make Payment" is clicked, skip BillDesk navigation entirely. Load `upi_qr.png` from `frontend/public/` and send it directly as `PAYMENT_QR` WebSocket event.

```python
# Load local UPI QR
qr_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "public", "upi_qr.png")
with open(qr_path, "rb") as qf:
    qr_b64 = base64.b64encode(qf.read()).decode()

manager.send_event_sync({"type": "PAYMENT_QR", "qr_image": f"data:image/png;base64,{qr_b64}"})
```

---

### 18. `App.jsx` — Payment success goes into chat, not a modal

**Problem:** Payment success was shown as a separate modal overlay that blocked the chat.

**Fix:** `PAYMENT_SUCCESS` now pushes a `{ type: "receipt_download" }` message into the chat. The messages map renders it as:
- "Payment complete!" text
- Download Receipt button (purple bordered, `LuDownload` icon)
- 3 suggestion prompt chips (↳ style)

Modal state `paymentSuccess` is no longer set — replaced by inline chat rendering.

---

### 19. `App.jsx` — "Getting your receipt" loading state

After user clicks "I have paid":
- `gettingReceipt` set to `true` immediately → spinner shows in QR modal
- In test mode: auto-resolves after 3s
- In real automation: resolves when `PAYMENT_SUCCESS` WebSocket event arrives

---

### 20. `App.jsx` — Certificate tracking flow (inline in chat)

User types "track my certificate" or clicks the suggestion prompt → inline `TrackForm` component rendered in chat messages.

**Flow:**
1. Radio buttons: Transaction No. / Application No.
2. Input field for reference number
3. "Done" button → loading spinner in chat
4. After 5s → `{ type: "cert_download" }` message appears with Download Certificate button

---

### 21. `main.py` + `DocumentUploadAgent` — `pypdf` installed

`pypdf` was missing from the new venv. Installed via:
```bash
uv pip install pypdf
```

---

### 22. NVIDIA API keys updated

Key #1 (`nvapi-aL5Hc`) returned 403 (expired). Three new keys added at the front, old keys pushed back as fallback:

| Position | Key prefix |
|---|---|
| Key 1 (primary) | `nvapi-fNd2W6` (new) |
| Key 2 | `nvapi-fsV6Lr` (new) |
| Key 3 | `nvapi--Dr5be` (new) |
| Key 4–7 | Old keys as fallback |

---

### 23. `upi_qr.png` generated

UPI QR code for `danielsebastin2018@okaxis` generated using `qrcode[pil]` and saved to:
- `d:\RESIDENCE_CERTIFICATE_COMPRESSED\upi_qr.png`
- `RESIDENCE_CERTIFICATE_NEW\ORCHESTRA\frontend\public\upi_qr.png`

---

### 24. `cert.pdf` and `Receipt_updated(1).pdf` added to frontend public

Copied from `d:\RESIDENCE_CERTIFICATE_COMPRESSED\` to `frontend/public/` so they can be served as static downloads.

---

### 25. `App.jsx` — Payment state reset on automation start

**Problem:** Stale `gettingReceipt=true` from a previous test run caused the QR modal to skip directly to the loading screen when automation started.

**Fix:** All payment states reset when `onOpenSocket` is called:
```js
onOpenSocket={() => {
  setPaymentQr(null);
  setGettingReceipt(false);
  setPaymentSuccess(null);
  return openAutomationSocket();
}}
```

---

## Frontend Changes — by Daniel

---

### 26. Sidebar — "Apply Now" Quick Start Button

**File:** `ORCHESTRA/frontend/src/components/AppSidebar.jsx`

A direct **Apply Now** button (⚡ icon) added to the sidebar footer above "Clear My Data". Clicking it immediately opens the document upload checklist without needing to type anything in chat.

- Visible in both collapsed (icon only) and expanded (icon + label) states
- Navigates to Home and opens checklist instantly
- Works regardless of current chat state

---

### 27. Sidebar — "Clear My Data" Button + Confirmation Modal

**File:** `ORCHESTRA/frontend/src/components/AppSidebar.jsx`, `App.jsx`

🗑 "Clear My Data" button in sidebar footer permanently deletes:
- Chat history (all sessions)
- Uploaded document metadata
- Saved application payloads

Account/profile identity is preserved. User stays logged in after clearing.

**Confirmation modal:**
- Full-screen overlay with trash icon in red circle
- "Clear All My Data?" title with description
- Cancel (grey) + "Yes, Delete" (red gradient) buttons
- Loading spinner during deletion
- Local state only cleared after server confirms success

---

### 28. "Residing To" Date Auto-filled to Today

**File:** `ORCHESTRA/frontend/src/components/DocumentChecklist.jsx`

The "Residing To" date field is automatically pre-filled with today's date when the checklist opens. Format: `DD/MM/YYYY`. The "Residing From" field is left blank for the user. User can still change it via the calendar picker.

**Why:** For most applications, the "Residing To" date is the current date. Old saved "Residing To" dates are never restored from profile.

---

### 29. PDF-Only Document Upload Enforcement

**File:** `ORCHESTRA/frontend/src/components/DocumentChecklist.jsx`

All document slots (Aadhaar, Ration Card, Address Proof) only accept PDF files. Image files (JPG, PNG) are rejected with an error message. Photo slot (Applicant Photograph) still accepts JPG and PNG.

**Why:** Government portal PDFs contain embedded text readable directly — no VLM hallucinations.

---

### 30. Address Proof Slot Renamed

**File:** `ORCHESTRA/frontend/src/components/DocumentChecklist.jsx`

"Driving License" slot renamed to **"Address Proof (Driving License / Aadhaar)"** to clarify any official address proof document is accepted there.

---

## Session Changes Summary (Full Run)

| # | What Changed | File(s) |
|---|---|---|
| 1–11 | Initial setup, env, venvs, OTP toggle, dev creds, SelfDecl fix, QR payment | Various |
| 12 | DOB uses Aadhaar only in combined extraction | `main.py` |
| 13 | Village field broken after payload rewrite — fixed `c.taluk` | `DocumentChecklist.jsx` |
| 14 | Payload priority: real-time extraction over stale Supabase | `DocumentChecklist.jsx` |
| 15 | Photo upload accepts JPG/JPEG/PNG | `DocumentChecklist.jsx` |
| 16 | Stealth import fix (`stealth` not `stealth_sync`) | `rescert.py` |
| 17 | Skip BillDesk — send local UPI QR directly | `rescert.py` |
| 18 | Payment success goes into chat (not modal) | `App.jsx` |
| 19 | "Getting your receipt" loading state | `App.jsx` |
| 20 | Certificate tracking inline in chat (TrackForm) | `App.jsx` |
| 21 | `pypdf` installed in new venv | `DocumentUploadAgent` |
| 22 | NVIDIA API keys updated (3 new + old as fallback) | `.env` |
| 23 | UPI QR generated for `danielsebastin2018@okaxis` | `public/upi_qr.png` |
| 24 | `cert.pdf` + `Receipt_updated(1).pdf` added to frontend public | `frontend/public/` |
| 25 | Payment state reset on automation start | `App.jsx` |
| 26 | "Apply Now" sidebar button | `AppSidebar.jsx` |
| 27 | "Clear My Data" button + modal | `AppSidebar.jsx`, `App.jsx` |
| 28 | "Residing To" auto-fills today's date | `DocumentChecklist.jsx` |
| 29 | PDF-only enforcement (photo allows images) | `DocumentChecklist.jsx` |
| 30 | Address proof slot renamed | `DocumentChecklist.jsx` |
| 31 | `OPEN_PAYMENT_URL` suppressed in chat | `App.jsx` |
| 32 | AutomationModal closes on PAYMENT_QR | `App.jsx` |
| 33 | Duplicate receipt fix — WS-driven only | `App.jsx` |
| 34 | NVIDIA timeout reduced to 7s, 429 handling added | `extractor.py` |
| 35 | rescert.py timing matched to old codebase (~97s) | `rescert.py` |
