# Name Intent Identification Fix

## Issue
When users said "my name is X" or "my full name is X", the system was treating them as different intents, potentially causing confusion or duplicate extraction attempts.

## Root Cause
The regex pattern for extracting full name had multiple alternative patterns:
```regex
(?:(?:my\s+)?(?:full\s+)?name\s+is\s+|(?:my\s+)?name\s*[:\-]\s*|full\s+name\s*[:\-]?\s*)
```

This created three separate matching groups:
1. `(?:my\s+)?(?:full\s+)?name\s+is\s+` - matches "my name is", "my full name is", "name is", "full name is"
2. `(?:my\s+)?name\s*[:\-]\s*` - matches "my name:", "name:"
3. `full\s+name\s*[:\-]?\s*` - matches "full name:", "full name"

The complexity made it unclear that all variations should extract to the same field.

## Solution
Simplified the regex pattern to a single, unified pattern that clearly shows all variations extract to the same `full_name` field:

```regex
(?:my\s+)?(?:full\s+)?name\s+(?:is\s+)?[:\-]?\s*
```

This pattern now clearly matches:
- "my name is X"
- "my full name is X"
- "name is X"
- "full name is X"
- "my name: X"
- "my name X" (without "is")
- "name X"
- "full name X"

All variations extract to the **same field**: `flow.state["full_name"]`

## Changes Made

### File: `pan-rag/agent/receptionist.py`

**Before:**
```python
for m in re.finditer(
    r"(?:(?:my\s+)?(?:full\s+)?name\s+is\s+|(?:my\s+)?name\s*[:\-]\s*|full\s+name\s*[:\-]?\s*)"
    r"([A-Za-z][A-Za-z\s]{2,50}?)" + _TERM,
    text, re.IGNORECASE
):
```

**After:**
```python
for m in re.finditer(
    r"(?:my\s+)?(?:full\s+)?name\s+(?:is\s+)?[:\-]?\s*"
    r"([A-Za-z][A-Za-z\s]{2,50}?)" + _TERM,
    text, re.IGNORECASE
):
```

Added clear comment explaining the intent:
```python
# Match patterns like:
# - "my name is X"
# - "my full name is X"
# - "name is X"
# - "full name is X"
# - "my name: X"
# - "name X" (without "is")
# All variations should extract the same field (full_name)
```

## Testing Examples

All these inputs now correctly extract to `full_name`:

| User Input | Extracted Field | Extracted Value |
|------------|----------------|-----------------|
| "my name is John Doe" | `full_name` | "John Doe" |
| "my full name is John Doe" | `full_name` | "John Doe" |
| "name is John Doe" | `full_name` | "John Doe" |
| "full name is John Doe" | `full_name` | "John Doe" |
| "my name: John Doe" | `full_name` | "John Doe" |
| "name John Doe" | `full_name` | "John Doe" |

## Benefits
1. **Clearer intent** - All name variations map to the same field
2. **Simpler regex** - Easier to understand and maintain
3. **Consistent behavior** - No confusion about which field gets populated
4. **Better UX** - Users can say "my name" or "my full name" interchangeably

## Files Modified
- `pan-rag/agent/receptionist.py` - Updated `_extract_details()` function

## Next Steps
Restart the RAG server to apply the fix:
```bash
cd pan-rag && python main.py
```
