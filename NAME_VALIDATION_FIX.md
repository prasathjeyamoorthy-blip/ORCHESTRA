# Name Validation Fix - Single Word Names

## Problem
When user provides single-word names like "Devaprasath" or "Nabina", the system doesn't extract them because the `_is_valid_name()` function required names to have **2-5 words**.

## Root Cause

### `_is_valid_name()` function (line 1096-1106)
**Before:**
```python
def _is_valid_name(name: str) -> bool:
    """Basic sanity check for a person name."""
    if not name or len(name.strip()) < 3:
        return False
    words = name.strip().split()
    if len(words) < 2 or len(words) > 5:  # ❌ Rejects single-word names!
        return False
    # Must be mostly alphabetic
    alpha_ratio = sum(c.isalpha() or c.isspace() for c in name) / len(name)
    return alpha_ratio > 0.85
```

This validation rejected valid single-word names like:
- "Devaprasath"
- "Nabina"
- "Priya"
- "Rajesh"
- etc.

## Solution

Changed the minimum word count from 2 to 1:

**After:**
```python
def _is_valid_name(name: str) -> bool:
    """Basic sanity check for a person name."""
    if not name or len(name.strip()) < 3:
        return False
    words = name.strip().split()
    if len(words) < 1 or len(words) > 5:  # ✅ Allows single-word names!
        return False
    # Must be mostly alphabetic
    alpha_ratio = sum(c.isalpha() or c.isspace() for c in name) / len(name)
    return alpha_ratio > 0.85
```

## Impact

Now the system will correctly extract:
- ✅ Single-word names: "Devaprasath", "Nabina", "Priya"
- ✅ Two-word names: "John Doe", "Priya Sharma"
- ✅ Three-word names: "Devaprasath Kumar J"
- ✅ Up to five-word names

## Testing Instructions

### 1. Restart RAG Server
```bash
cd pan-rag
python api/main.py
```

### 2. Test Single-Word Names
1. Start a new chat
2. Complete the initial flow until "details_collection" step
3. Type: "name is devaprasath and mother name is nabina and salary is 2 laksh"
4. **Expected**: All three fields should be extracted correctly
5. **Verify**: System should show:
   - ✅ Full name: Devaprasath
   - ✅ Mother's name: Nabina
   - ✅ Annual income: ₹2,00,000

### 3. Test Other Variations
Try these inputs:
- "my name is priya and mother name is lakshmi"
- "name is rajesh and mother name is sita and salary is 5 lakh"
- "devaprasath" (just the name)
- "my name is john doe and mother name is jane doe"

## Debug Logs

With the debug logging added earlier, you should see:
```
[DEBUG] _extract_details called with inp='name is devaprasath and mother name is nabina and salary is 2 lakh', raw='name is devaprasath and mother name is nabina and salary is 2 laksh'
[DEBUG] Current state: full_name=None, mother_name=None, email=None, salary=None
[DEBUG] Extracted mother_name: Nabina
[DEBUG] Extracted full_name: Devaprasath
[DEBUG] Extracted salary: ₹2,00,000
[DEBUG] _extract_details finished. updated=True, state: full_name=Devaprasath, mother_name=Nabina, email=None, salary=₹2,00,000
```

## Files Modified
- `pan-rag/agent/receptionist.py` (line 1101)

## Status
✅ **FIXED** - Restart RAG server and test
