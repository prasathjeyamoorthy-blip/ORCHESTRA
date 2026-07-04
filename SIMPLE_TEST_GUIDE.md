# Simple Testing Guide - Corrected Flow

## Overview

No Tkinter, no complexity. Just:
1. Frontend → generates INPUT.json
2. You review INPUT.json  
3. You run `python main.py`
4. Browser fills form automatically

---

## Setup (One Time)

### Start All Services

```bash
# Or use: start_all_services.bat

# Terminal 1
cd pan_verification && .venv\Scripts\activate && python app.py

# Terminal 2  
cd pan-rag && .venv\Scripts\activate && uvicorn api.main:app --reload --port 8000

# Terminal 3
cd auth-app\backend && npm run dev

# Terminal 4
cd frontend && npm run dev
```

---

## Testing Flow

### 1. Complete Application in Frontend

1. Go to http://localhost:5173
2. Login
3. Chat: "Apply for PAN"
4. Upload documents (3-4 files)
5. Answer questions
6. Confirm

### 2. Get Token & Session from Browser

Press F12, then in console:

```javascript
// Copy these values
console.log('Token:', localStorage.getItem('token'));
console.log('Session:', localStorage.getItem('session_id'));
```

### 3. Call Finalize Endpoint

**Option A: Use test script**
```bash
TEST_FINALIZE.bat
# Follow prompts
```

**Option B: Manual curl**
```bash
curl -X POST http://localhost:4000/api/finalize-application ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer YOUR_TOKEN_HERE" ^
  -d "{\"session_id\":\"YOUR_SESSION_ID\",\"trigger_automation\":false}"
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "✅ Application data prepared successfully!\n\n📄 Next Steps:\n1. Review: automation_agent/INPUT.json\n2. Run: cd automation_agent && python main.py",
  "input_file": "d:/PANCARD/automation_agent/INPUT.json"
}
```

### 4. Review INPUT.json

```bash
# View in terminal
type automation_agent\INPUT.json

# Or open in VS Code
code automation_agent\INPUT.json
```

**Check these:**

✅ **Name split correctly?**
- Input: "Anand R Ajaanand"
- Expected: `"first_name": "Ajaanand", "middle_name": "R", "last_name": "Anand"`

✅ **All 30 fields present?**
```bash
python -c "import json; print('Fields:', len(json.load(open('automation_agent/INPUT.json'))))"
```
Should print: `Fields: 30`

✅ **Files exist?**
```bash
dir automation_agent\docs\
```
Should show: `jaadhar.pdf`, `jphoto.jpeg`, `jsign.jpeg`, `jbirthcert.pdf`

✅ **Critical fields filled?**
- first_name OR last_name
- email
- aadhaar_first_8 (8 digits)
- aadhaar_last_4 (4 digits)
- dob (DD/MM/YYYY)

**If anything is wrong, edit INPUT.json manually!**

### 5. Run Automation

```bash
cd automation_agent
.venv\Scripts\activate
python main.py
```

**What you'll see:**
```
================================================================================
PAN CARD APPLICATION AUTOMATION
================================================================================

[*] Applicant: Ajaanand R Anand
[*] Email: test@example.com

=== Step 1: Contact Form ===
[Step1] Page loaded.
[Step1] Starting reCAPTCHA solve.
[CAPTCHA] Solved!

=== Step 2: Token ===
Token: 1234567890

[... more steps ...]

[✓] Automation completed successfully!
================================================================================
```

**Browser will:**
- Open Chrome (visible window)
- Navigate to NSDL
- Fill all form fields
- Upload documents  
- Solve reCAPTCHA (may need your help)
- Submit application
- Capture payment URL

### 6. Get Payment Link

```bash
type automation_agent\payment_link.json
```

**Contains:**
```json
{
  "payment_url": "https://onlineservices.tin.egov-nsdl.com/...",
  "screenshot": "payment_page.png",
  "applicant_name": "Ajaanand R Anand"
}
```

Open this URL in browser to complete payment.

---

## Name Splitting Quick Reference

| Input | first_name | middle_name | last_name |
|-------|------------|-------------|-----------|
| Akash | `""` | `""` | `Akash` |
| Akash Raja | `Raja` | `""` | `Akash` |
| Anand R Ajaanand | `Ajaanand` | `R` | `Anand` |
| John Michael Doe | `John` | `Michael` | `Doe` |

**Rule:** South Indian with initial → last name first, then initial, then first name

---

## Troubleshooting

### INPUT.json not created
- Check pan-rag terminal for errors
- Verify finalize endpoint was called successfully
- Check response status was 200

### Name split wrong
- Edit INPUT.json manually
- Correct first_name, middle_name, last_name
- Save and run `python main.py`

### Files not in docs/
- Check `pan-rag/storage/uploads/{session_id}/` has files
- Re-run finalize endpoint
- Check file permissions

### Browser doesn't open
```bash
cd automation_agent
playwright install chromium
```

### reCAPTCHA fails
- Manually click checkbox when browser pauses
- Wait for audio solve to complete

---

## Files You'll Have After Testing

```
automation_agent/
  ├── INPUT.json           ← Review this before running automation!
  ├── data.json            ← Copy of INPUT.json
  ├── docs/
  │   ├── jaadhar.pdf
  │   ├── jphoto.jpeg
  │   ├── jsign.jpeg
  │   └── jbirthcert.pdf
  ├── payment_link.json    ← Generated after automation
  └── payment_page.png     ← Screenshot
```

---

## Quick Commands Cheat Sheet

```bash
# View INPUT.json
type automation_agent\INPUT.json | python -m json.tool

# Count fields (should be 30)
python -c "import json; print(len(json.load(open('automation_agent/INPUT.json'))))"

# Check name splitting
python -c "import json; d=json.load(open('automation_agent/INPUT.json')); print(f\"Name: {d['first_name']} {d['middle_name']} {d['last_name']}\")"

# Verify files exist
dir automation_agent\docs\

# Run automation
cd automation_agent && python main.py

# View payment link
type automation_agent\payment_link.json
```

---

## Success Checklist

Before running automation:
- [ ] INPUT.json exists
- [ ] 30 fields present
- [ ] Name split correctly
- [ ] Email filled
- [ ] Aadhaar digits present
- [ ] 4 files in docs/ folder

After automation:
- [ ] Browser ran visibly
- [ ] Form filled automatically
- [ ] Application submitted
- [ ] payment_link.json created
- [ ] Payment URL valid

---

**That's it!** Simple, direct, no complexity. 🚀

1. Frontend generates INPUT.json
2. You review it
3. You run automation
4. Done!
