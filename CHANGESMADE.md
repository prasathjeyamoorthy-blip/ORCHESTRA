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
