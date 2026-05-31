# Multi-Field Extraction Debug

## Problem
When user provides all information in one message (e.g., "name is devaprasath and mother name is nabina and salary is 2 laksh"), the system doesn't extract all fields correctly and keeps asking for the same information.

## Investigation

The `_extract_details()` function in `pan-rag/agent/receptionist.py` should extract:
- Full name
- Mother's name  
- Email
- Salary

from a single message.

## Debug Logging Added

Added comprehensive debug logging to trace the extraction process:

### 1. Function Entry (line 928)
```python
print(f"[DEBUG] _extract_details called with inp={inp!r}, raw={raw!r}")
print(f"[DEBUG] Current state: full_name={flow.state.get('full_name')}, mother_name={flow.state.get('mother_name')}, email={flow.state.get('email')}, salary={flow.state.get('salary')}")
```

### 2. Mother's Name Extraction (line 985)
```python
print(f"[DEBUG] Extracted mother_name: {candidate}")
```

### 3. Full Name Extraction - Primary (line 1009)
```python
print(f"[DEBUG] Extracted full_name: {candidate}")
```

### 4. Full Name Extraction - Fallback (line 1025)
```python
print(f"[DEBUG] Extracted full_name (fallback): {candidate}")
```

### 5. Salary Extraction (line 1074)
```python
print(f"[DEBUG] Extracted salary: {formatted}")
```

### 6. Function Exit (line 1078)
```python
print(f"[DEBUG] _extract_details finished. updated={updated}, state: full_name={flow.state.get('full_name')}, mother_name={flow.state.get('mother_name')}, email={flow.state.get('email')}, salary={flow.state.get('salary')}")
```

## Testing Instructions

### 1. Restart RAG Server
```bash
cd pan-rag
python api/main.py
```

### 2. Test Multi-Field Input
1. Start a new chat
2. Complete the initial flow until you reach "details_collection" step
3. Type: "name is devaprasath and mother name is nabina and salary is 2 laksh"
4. **Check the RAG server console** for debug logs showing:
   - What input was received
   - What fields were extracted
   - Final state after extraction

### 3. Expected Debug Output
```
[DEBUG] _extract_details called with inp='name is devaprasath and mother name is nabina and salary is 2 lakh', raw='name is devaprasath and mother name is nabina and salary is 2 laksh'
[DEBUG] Current state: full_name=None, mother_name=None, email=None, salary=None
[DEBUG] Extracted mother_name: Nabina
[DEBUG] Extracted full_name: Devaprasath
[DEBUG] Extracted salary: ₹2,00,000
[DEBUG] _extract_details finished. updated=True, state: full_name=Devaprasath, mother_name=Nabina, email=None, salary=₹2,00,000
```

## Possible Issues to Check

### 1. Name Validation
The `_is_valid_name()` function requires:
- At least 3 characters
- 2-5 words
- At least 85% alphabetic characters

**Issue**: "Devaprasath" is a single word, but the validation requires 2-5 words!

### 2. Regex Patterns
- Mother's name pattern might not match "mother name is" (without apostrophe)
- Full name pattern might not match "name is" at the beginning

### 3. Terminator Issues
The regex uses terminators to stop at "and", which might cause issues with multi-field input.

## Next Steps

1. **Run the test** and check the debug logs
2. **Identify which field(s) are not being extracted**
3. **Fix the specific regex or validation** causing the issue

## Files Modified
- `pan-rag/agent/receptionist.py` (lines 928, 985, 1009, 1025, 1074, 1078)

## Status
🔍 **DEBUG MODE** - Restart RAG server and test to see debug output
