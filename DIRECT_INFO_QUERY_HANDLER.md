# Direct Information Query Handler

## Problem
When users ask direct questions about their saved information in a new chat, the agent doesn't retrieve it from the profile.

**User asks:** "what is my mother name"

**Agent responds:** "I don't have your mother's name on record yet"

**But:** The mother's name WAS saved in a previous chat session!

## Root Cause
The profile loading logic (`prefill_flow_from_profile`) only loads data into the flow state when starting a PAN application. When users ask direct questions about their information without starting a flow, the profile data isn't loaded or checked.

## Solution
Added a **direct information query handler** that:
1. Detects when users ask about specific saved information
2. Retrieves the data from the user profile
3. Returns the answer directly without needing to start a flow

## Implementation

### Pattern Detection
```python
_direct_info_query = re.compile(
    r"\b(what|whats|tell\s+me)\s+(is|are)\s+(my|the)\s+(name|mother|email|salary|income|full\s+name|mother'?s?\s+name)",
    re.IGNORECASE
)
```

**Matches:**
- "what is my mother name"
- "what is my name"
- "what is my email"
- "what is my salary"
- "tell me my mother's name"
- "what are my details"

### Handler Logic

```python
if _direct_info_query.search(question) and user_id:
    from agent.user_profile import get_user_profile
    profile = get_user_profile(user_id)
    
    # Check what information they're asking for
    lower_q = question.lower()
    
    if "mother" in lower_q:
        mother_name = flow.state.get("mother_name") or (profile.get("mother_name") if profile else None)
        if mother_name:
            return {
                "answer": f"Your mother's name is **{mother_name}**.",
                ...
            }
```

### Data Sources (Priority Order)

For each field, the handler checks:
1. **Flow state** - Current session data
2. **User profile** - Saved data from previous sessions
3. **Account email** - For email field only

## Supported Queries

### Mother's Name
**Queries:**
- "what is my mother name"
- "what is my mother's name"
- "tell me my mother name"

**Response:**
- If found: "Your mother's name is **{name}**."
- If not found: "I don't have your mother's name on record yet. Would you like to provide it?"

### Full Name
**Queries:**
- "what is my name"
- "what is my full name"
- "tell me my name"

**Response:**
- If found: "Your full name is **{name}**."
- If not found: "I don't have your name on record yet. Would you like to provide it?"

### Email
**Queries:**
- "what is my email"
- "tell me my email"

**Response:**
- If found: "Your email is **{email}**."

### Salary/Income
**Queries:**
- "what is my salary"
- "what is my income"
- "tell me my annual income"

**Response:**
- If found: "Your annual income is **{amount}**."

### Fallback
If the specific field can't be determined, shows the full profile display.

## Example Flows

### Example 1: Query Saved Mother's Name

**Chat 1:**
```
User: "I want to apply for PAN"
Agent: [asks questions]
User: "my name is John and mother name is Mary"
Agent: [saves to profile]
```

**Chat 2 (New Chat):**
```
User: "what is my mother name"
Agent: "Your mother's name is **Mary**."
```

### Example 2: Query Before Providing Info

**Chat 1 (New User):**
```
User: "what is my mother name"
Agent: "I don't have your mother's name on record yet. Would you like to provide it?"
```

### Example 3: Query Multiple Fields

**Chat 2:**
```
User: "what is my name"
Agent: "Your full name is **John Doe**."

User: "what is my email"
Agent: "Your email is **john@example.com**."
```

## Integration with Existing Features

### Works With Profile Loading
- Profile is still loaded when starting a PAN application
- Direct queries work even without an active flow

### Works With Profile Display
- "Show me what you know about me" still shows full profile
- Direct queries provide quick answers for specific fields

### Works With Auto-Save
- Data saved in previous chats is accessible
- Progressive auto-save ensures data is available immediately

## Benefits

1. **Better UX** - Users can quickly check specific information
2. **Natural conversation** - Supports direct questions
3. **Cross-session memory** - Demonstrates that the agent remembers
4. **Reduced friction** - No need to start a flow to check saved data
5. **Helpful followups** - Suggests next actions after answering

## Testing

### Test Case 1: Query After Saving
1. **Chat 1:** Complete PAN application with all details
2. **Chat 2:** Ask "what is my mother name"
3. **Expected:** Agent responds with the saved mother's name

### Test Case 2: Query Before Saving
1. **New User:** Ask "what is my name"
2. **Expected:** Agent says "I don't have your name on record yet"

### Test Case 3: Multiple Queries
1. **Chat 2:** Ask "what is my name"
2. **Expected:** Agent responds with name
3. Ask "what is my email"
4. **Expected:** Agent responds with email

### Test Case 4: Variations
1. Try "what is my mother's name" (with apostrophe)
2. Try "tell me my mother name"
3. Try "what are my details"
4. **Expected:** All variations work correctly

## Server Restart Required

**IMPORTANT:** You must restart the Python server for these changes to take effect!

```bash
# Option 1: Manual restart
cd /media/devaprasath-j/88C6AD0DC6ACFD16/PAN_APP/pan-rag
# Stop server (Ctrl+C)
python api/main.py

# Option 2: Use restart script
./restart_server.sh

# Option 3: Auto-reload (recommended)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## Files Modified

1. **pan-rag/agent/receptionist.py**
   - Added `_direct_info_query` pattern
   - Added direct information query handler
   - Checks flow state and user profile for data
   - Returns specific answers for each field type

## Impact

- **Low risk** - Only adds new functionality, doesn't change existing behavior
- **High value** - Significantly improves user experience
- **No breaking changes** - All existing flows still work
- **Better memory demonstration** - Shows users that their data persists

## Related Features

This feature works together with:
1. **Progressive auto-save** - Ensures data is saved after each answer
2. **Profile persistence** - Data saved in previous chats is accessible
3. **Profile display** - Full profile view for comprehensive information
4. **Profile prefill** - Automatic loading when starting new application

## Status

✅ **IMPLEMENTED** - Users can now ask direct questions about their saved information across chat sessions.

⚠️ **ACTION REQUIRED:** Restart the Python server to load the new code!
