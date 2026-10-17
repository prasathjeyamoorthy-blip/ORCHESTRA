# Frontend Updates — TNeGA Residence Certificate Assistant

## 1. Apply Now — Quick Start Automation Button

**Location:** Sidebar footer (above "Clear My Data")

**What it does:**
A direct "Apply Now" button with a lightning bolt icon has been added to the sidebar. Clicking it immediately opens the document upload and automation checklist without needing to type anything in the chat.

**Why it was added:**
Previously, users had to type something like "I want to apply for residence certificate" in the chat to trigger the document upload flow. Many users found this non-obvious. The sidebar button provides a direct, always-visible shortcut.

**Behavior:**
- Visible in both collapsed (icon only) and expanded (icon + label) sidebar states
- Clicking it navigates to Home and opens the document upload checklist immediately
- Works regardless of current chat state

---

## 2. Clear My Data

**Location:** Sidebar footer — 🗑 "Clear My Data" button (below Apply Now)

**What it does:**
Permanently deletes the current user's:
- Chat history (all sessions)
- Uploaded documents metadata
- Saved application payloads

The user's **account/profile identity is preserved** — only the data is erased. The user stays logged in after clearing.

**Confirmation modal:**
Clicking "Clear My Data" opens a full-screen confirmation modal with:
- A trash icon in a red circle
- Title: "Clear All My Data?"
- Description explaining the action is permanent
- Cancel button (grey)
- Yes, Delete button (red gradient)
- Loading spinner while deletion is in progress

**Error handling:**
- If server returns a non-2xx response, an alert is shown with the error message
- Local state is only cleared **after** server confirms successful deletion
- If the user is not logged in, the button alerts them to sign in first

**After successful clear:**
- All chat sessions removed from sidebar
- Current chat reset to welcome message
- User stays logged in (phone number preserved in session)
- No OTP re-verification required

---

## 3. Auto-fill "Residing To" Date

**Location:** Document checklist → Step 2: Residency → "Residing To (DD/MM/YYYY)" field

**What it does:**
The "Residing To" date field is automatically pre-filled with **today's date** whenever the checklist panel opens.

**Why this field:**
The "Residing To" field represents the end date of the applicant's current residence period being declared. For most applications, this is the current date (the date of application). Pre-filling it saves the user from having to pick today's date manually.

**Behavior:**
- Format: `DD/MM/YYYY` (e.g. `17/10/2026`)
- Populated immediately when the panel mounts
- Always uses the current date — never restores an old "Residing To" date from saved profile
- The "Residing From" field is left blank for the user to fill (varies per person)
- User can still change the date using the calendar picker if needed

---

## 4. PDF-Only Document Upload Enforcement

**Location:** Document checklist → Step 3: Documents

**What it does:**
All document slots (Aadhaar Card, Ration Card, Address Proof) now only accept **PDF files**. Image files (JPG, PNG) are rejected with an error message.

**Why:**
PDF documents from government portals (e.g. eAadhaar from UIDAI, digital ration card) contain embedded text that can be read directly — no AI vision model needed. This eliminates hallucinations that occur when the AI tries to "read" a photographed card.

**Behavior:**
- File picker only shows `.pdf` files for document slots
- If a non-PDF is selected, the user sees: *"Please upload a PDF file. Images are not accepted for documents — download the official PDF from the government portal"*
- Photo slot (Applicant Photograph) still accepts JPG and PNG

---

## 5. Document Slot Renamed

The "Driving license" upload slot has been renamed to **"Address Proof (Driving License / Aadhaar)"** to clarify that any official address proof document can be uploaded there, not just a driving license.
