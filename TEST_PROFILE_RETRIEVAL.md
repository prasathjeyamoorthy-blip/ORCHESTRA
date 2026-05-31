# Test Profile Retrieval - All Details

## Issue Fixed
The profile was only showing 3 fields (name, email, income) instead of ALL collected details including:
- Mother's name
- Submission mode
- Delivery mode
- Aadhaar photo preference
- Source of income
- Address for communication
- Residential status
- Representative Assessee

## Changes Made

### 1. Updated `loadProfile()` in `auth-app/backend/routes/chat.js`
**Before:** Only loaded `facts` JSONB column (old structure)
**After:** Loads all individual columns + extracts `pan_preferences` JSONB

```javascript
// Now loads:
- full_name
- mother_name
- email
- phone
- annual_income → mapped to profile.income
- date_of_birth → mapped to profile.dob
- pan_preferences.submission_mode
- pan_preferences.delivery_mode
- pan_preferences.aadhaar_photo
- pan_preferences.source_of_income
- pan_preferences.address_for_comm
- pan_preferences.residential_status
- pan_preferences.rep_assessee
- pan_preferences.applicant_type
```

### 2. Updated `saveProfile()` in `auth-app/backend/routes/chat.js`
**Before:** Saved everything to `facts` JSONB
**After:** Maps fields to individual columns + builds `pan_preferences` JSONB

```javascript
// Maps:
facts.full_name → full_name column
facts.mother_name → mother_name column
facts.email → email column
facts.income → annual_income column
facts.submission_mode → pan_preferences.submission_mode
facts.delivery_mode → pan_preferences.delivery_mode
// ... etc
```

### 3. Updated `buildUserContext()` in `auth-app/backend/routes/chat.js`
**Before:** Only included 7 fields (gender, dob, email, pan_number, aadhaar, income, address)
**After:** Includes ALL 16+ fields

```javascript
// Now includes in context sent to RAG:
- Full name
- Mother's name
- Email
- Phone
- Annual income
- Date of birth
- Submission mode
- PAN delivery mode
- Aadhaar photo preference
- Source of income
- Address for communication
- Residential status
- Representative Assessee
- Applicant type
+ Legacy fields for backward compatibility
```

---

## Testing Steps

### 1. Restart Backend Server
```bash
cd auth-app/backend
# Stop current process (Ctrl+C)
npm start
```

### 2. Test Profile Retrieval
1. Log in with existing account that has completed a PAN application
2. Open browser console (F12)
3. Type: "what are the details i gave you so far"
4. **Expected Response:**
   ```
   Here's what I have on file for you:
   
   - Name: J Devaprasath
   - Mother's name: [saved name]
   - Email: prasath@gmail.com
   - Annual income: ₹300,000
   - Submission mode: [saved choice]
   - PAN delivery: [saved choice]
   - Aadhaar photo on PAN: [Yes/No]
   - Source of income: [saved choice]
   - Address for communication: [saved choice]
   - Residential status: [saved choice]
   - Representative Assessee: [Yes/No]
   ```

### 3. Verify Database
```sql
-- Check what's actually stored
SELECT 
    full_name,
    mother_name,
    email,
    annual_income,
    pan_preferences
FROM user_profiles
WHERE email = 'prasath@gmail.com';
```

**Expected:**
- All columns populated
- `pan_preferences` JSONB contains all PAN choices

### 4. Test New Session Prefill
1. Start new chat session
2. Say: "I want to apply for PAN"
3. **Expected:** System should prefill ALL details, not just name/email/income
4. Should skip directly to confirmation with all fields filled

---

## Verification Checklist

✅ **Profile Load:**
- [ ] All personal details loaded (name, mother's name, email, income)
- [ ] All PAN preferences loaded (submission mode, delivery mode, etc.)
- [ ] No fields missing from profile object

✅ **Profile Save:**
- [ ] Personal details saved to individual columns
- [ ] PAN preferences saved to `pan_preferences` JSONB
- [ ] Database shows all fields populated

✅ **Context Building:**
- [ ] All profile fields included in RAG context
- [ ] Bot can answer "what details do I have" with complete list
- [ ] Bot doesn't re-ask for saved information

✅ **Prefill:**
- [ ] New flow starts with all saved details
- [ ] Confirmation shows all fields pre-filled
- [ ] User can modify any field if needed

---

## Expected Behavior

### Query: "what are the details i gave you so far"

**Before Fix:**
```
Here's what I have on file for you:

• Name: J Devaprasath
• Email: prasath@gmail.com
• Annual income: ₹300,000
```

**After Fix:**
```
Here's what I have on file for you:

• Full name: J Devaprasath
• Mother's name: [saved name]
• Email: prasath@gmail.com
• Annual income: ₹300,000
• Submission mode: Aadhaar-based Online (eKYC)
• PAN delivery: Physical copy to home + soft copy on email
• Aadhaar photo on PAN: Yes
• Source of income: Salary
• Address for communication: Residence
• Residential status: Resident
• Representative Assessee: No
```

---

## Troubleshooting

### Still showing only 3 fields
**Check:**
1. Backend server restarted? Old code may be cached
2. Profile exists in database? Run verification query
3. `pan_preferences` column populated? Check JSONB content
4. Redis cache cleared? May be serving old cached profile

**Solution:**
```bash
# Clear Redis cache for user
# In Redis CLI or Upstash console:
DEL profile:USER_ID_HERE

# Or restart backend to clear in-memory cache
```

### Profile not saving all fields
**Check:**
1. Flow confirmation completed? Profile saves on confirmation
2. `flow_data` in response? Check network tab for confirmation response
3. Backend logs? Look for "[profile] Supabase write error"

**Debug:**
```javascript
// Add to saveProfile() function:
console.log('[profile] Saving:', profileData);
```

### Prefill not working
**Check:**
1. Profile loaded? Check logs for "[user_profile] Prefilled flow state"
2. `user_id` passed to RAG? Check network request payload
3. Flow state updated? Check flow manager state file

---

## Database Schema Reference

```sql
-- user_profiles table structure
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY,
    user_id UUID UNIQUE,
    
    -- Individual columns for personal details
    full_name TEXT,
    mother_name TEXT,
    email TEXT,
    phone TEXT,
    annual_income TEXT,
    date_of_birth DATE,
    
    -- JSONB for PAN preferences
    pan_preferences JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

-- pan_preferences JSONB structure
{
    "submission_mode": "Aadhaar-based Online (eKYC)",
    "delivery_mode": "physical_and_soft",
    "aadhaar_photo": true,
    "source_of_income": "Salary",
    "address_for_comm": "Residence",
    "residential_status": "Resident",
    "rep_assessee": false,
    "applicant_type": "indian_citizen"
}
```

---

## Success Criteria

✅ Profile retrieval shows ALL 11+ fields
✅ Database stores all fields correctly
✅ Context sent to RAG includes all fields
✅ Bot can answer detailed questions about saved preferences
✅ New sessions prefill all saved data
✅ No re-asking for any saved information

---

**Status:** ✅ Fixed - Ready for Testing
**Files Modified:** `auth-app/backend/routes/chat.js`
**Restart Required:** Backend server only
