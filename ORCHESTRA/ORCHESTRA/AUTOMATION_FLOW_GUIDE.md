# Complete Automation Flow - What Happens After Add & Submit

## Current Position: After Clicking Add & Submit Buttons

```
┌─────────────────────────────────────────────────────────────────┐
│  YOU ARE HERE: Form Submitted Successfully                      │
└─────────────────────────────────────────────────────────────────┘
```

## What Happens Next (Automatic Steps)

### Step 1: Dialog Handler Setup
```python
# Dialog Handler - Auto-accepts any popup alerts
def safe_dialog_handler(dialog):
    try: dialog.accept()
    except Exception: pass 
page_form.on("dialog", safe_dialog_handler)
```
**Purpose:** Automatically handles any confirmation dialogs that appear after submission

---

### Step 2: Click Submit Button
```python
self.log("Submitting Form...")
page_form.get_by_role("button", name="Submit").click()
page_form.wait_for_load_state("networkidle")
time.sleep(6)
```
**What happens:**
- Clicks the final Submit button
- Waits for page to fully load
- Portal processes your application
- **You should see:** Application submitted confirmation page

---

### Step 3: Download Self-Declaration Form
```python
self.log("Downloading Self Declaration Form...")
try:
    with page_form.expect_download(timeout=15000) as download_info:
        page_form.get_by_role("link", name="Download Self declaration form").click(force=True)
    download = download_info.value
    save_path = os.path.join(os.getcwd(), "Self_Declaration_Form_For_User.pdf")
    download.save_as(save_path)
    self.log(f"Form saved locally at: {save_path}")
except Exception as e:
    self.log("Download skipped or failed. Proceeding.")
```
**What happens:**
- Portal generates a Self-Declaration Form PDF
- Automation clicks the download link
- Saves PDF to: `Self_Declaration_Form_For_User.pdf` in current directory
- **If download fails:** Continues anyway (not critical)

**What you need to do:**
- Print this PDF
- Sign it manually
- Scan/photograph the signed document
- Keep it ready for upload

---

### Step 4: Wait for User Confirmation (PAUSE POINT)
```python
self.log("Waiting for user to confirm documents are ready for upload...")

self._ws_prompt({
    "type": "REQUEST_RESUME",
    "message": "The Self-Declaration Form has been downloaded. Please ensure your photo, signed declaration, and address proof are ready. Click Submit to continue with document upload."
})
```
**What happens:**
- ⏸️ **AUTOMATION PAUSES HERE**
- WebSocket sends message to your React UI
- Modal appears asking you to confirm documents are ready
- **You must click "Submit" in the UI to continue**

**Documents needed at this point:**
1. ✅ Photo (already uploaded earlier)
2. ✅ Signed Self-Declaration Form (just downloaded, needs your signature)
3. ✅ Address Proof (already uploaded earlier)

---

### Step 5: Document Upload Process
```python
def process_document_upload(doc_label, filepath, doc_no=None):
    # 1. Select document type from dropdown
    page_form.get_by_role("combobox").select_option(label=doc_label)
    
    # 2. If document number required, fill it
    if doc_no:
        doc_input = page_form.locator('[id="ss:dscnum"]')
        doc_input.fill(doc_no)
    
    # 3. Upload file
    page_form.locator("input[type='file']").last.set_input_files(filepath)
    
    # 4. Click Upload button
    page_form.get_by_text("Upload", exact=True).click(force=True)
```

**Three documents are uploaded in sequence:**

#### Upload 1: Photo
```python
process_document_upload("Photo", self.docs.get("photo_path"))
```
- Selects "Photo" from dropdown
- Uploads your photograph
- Clicks Upload button
- Waits 10 seconds

#### Upload 2: Self-Declaration Form
```python
process_document_upload("Self-Declaration of Applicant", self.docs.get("self_decl_path"))
```
- Selects "Self-Declaration of Applicant" from dropdown
- Uploads the signed declaration PDF
- Clicks Upload button
- Waits 10 seconds

#### Upload 3: Address Proof
```python
process_document_upload("Current Address Proof", self.docs.get("address_proof_path"), self.docs.get("address_doc_no"))
```
- Selects "Current Address Proof" from dropdown
- Fills document number (Aadhaar number)
- Uploads address proof document
- Clicks Upload button
- Waits 10 seconds

---

### Step 6: Navigate to Payment
```python
self.log("All Documents Uploaded! Navigating to Payment...")
try:
    page_form.get_by_role('button', name='Make Payment').click(force=True)
except:
    page_form.locator('input[value="Make Payment"]').first.click(force=True)
```
**What happens:**
- Clicks "Make Payment" button
- Portal redirects to payment gateway
- **You should see:** Payment page with amount and payment options

---

### Step 7: Automation Complete
```python
self.log("SUCCESS! Payment page reached. Backend job complete.")
time.sleep(5)
browser.close()
```
**What happens:**
- Automation logs success
- Waits 5 seconds
- Closes the browser
- **Your turn:** Complete the payment manually on the portal

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTOMATION COMPLETE FLOW                      │
└─────────────────────────────────────────────────────────────────┘

1. Login + CAPTCHA ✓
   ↓
2. Navigate to Residence Certificate ✓
   ↓
3. CAN Search + Aadhaar + DOB ✓
   ↓
4. OTP Verification ✓
   ↓
5. Form Filling (All Fields) ✓
   ↓
6. Click Add Button ✓
   ↓
7. Click Submit Button ✓
   ↓
8. Download Self-Declaration Form ✓
   ├─ Saved to: Self_Declaration_Form_For_User.pdf
   └─ ACTION REQUIRED: Print, Sign, Scan
   ↓
9. ⏸️  PAUSE: Wait for User Confirmation
   └─ Click "Submit" in UI when ready
   ↓
10. Upload Photo ✓
    ├─ Select "Photo" from dropdown
    ├─ Upload file
    └─ Click Upload
    ↓
11. Upload Self-Declaration ✓
    ├─ Select "Self-Declaration of Applicant"
    ├─ Upload signed PDF
    └─ Click Upload
    ↓
12. Upload Address Proof ✓
    ├─ Select "Current Address Proof"
    ├─ Fill document number
    ├─ Upload file
    └─ Click Upload
    ↓
13. Click "Make Payment" ✓
    ↓
14. 🎉 SUCCESS - Payment Page Reached
    ↓
15. Browser Closes
    ↓
16. 👤 MANUAL: Complete Payment on Portal
```

---

## What You Need to Do Manually

### During Automation:
1. **Enter CAPTCHA** when prompted (via WebSocket modal)
2. **Enter OTP** when prompted (via WebSocket modal)
3. **Confirm documents ready** before upload (via WebSocket modal)

### After Automation:
1. **Sign the Self-Declaration Form** (downloaded PDF)
2. **Complete Payment** on the portal (automation stops at payment page)
3. **Save Transaction ID** for certificate download later

---

## Files Generated by Automation

| File | Location | Purpose |
|------|----------|---------|
| `Self_Declaration_Form_For_User.pdf` | Current directory | Form to be signed and uploaded |
| `backend_captcha.png` | Playwright directory | CAPTCHA image for user input |
| `last_payload.json` | Playwright directory | Backup of submitted data |

---

## Error Handling

### If Download Fails:
```
[STATUS] Download skipped or failed. Proceeding.
```
- Automation continues
- You may need to download the form manually from portal

### If File Not Found:
```
[STATUS] WARNING: File not found at 'path'. Skipping document...
```
- That document upload is skipped
- Check file paths in payload

### If Upload Fails:
- Automation logs error but continues
- You may need to upload manually on portal

---

## Next Steps After Payment

Once you complete payment:
1. Portal generates **Transaction ID**
2. Application goes for approval
3. Once approved, use the **Certificate Downloader Agent** (`4thAgent/cert_agent.py`) to download your certificate:

```python
config = {
    "username": "your_username",
    "password": "your_password",
    "transaction_id": "TNCIT000000012997009"  # From payment receipt
}
bot = TNeGACertificateDownloader()
bot.execute(config)
```

---

## Summary

**Automated Steps:** 13 steps (Login → Payment Page)
**Manual Steps:** 3 steps (CAPTCHA, OTP, Payment)
**Pause Points:** 3 (CAPTCHA, OTP, Document Confirmation)
**Final Output:** Application submitted, ready for payment
**Success Indicator:** Browser reaches payment page and closes
