# Name Extraction and Modification Fix - Preserve Exact Case

## Issues Fixed

### Issue 1: Name Extraction Failing for Lowercase Input
**Problem**: When user says "my name is devaprasath" (lowercase), the system responds "I don't have your name on record yet"

**Root Cause**: 
- The primary extraction pattern with "name" keyword works correctly
- However, the fallback standalone pattern only matched Title Case names: `r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]*){1,3})\b"`
- This meant lowercase names like "devaprasath" would not be extracted by the fallback

**Fix Applied**:
- Enhanced the fallback extraction logic in `_extract_details()` function
- Changed to a single unified pattern that matches any case: `r"\b([A-Za-z][A-Za-z]+(?:\s+[A-Za-z][A-Za-z]*){0,3})\b"`
- **Preserves exact case as provided by user** - no automatic Title Case conversion
- Added minimum length check (3 characters) to avoid false matches

### Issue 2: Name Modification Too Restrictive
**Problem**: When trying to update name in modification menu, system only accepts input if it contains "full name" keyword - user can't just type the new name

**Root Cause**:
1. **Detection Issue**: `_detect_modification_field()` pattern was too restrictive - didn't include common modification phrases
2. **Application Issue**: `_apply_field_update()` for `full_name` was converting to Title Case, not preserving user input
3. **Inline Extraction Issue**: When user says "my name is deva" in the modification menu, the inline extraction patterns required Title Case (`[A-Z][a-z]+`)

**Fix Applied**:

#### Detection Enhancement (`_detect_modification_field()`):
- Added more flexible patterns to detect name modification intent:
  - Added: `name\s+is`, `name\s+to`, `update\s+name`
  - Now matches: "change name", "update name", "name is X", "name to X"

**Code Changes** (`pan-rag/agent/receptionist.py` line ~1630):
```python
if re.search(r"\b(full\s+name|my\s+name|name\s+on\s+aadhaar|aadhaar\s+name|just\s+name|the\s+name|change\s+name|update\s+name|name\s+is|name\s+to)\b", lower):
```

#### Application Enhancement (`_apply_field_update()`):
- Completely rewrote name update logic to handle multiple input formats:
  1. Extracts name from patterns like "name is X", "change to X", "update to X"
  2. Falls back to treating entire input as the name
  3. Filters out command words: 'my', 'name', 'is', 'the', 'full', 'change', 'update', 'to', 'it'
  4. **Preserves exact case as provided by user** - no Title Case conversion
- Same logic applied to both `full_name` and `mother_name` fields

**Code Changes** (`pan-rag/agent/receptionist.py` lines ~1850-1900):
```python
if field == "full_name":
    # Extract name from input - handle both "name is X" and just "X"
    name_match = re.search(
        r"(?:name\s+(?:is|to)\s+|change\s+(?:to|it\s+to)\s+|update\s+(?:to|it\s+to)\s+)?([A-Za-z][A-Za-z\s]{1,50})$",
        text, re.IGNORECASE
    )
    if name_match:
        candidate = name_match.group(1).strip()
    else:
        # If no pattern match, treat entire input as the name
        candidate = text
    
    # Filter out common command words
    words = candidate.split()
    _FILTER_WORDS = {'my', 'name', 'is', 'the', 'full', 'change', 'update', 'to', 'it'}
    filtered_words = [w for w in words if w.lower() not in _FILTER_WORDS]
    
    if filtered_words:
        candidate = ' '.join(filtered_words)  # Preserve original case
        if _is_valid_name(candidate):
            flow.state["full_name"] = candidate
```

#### Inline Extraction Enhancement (Confirmation Step - PRIORITY 4):
- Fixed inline extraction when user says "my name is deva" in the modification menu
- Changed patterns from `[A-Z][a-z]+` (Title Case only) to `[A-Za-z][A-Za-z\s]+` (any case)
- Removed `.title()` conversion to preserve original case
- This handles the case where user is in the modification menu and provides the field name + value in one message

**Code Changes** (`pan-rag/agent/receptionist.py` lines ~1070-1120):
```python
if field == "full_name":
    # Try to extract name from the message - handle any case
    name_match = re.search(r"(?:my\s+)?(?:full\s+)?name\s+is\s+([A-Za-z][A-Za-z\s]+?)(?:\s*$|\s+and\b|\s*,)", user_input, re.IGNORECASE)
    if not name_match:
        name_match = re.search(r"(?:my\s+)?(?:full\s+)?name\s+([A-Za-z][A-Za-z\s]+?)(?:\s*$|\s+and\b|\s*,)", user_input, re.IGNORECASE)
    
    if name_match:
        candidate = name_match.group(1).strip()
        words = candidate.split()
        filtered_words = [w for w in words if w.lower() not in ('my', 'name', 'is', 'the', 'full')]
        if filtered_words:
            candidate = ' '.join(filtered_words)  # Preserve original case
            if _is_valid_name(candidate):
                flow.state["full_name"] = candidate
                flow.state["pending_modification"] = None
                flow.save()
                return _build_confirmation(flow)
```

## Test Cases Now Supported

### Extraction (during details collection):
✅ "my name is devaprasath" → Extracts "devaprasath" (exact case)
✅ "devaprasath" → Extracts "devaprasath" (exact case)
✅ "My name is Devaprasath Kumar" → Extracts "Devaprasath Kumar" (exact case)
✅ "name: DEVAPRASATH" → Extracts "DEVAPRASATH" (exact case)
✅ "my name is DeVaPrAsAtH" → Extracts "DeVaPrAsAtH" (exact case)

### Modification (during confirmation review):
✅ User clicks "Change something" → System shows modification menu
✅ User types "my name is deva" → Updates to "deva" (exact case) ✨ **NEW FIX**
✅ User types "name" → System asks for new name
✅ User types "devaprasath" → Updates to "devaprasath" (exact case)
✅ User types "DEVAPRASATH KUMAR" → Updates to "DEVAPRASATH KUMAR" (exact case)
✅ User types "change to devaprasath" → Updates to "devaprasath" (exact case)
✅ User types "name is Devaprasath Kumar" → Updates to "Devaprasath Kumar" (exact case)

## Key Behavior Changes

### Before:
- All names were automatically converted to Title Case
- "devaprasath" → stored as "Devaprasath"
- "JOHN DOE" → stored as "John Doe"
- Inline extraction in modification menu required Title Case

### After:
- Names are stored exactly as user provides them
- "devaprasath" → stored as "devaprasath"
- "JOHN DOE" → stored as "JOHN DOE"
- "Devaprasath Kumar" → stored as "Devaprasath Kumar"
- "DeVaPrAsAtH" → stored as "DeVaPrAsAtH"
- Inline extraction works with any case

## Files Modified
- `pan-rag/agent/receptionist.py`
  - Function: `_extract_details()` (lines ~1380-1500)
    - Mother's name extraction: Removed `.title()` conversion
    - Full name extraction: Removed `.title()` conversion
    - Fallback pattern: Unified to match any case
  - Function: `_detect_modification_field()` (lines ~1630-1670)
    - Added more flexible name detection patterns
  - Function: `_apply_field_update()` (lines ~1850-1900)
    - Removed `.title()` conversion for both full_name and mother_name
  - Function: `_continue_flow()` - Confirmation step PRIORITY 4 (lines ~1070-1120)
    - Fixed inline extraction patterns to match any case
    - Removed `.title()` conversion
    - Now handles "my name is deva" correctly in modification menu

## Testing Recommendations
1. Test name extraction with various formats:
   - All lowercase: "my name is devaprasath" → should store "devaprasath"
   - All uppercase: "MY NAME IS JOHN DOE" → should store "JOHN DOE"
   - Title case: "My name is Devaprasath" → should store "Devaprasath"
   - Mixed case: "my name is DeVaPrAsAtH" → should store "DeVaPrAsAtH"
   - Just the name: "devaprasath" → should store "devaprasath"
   - With middle name: "devaprasath kumar" → should store "devaprasath kumar"

2. Test name modification (after clicking "Change something"):
   - Inline with field name: "my name is deva" → should update to "deva"
   - Just field name: "name" → should ask for value, then accept "deva"
   - Just the name: "devaprasath" → should update to "devaprasath"
   - With keywords: "change to DEVAPRASATH" → should update to "DEVAPRASATH"
   - With "name is": "name is Devaprasath Kumar" → should update to "Devaprasath Kumar"

3. Verify mother's name extraction and modification work the same way

4. Verify confirmation screen displays names exactly as user provided them

## Notes
- **Case preservation is now complete** - no automatic Title Case conversion anywhere
- User has full control over capitalization in all flows
- Minimum 3-character requirement for standalone names prevents false matches
- Debug logging added to track extraction and modification flow
- Name validation ensures extracted text is actually a valid name (not keywords or random text)
- Filter words are still removed (e.g., "my", "name", "is") but remaining text preserves exact case
- **Critical fix**: Inline extraction in modification menu now works with lowercase names
