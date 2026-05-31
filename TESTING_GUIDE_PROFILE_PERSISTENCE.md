# Testing Guide: Profile Persistence Across Chat Sessions

## What Was Fixed
The `user_id` parameter was missing in 4 out of 5 code paths in `chain.py`, preventing the progressive auto-save feature from working. This has been fixed.

## Quick Test Scenario

### Test 1: Basic Profile Persistence

**Step 1 - First Chat Session:**
1. Open the application and log in
2. Start a new chat
3. Say: "I want to apply for new PAN"
4. Answer the optional questions:
   - Submission mode: Choose "Aadhaar-based Online (eKYC)"
   - Delivery mode: Choose "Physical copy to home + soft copy on email"
   - Aadhaar photo: Choose "Yes"
   - Source of income: Choose "Salary"
   - Address: Choose "Residence"
   - Residential status: Choose "Resident"
   - Representative Assessee: Choose "No"

**Expected:** After each answer, check server logs for:
```
[DEBUG] Auto-saved preferences to profile for user <user_id>
```

**Step 2 - Provide Personal Details:**
5. When asked for details, provide:
   - "My name is John Doe, mother name is Jane Doe, email john@example.com, salary 5 lakh"

**Expected:** Check server logs for:
```
[DEBUG] Auto-saved details to profile for user <user_id>
```

**Step 3 - Open New Chat Session:**
6. Delete the current chat or open a new chat
7. Say: "I want to apply for new PAN"

**Expected:** Agent should respond with:
```
Welcome back! I see you've applied for PAN before. 🎉

**Your previous choices:**

📝 **Submission mode:** Aadhaar-based Online (eKYC)
📦 **Delivery mode:** Physical copy to home + soft copy on email
📸 **Aadhaar photo on PAN:** Yes
💰 **Source of income:** Salary
📍 **Address for communication:** Residence
🏠 **Residential status:** Resident
👤 **Representative Assessee:** No

**Would you like to use the same options for this application?**

Reply **Yes** to use these options, or **No** to choose different options.
```

### Test 2: Partial Completion Persistence

**Step 1 - Start Application:**
1. Open new chat
2. Say: "I want to apply for new PAN"
3. Answer only 3 questions:
   - Submission mode: "Physical"
   - Delivery mode: "Soft only"
   - Aadhaar photo: "No"

**Step 2 - Abandon Flow:**
4. Say: "cancel" or close the chat

**Step 3 - Resume in New Chat:**
5. Open new chat
6. Say: "I want to apply for new PAN"

**Expected:** Agent should show the 3 saved preferences and ask if you want to use them.

### Test 3: Profile Display

**Step 1 - After Providing Details:**
1. Complete at least some optional questions and personal details
2. Say: "show me what you know about me"

**Expected:** Agent displays all collected information:
```
Here's what I know about you so far: 📋

**Personal Details:**
**Full name:** John Doe
**Mother's name:** Jane Doe
**Email:** john@example.com
**Annual income:** ₹5,00,000

**PAN Application Preferences:**
**Submission mode:** Aadhaar-based Online (eKYC)
**PAN delivery:** Physical + e-PAN
**Aadhaar photo on PAN:** Yes
**Source of income:** Salary
**Address for communication:** Residence
**Residential status:** Resident
**Representative Assessee:** No

---
This information is saved securely and will be used to help you with PAN services.

Would you like to continue with your application or start a new one?
```

## Server Log Monitoring

### What to Look For

**Successful Auto-Save:**
```
[DEBUG] Auto-saved preferences to profile for user <uuid>
[DEBUG] Auto-saved details to profile for user <uuid>
[user_profile] Saved profile for user <uuid>
```

**Profile Loading:**
```
[user_profile] Prefilled flow state for user <uuid>
```

**Missing user_id (Should NOT appear anymore):**
```
[ERROR] Failed to auto-save preferences: <error>
```

## Common Issues and Solutions

### Issue 1: "user_id is None"
**Symptom:** Logs show `user_id` is None or missing
**Solution:** Check that user is logged in and JWT token is valid

### Issue 2: "Profile not persisting"
**Symptom:** New chat doesn't show saved preferences
**Solution:** 
1. Check Supabase connection (SUPABASE_URL and SUPABASE_SERVICE_KEY in .env)
2. Verify user_profiles table exists in Supabase
3. Check server logs for auto-save confirmation messages

### Issue 3: "Auto-save not triggering"
**Symptom:** No "[DEBUG] Auto-saved" messages in logs
**Solution:**
1. Verify the fix was applied correctly (all 5 handle_message calls have user_id)
2. Restart the server
3. Check that user is authenticated (not anonymous)

## Verification Commands

### Check if fix is applied:
```bash
cd pan-rag
grep -n "handle_message(question, session_id, language" generation/chain.py
```

**Expected:** All 5 lines should include `user_id=user_id`

### Check Supabase connection:
```bash
cd pan-rag
python3 -c "
from agent.user_profile import supabase
print('Supabase connected:', supabase is not None)
"
```

### Check user profile in database:
```sql
-- Run in Supabase SQL editor
SELECT * FROM user_profiles WHERE user_id = '<your-user-id>';
```

## Success Criteria

✅ Auto-save logs appear after each optional question answer
✅ Auto-save logs appear after providing personal details
✅ New chat shows "Welcome back" message with saved preferences
✅ User can choose to reuse or change saved preferences
✅ Profile display shows all collected information
✅ Data persists even if user abandons flow before confirmation

## Rollback Plan

If issues occur, revert the changes in `pan-rag/generation/chain.py`:

```bash
git diff pan-rag/generation/chain.py
git checkout pan-rag/generation/chain.py
```

Then restart the server.
