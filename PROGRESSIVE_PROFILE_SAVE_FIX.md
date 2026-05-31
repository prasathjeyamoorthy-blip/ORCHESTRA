# Progressive Profile Auto-Save Fix

## Problem
User reported that details provided during PAN application were not persisting across chat sessions. When opening a new chat, the agent would ask for the same information again, even though it was already provided in a previous session.

## Root Cause
The progressive auto-save feature was **implemented correctly** in `receptionist.py`, but the `user_id` parameter was **not being passed** from `chain.py` to `handle_message()` in 4 out of 5 code paths.

### Implementation Status Before Fix
- ✅ Auto-save logic implemented in `_advance_after_answer()` (saves after each optional question)
- ✅ Auto-save logic implemented in details_collection step (saves after extracting personal details)
- ✅ `user_id` parameter added to `_advance_after_answer()` function signature
- ✅ All 8 calls to `_advance_after_answer()` pass `user_id` correctly
- ❌ **Only 1 out of 5 calls to `handle_message()` in chain.py was passing `user_id`**

### Missing `user_id` in chain.py
The `chain.py` file has 5 different code paths that call `handle_message()`:

1. **Line 639** - Upload intent with active flow → ✅ **Already had `user_id`**
2. **Line 697** - Greeting/farewell with active flow → ❌ **Missing `user_id`**
3. **Line 720** - Context continuation → ❌ **Missing `user_id`**
4. **Line 872** - New service detection (run method) → ❌ **Missing `user_id`**
5. **Line 1226** - New service detection (run_stream method) → ❌ **Missing `user_id`**

## Solution
Added `user_id=user_id` parameter to all 4 missing `handle_message()` calls in `chain.py`.

### Changes Made

#### File: `pan-rag/generation/chain.py`

**Change 1 - Line 697 (Greeting/farewell with active flow):**
```python
# Before:
agent_response = handle_message(question, session_id, language, user_context=user_context, account_email=account_email)

# After:
agent_response = handle_message(question, session_id, language, user_context=user_context, account_email=account_email, user_id=user_id)
```

**Change 2 - Line 720 (Context continuation):**
```python
# Before:
agent_response = handle_message(question, session_id, language, user_context=user_context, account_email=account_email)

# After:
agent_response = handle_message(question, session_id, language, user_context=user_context, account_email=account_email, user_id=user_id)
```

**Change 3 - Line 872 (New service detection in run method):**
```python
# Before:
agent_response = handle_message(question, session_id, language, user_context=user_context, account_email=account_email)

# After:
agent_response = handle_message(question, session_id, language, user_context=user_context, account_email=account_email, user_id=user_id)
```

**Change 4 - Line 1226 (New service detection in run_stream method):**
```python
# Before:
agent_response = handle_message(question, session_id, language, user_context=user_context, account_email=account_email)

# After:
agent_response = handle_message(question, session_id, language, user_context=user_context, account_email=account_email, user_id=user_id)
```

## How Progressive Auto-Save Works

### Auto-Save Trigger Points

1. **After each optional question** (via `_advance_after_answer()`):
   - Submission mode
   - Delivery mode
   - Aadhaar photo consent
   - Source of income
   - Address for communication
   - Residential status
   - Representative assessee

2. **After extracting personal details** (in details_collection step):
   - Full name
   - Mother's name
   - Email
   - Annual income/salary

3. **At confirmation** (when user clicks "Yes"):
   - All collected data saved to profile

### Auto-Save Implementation

**In `_advance_after_answer()` function:**
```python
def _advance_after_answer(flow: FlowManager, user_id: str = None) -> dict:
    # Auto-save preferences to profile after each answer
    if user_id:
        try:
            save_flow_to_profile(user_id, flow.state)
            print(f"[DEBUG] Auto-saved preferences to profile for user {user_id}")
        except Exception as e:
            print(f"[ERROR] Failed to auto-save preferences: {e}")
    
    # ... rest of function
```

**In details_collection step handler:**
```python
# Try to extract whatever the user typed (name, mother, salary)
_extract_details(flow, inp, user_input)
flow.save()  # CRITICAL: Save after extraction!

# Auto-save extracted details to profile (progressive save)
if user_id and any([
    flow.state.get("full_name"),
    flow.state.get("mother_name"),
    flow.state.get("email"),
    flow.state.get("salary")
]):
    try:
        save_flow_to_profile(user_id, flow.state)
        print(f"[DEBUG] Auto-saved details to profile for user {user_id}")
    except Exception as e:
        print(f"[ERROR] Failed to auto-save profile: {e}")
```

## Expected Behavior After Fix

1. **User provides details in Chat 1:**
   - User: "I want to apply for PAN"
   - Agent asks optional questions
   - User answers: "Physical delivery", "Yes to Aadhaar photo", "Salary as income"
   - **Auto-save happens after each answer** ✅

2. **User provides personal details:**
   - User: "My name is John Doe, mother name is Jane Doe, email john@example.com, salary 5 lakh"
   - **Auto-save happens immediately after extraction** ✅

3. **User opens new chat (Chat 2):**
   - User: "I want to apply for PAN"
   - Agent: "Welcome back! I see you've applied before. Would you like to use the same options?"
   - **Agent shows previously saved preferences** ✅
   - User can choose to reuse or change them

4. **User abandons flow before confirmation:**
   - Even if user doesn't click "Yes" at confirmation
   - All answered questions are still saved
   - **Data persists for next session** ✅

## Testing Checklist

- [ ] Start PAN application in Chat 1
- [ ] Answer 2-3 optional questions (submission mode, delivery mode, aadhaar photo)
- [ ] Check server logs for "[DEBUG] Auto-saved preferences to profile"
- [ ] Provide personal details (name, mother's name, email, salary)
- [ ] Check server logs for "[DEBUG] Auto-saved details to profile"
- [ ] Open new chat (Chat 2)
- [ ] Start PAN application again
- [ ] Verify agent shows "Welcome back! I see you've applied before"
- [ ] Verify agent displays previously saved preferences
- [ ] Test "Use same options" flow
- [ ] Test "Change some options" flow

## Files Modified

1. **pan-rag/generation/chain.py** - Added `user_id` parameter to 4 `handle_message()` calls

## Files Already Correct (No Changes Needed)

1. **pan-rag/agent/receptionist.py** - Auto-save logic already implemented
2. **pan-rag/agent/user_profile.py** - Profile save/load functions already correct
3. **pan-rag/api/routes.py** - Already passing `user_id` from API to chain
4. **pan-rag/memory/memory_manager.py** - Memory management already correct

## Impact

- **Low risk** - Only adding a parameter that was already being used in 1 out of 5 code paths
- **High value** - Fixes major UX issue where users had to re-enter information
- **No breaking changes** - `user_id` parameter is optional with default value
- **Backward compatible** - Works with existing code

## Related Issues

- User query 9: "it is not properly fetching from memory"
- User query 10: "i already gave those details but still those details are not known to the agent when i open another chat"

## Status

✅ **FIXED** - All `handle_message()` calls now pass `user_id` parameter correctly.
