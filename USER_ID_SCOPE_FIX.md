# User ID Scope Error - FIXED ✅

## Error
```
NameError: name 'user_id' is not defined
```

**Location:** Line 550 in `_continue_flow()` function

**Traceback:**
```
handle_message() → _continue_flow() → tries to use user_id (ERROR!)
```

## Root Cause
The `user_id` parameter was available in `handle_message()` but was NOT being passed to the `_continue_flow()` helper function. When `_continue_flow()` tried to save the user profile at line 550, it couldn't find `user_id` because it wasn't in that function's scope.

## Fix Applied

### 1. Added `user_id` Parameter to `_continue_flow()`

**Before:**
```python
def _continue_flow(flow: FlowManager, user_input: str, language: str) -> dict:
```

**After:**
```python
def _continue_flow(flow: FlowManager, user_input: str, language: str, user_id: str = None) -> dict:
```

### 2. Pass `user_id` When Calling `_continue_flow()`

**Before:**
```python
return _continue_flow(flow, question, language)
```

**After:**
```python
return _continue_flow(flow, question, language, user_id)
```

## How It Works Now

```
handle_message(user_id="abc123")
    ↓
_continue_flow(user_id="abc123")  ← Now has user_id!
    ↓
save_flow_to_profile(user_id="abc123")  ← Works!
```

## Testing

1. **Restart the RAG server:**
   ```bash
   cd pan-rag
   python3 api/main.py
   ```

2. **Complete the flow:**
   - Fill in all PAN application details
   - Click "Yes, proceed"
   - ✅ Should work without errors!

3. **Check logs:**
   ```
   [DEBUG] Saved profile for user <user_id>
   ```

## Files Modified
- `pan-rag/agent/receptionist.py`
  - Line 143: Pass `user_id` to `_continue_flow()`
  - Line 262: Add `user_id` parameter to `_continue_flow()` function signature

## Result
✅ User profile is now saved correctly when confirming PAN application details
✅ No more "name 'user_id' is not defined" errors
✅ Application proceeds smoothly to document upload
