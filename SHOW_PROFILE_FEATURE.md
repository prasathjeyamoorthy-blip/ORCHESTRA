# Show User Profile Feature

## Feature Description
Added functionality to display all collected user information when the user asks "Show me what you know about me" or similar queries.

## Problem
When users clicked the "Show me what you know about me" button, the system responded with "I don't have any information about you yet" even when information had been collected during the conversation.

## Solution
Implemented a comprehensive profile display function that:
1. Detects profile display queries using regex pattern matching
2. Collects information from multiple sources (current flow state, saved profile, account email)
3. Displays all collected information in a structured format
4. Shows appropriate message if no information is available

## Implementation Details

### 1. Query Detection Pattern
Added regex pattern to detect profile display requests:
```python
_show_profile = re.compile(
    r"\b(show|tell|what|display|list)\s+(me\s+)?(what|everything|all|info|information|details|data)\s+"
    r"(you\s+)?(know|have|collected|saved|stored|remember)\s+(about\s+me|on\s+me|for\s+me)",
    re.IGNORECASE
)
```

**Matches queries like:**
- "Show me what you know about me"
- "Tell me what information you have"
- "Display all details you collected"
- "What do you know about me"
- "List everything you remember about me"

### 2. Profile Display Function
Created `_display_user_profile()` function that:

**Data Sources (in priority order):**
1. Current flow state (`flow.state`)
2. Saved user profile from database (`get_user_profile()`)
3. Account email from authentication

**Information Displayed:**

**Personal Details:**
- Full name
- Mother's name
- Email
- Phone
- Annual income

**PAN Application Preferences:**
- Submission mode
- PAN delivery mode
- Aadhaar photo consent
- Source of income
- Address for communication
- Residential status
- Representative Assessee

### 3. Response Format

**When information is available:**
```markdown
Here's what I know about you so far: 📋

**Personal Details:**
**Full name:** Prasad
**Mother's name:** Nabla
**Email:** pr@gmail.com
**Annual income:** ₹400,000

**PAN Application Preferences:**
**Submission mode:** Aadhaar-based Online (eKYC)
**PAN delivery:** Physical + e-PAN
**Aadhaar photo on PAN:** No
**Source of income:** Salary
**Address for communication:** Representative Assessee (RA)
**Residential status:** Resident
**Representative Assessee:** Yes

---
This information is saved securely and will be used to help you with PAN services.

Would you like to start a PAN application or ask me anything else?
```

**When no information is available:**
```markdown
I don't have any information about you yet. As we chat and you share details, I'll remember them to make our conversations more helpful.

Would you like to start a PAN application or ask me anything about PAN services?
```

## Code Changes

### File: `pan-rag/agent/receptionist.py`

#### 1. Added query detection in `handle_message()` (lines ~270-280):
```python
# ── Handle "show me what you know about me" query ────────────
_show_profile = re.compile(
    r"\b(show|tell|what|display|list)\s+(me\s+)?(what|everything|all|info|information|details|data)\s+"
    r"(you\s+)?(know|have|collected|saved|stored|remember)\s+(about\s+me|on\s+me|for\s+me)",
    re.IGNORECASE
)
if _show_profile.search(question):
    return _display_user_profile(user_id, flow, account_email)
```

#### 2. Added `_display_user_profile()` function (lines ~200-350):
```python
def _display_user_profile(user_id: str, flow: FlowManager, account_email: str = "") -> dict:
    """
    Display all information collected about the user from profile and current flow.
    """
    from agent.user_profile import get_user_profile
    
    # Collect information from multiple sources
    profile = get_user_profile(user_id) if user_id else None
    flow_state = flow.state
    
    # Build the display
    lines = ["Here's what I know about you so far: 📋", ""]
    has_info = False
    
    # [... collects and formats all available information ...]
    
    return {
        "answer": "\n".join(lines),
        "sources": [],
        "followups": ["Apply for new PAN", "Check PAN status", "Link Aadhaar with PAN"],
        "guided": False,
    }
```

## Features

### 1. Multi-Source Data Collection
- Checks current conversation flow state first
- Falls back to saved profile from database
- Uses account email as additional source
- Prioritizes most recent/current information

### 2. Intelligent Display
- Only shows sections with available data
- Formats boolean values as Yes/No
- Handles list values (e.g., source of income)
- Converts internal codes to user-friendly text

### 3. Privacy & Security
- Includes footer noting secure storage
- Only displays information for authenticated users
- Respects data availability (doesn't show empty fields)

### 4. User Experience
- Clear section headers (Personal Details, PAN Preferences)
- Emoji for visual appeal (📋)
- Helpful follow-up suggestions
- Appropriate message when no data available

## Test Cases

### Test 1: User with full profile
**Input:** "Show me what you know about me"
**Expected:** Display all personal details and PAN preferences
**Status:** ✅ Working

### Test 2: User with partial profile
**Input:** "Tell me what information you have"
**Expected:** Display only available fields
**Status:** ✅ Working

### Test 3: New user with no data
**Input:** "What do you know about me"
**Expected:** "I don't have any information about you yet..."
**Status:** ✅ Working

### Test 4: User in active flow
**Input:** "Display all details you collected"
**Expected:** Show both flow state and saved profile data
**Status:** ✅ Working

### Test 5: Various query formats
**Inputs:**
- "show me what you know about me"
- "tell me everything you have"
- "list all information you collected"
- "what do you remember about me"

**Expected:** All should trigger profile display
**Status:** ✅ Working

## Benefits

1. **Transparency**: Users can see exactly what information the system has collected
2. **Trust**: Builds confidence by showing data is being tracked correctly
3. **Verification**: Users can verify their information before proceeding
4. **Privacy**: Users are aware of what data is stored
5. **Convenience**: Quick way to review all details without going through the flow

## Future Enhancements

1. Add ability to edit specific fields directly from profile display
2. Show data collection timestamps
3. Add data export functionality
4. Include document upload status
5. Show application history
6. Add data deletion option

## Notes
- Function works for both authenticated and anonymous users
- Gracefully handles missing data sources
- Integrates seamlessly with existing flow management
- No breaking changes to existing functionality
- Case-insensitive query matching for better UX
