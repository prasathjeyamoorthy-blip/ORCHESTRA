# User Profile Integration - Complete ✅

## Summary
Successfully integrated user profile persistence with the PAN application flow. User details collected during the guided flow are now saved to Supabase and automatically prefilled in future sessions for a personalized experience.

---

## Changes Made

### 1. Created User Profile Module (`pan-rag/agent/user_profile.py`)
**Purpose:** Manage user profile data in Supabase

**Functions:**
- `get_user_profile(user_id)` - Retrieve user profile from database
- `save_user_profile(user_id, profile_data)` - Save/update user profile
- `save_flow_to_profile(user_id, flow_state)` - Extract and save flow data to profile
- `prefill_flow_from_profile(user_id, flow_state)` - Load saved data into new flow
- `extract_pan_preferences(flow_state)` - Extract PAN preferences as JSONB

**Data Stored:**
- Personal details: full_name, mother_name, email, phone, annual_income
- PAN preferences: submission_mode, delivery_mode, aadhaar_photo, source_of_income, address_for_comm, residential_status, rep_assessee, applicant_type

---

### 2. Updated Receptionist Flow (`pan-rag/agent/receptionist.py`)

**Added:**
- Import of user_profile functions
- `user_id` parameter to `handle_message()` function
- Profile prefill logic at flow start (loads saved data from previous sessions)
- Profile save logic after user confirms details
- `flow_data` in confirmation response for backend persistence

**Key Changes:**
```python
# At flow start - prefill from profile
if user_id and not flow.has_active_flow() and not flow.state.get("_profile_loaded"):
    flow.state = prefill_flow_from_profile(user_id, flow.state)
    flow.state["_profile_loaded"] = True
    flow.save()

# After confirmation - save to profile
if _yes.match(inp):
    # ... existing code ...
    if user_id:
        save_flow_to_profile(user_id, flow.state)
    # ... return with flow_data ...
```

---

### 3. Updated Chain (`pan-rag/generation/chain.py`)

**Changed:**
- All `handle_message()` calls now pass `user_id` parameter
- Ensures user_id flows through from API → Chain → Receptionist

**Example:**
```python
agent_response = handle_message(
    question, session_id, language, 
    user_context=user_context, 
    account_email=account_email, 
    user_id=user_id  # ← Added
)
```

---

### 4. Created Supabase Migration (`supabase/migrations/20240104000000_add_user_profiles.sql`)

**Database Schema:**
```sql
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT,
    mother_name TEXT,
    email TEXT,
    phone TEXT,
    annual_income TEXT,
    date_of_birth DATE,
    pan_preferences JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);
```

**Security:**
- Row Level Security (RLS) enabled
- Users can only access their own profile
- Policies for SELECT, INSERT, UPDATE, DELETE
- Auto-update trigger for `updated_at` timestamp

---

## How It Works

### First Session (New User)
1. User starts PAN application flow
2. System checks for existing profile → none found
3. User provides details through guided flow
4. User confirms details at confirmation step
5. **Details saved to `user_profiles` table**
6. Flow continues to document upload

### Subsequent Sessions (Returning User)
1. User starts new PAN application
2. System loads profile from database
3. **Flow state prefilled with saved data**
4. User sees their previous details already filled
5. User can modify if needed or proceed directly
6. Any changes are saved back to profile

### Personalization Benefits
- **No re-asking:** System remembers name, mother's name, email, income
- **Faster applications:** Returning users skip data entry
- **Consistency:** Same details used across multiple applications
- **User control:** Can update details during any flow

---

## Testing Checklist

### ✅ Prerequisites
- [ ] Supabase migration applied: `supabase db push` or run SQL manually
- [ ] Environment variables set:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_KEY`
- [ ] RAG server restarted: `cd pan-rag && ./restart.sh`
- [ ] Backend server restarted

### ✅ Test Scenarios

#### Test 1: First-Time User Flow
1. Create new account and log in
2. Start PAN application: "I want to apply for a new PAN card"
3. Complete the guided flow with all details
4. Confirm details at confirmation step
5. **Expected:** Details saved to database
6. **Verify:** Check `user_profiles` table in Supabase

#### Test 2: Returning User Prefill
1. Log in with account from Test 1
2. Start new chat session
3. Start PAN application: "I want to apply for PAN"
4. **Expected:** System shows previously entered details
5. **Expected:** No re-asking for name, mother's name, email, income
6. **Expected:** User can proceed directly to confirmation

#### Test 3: Profile Update
1. Log in with existing account
2. Start PAN application
3. At confirmation step, click "Change something"
4. Update a field (e.g., change email or income)
5. Confirm updated details
6. **Expected:** Updated details saved to profile
7. **Verify:** Start new session, check if updated data is prefilled

#### Test 4: Multiple Applications
1. Complete one PAN application (new card)
2. Start another application (e.g., correction)
3. **Expected:** Personal details prefilled from first application
4. **Expected:** Only PAN-specific choices asked again
5. **Expected:** Consistent user experience

#### Test 5: Session Deletion
1. Complete a PAN application
2. Delete the chat session from frontend
3. Start new session
4. **Expected:** Profile data still available (not deleted)
5. **Expected:** Details prefilled in new session

---

## Database Queries for Verification

### Check if profile was saved
```sql
SELECT * FROM user_profiles 
WHERE user_id = 'YOUR_USER_ID';
```

### View all profiles
```sql
SELECT 
    user_id,
    full_name,
    mother_name,
    email,
    annual_income,
    pan_preferences,
    created_at,
    updated_at
FROM user_profiles
ORDER BY created_at DESC;
```

### Check profile for specific user
```sql
SELECT 
    u.email as account_email,
    p.full_name,
    p.mother_name,
    p.email as pan_email,
    p.annual_income,
    p.pan_preferences
FROM auth.users u
LEFT JOIN user_profiles p ON u.id = p.user_id
WHERE u.email = 'user@example.com';
```

---

## Troubleshooting

### Profile not saving
**Check:**
1. Migration applied? `SELECT * FROM user_profiles LIMIT 1;`
2. Environment variables set? Check `.env` files
3. Supabase client initialized? Check logs for connection errors
4. RLS policies working? Try with service key

### Profile not prefilling
**Check:**
1. `user_id` passed from frontend? Check network tab
2. Profile exists in database? Run verification query
3. Flow state loading? Add debug prints in `prefill_flow_from_profile()`
4. `_profile_loaded` flag set? Check flow state

### Permission errors
**Check:**
1. RLS policies created? Run migration again
2. User authenticated? Check JWT token
3. Service key used in backend? Should bypass RLS

---

## Files Modified

```
pan-rag/agent/user_profile.py          [NEW] - Profile management module
pan-rag/agent/receptionist.py          [MODIFIED] - Added profile integration
pan-rag/generation/chain.py            [MODIFIED] - Pass user_id to receptionist
supabase/migrations/20240104000000_add_user_profiles.sql  [NEW] - Database schema
```

---

## Next Steps (Optional Enhancements)

### 1. Profile Management UI
- Add "My Profile" page in frontend
- Allow users to view/edit saved details
- Show application history

### 2. Smart Prefill Logic
- Detect when details might be outdated (e.g., old income)
- Ask for confirmation: "Is your income still ₹5,00,000?"
- Update only changed fields

### 3. Multiple Profiles
- Support family members (e.g., applying for child's PAN)
- Store multiple profiles per account
- Let user choose which profile to use

### 4. Analytics
- Track how often profiles are reused
- Measure time saved by prefilling
- Identify most commonly updated fields

### 5. Data Export
- Let users download their profile data
- GDPR compliance - right to data portability
- Export as JSON or PDF

---

## Security Considerations

✅ **Implemented:**
- Row Level Security (RLS) on `user_profiles` table
- Users can only access their own data
- Service key used in backend (bypasses RLS for admin operations)
- Cascade delete on user account deletion

⚠️ **Additional Recommendations:**
- Encrypt sensitive fields (PAN number, Aadhaar) at rest
- Add audit logging for profile changes
- Implement rate limiting on profile updates
- Add data retention policy (auto-delete after X months of inactivity)

---

## Performance Notes

- Profile lookup: Single query by `user_id` (indexed)
- Profile save: Upsert operation (insert or update)
- Prefill: Happens once per flow start (cached in flow state)
- No impact on existing flows without user_id

**Expected Performance:**
- Profile load: < 50ms
- Profile save: < 100ms
- Prefill overhead: Negligible (one-time per session)

---

## Rollback Plan

If issues occur, rollback steps:

1. **Disable profile integration:**
   ```python
   # In receptionist.py, comment out:
   # - prefill_flow_from_profile() call
   # - save_flow_to_profile() call
   ```

2. **Revert database changes:**
   ```sql
   DROP TABLE IF EXISTS user_profiles CASCADE;
   ```

3. **Restart services:**
   ```bash
   cd pan-rag && ./restart.sh
   # Restart backend server
   ```

---

## Success Metrics

Track these to measure success:

1. **User Experience:**
   - % of returning users with prefilled data
   - Average time saved per application
   - User satisfaction scores

2. **Technical:**
   - Profile save success rate
   - Profile load latency
   - Database query performance

3. **Business:**
   - Increase in completed applications
   - Reduction in support tickets
   - User retention rate

---

## Contact & Support

For issues or questions:
- Check logs: `pan-rag/logs/` and backend console
- Review Supabase dashboard for database errors
- Test with sample user account first
- Verify migration applied correctly

---

**Status:** ✅ Integration Complete - Ready for Testing
**Date:** 2026-04-30
**Version:** 1.0
