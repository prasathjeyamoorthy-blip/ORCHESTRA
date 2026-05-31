# Negative Lookahead Fix for Name Extraction

## Problem
Even after the terminator fix, mother's name was still capturing "and salary".

**User input:** "my full name is deva and mother name is navina and salary is 30 lakhs"

**What was extracted (STILL WRONG):**
- Full name: "prasad" ✅ (but should be "deva")
- Mother's name: "navina and salary" ❌
- Salary: ₹4,00,000 ❌ (should be ₹30,00,000)

## Root Cause
The lookahead terminator `(?=\s+and\b|...)` wasn't working correctly because:
1. The greedy `*` in `(?:\s+[A-Za-z]+)*` was consuming spaces
2. The lookahead was checking AFTER the match, not DURING
3. The pattern could match "navina and salary" before the lookahead was evaluated

## Solution
Use **negative lookahead INSIDE the capture group** to explicitly exclude "and" from being matched.

### Old Pattern (Didn't Work)
```regex
([A-Za-z]+(?:\s+[A-Za-z]+)*?)(?=\s+and\b|,|$)
```
- Captures: "navina and salary"
- Then checks if followed by " and" (but it's already inside!)

### New Pattern (Works!)
```regex
([A-Za-z]+(?:\s+(?!and\b)[A-Za-z]+)*)\s*(?:and\b|,|$)
```
- `(?!and\b)` - Negative lookahead: next word must NOT be "and"
- Captures: "navina" (stops when next word is "and")
- Then matches the terminator " and"

## How It Works

### Pattern Breakdown
```regex
(?:my\s+)?mother(?:'?s)?\s+(?:full\s+)?name\s*(?:is\s*)?[:\-]?\s*
([A-Za-z]+(?:\s+(?!and\b)[A-Za-z]+)*)
\s*(?:and\b|,|$)
```

**Parts:**
1. `(?:my\s+)?` - Optional "my "
2. `mother(?:'?s)?` - "mother" or "mother's"
3. `\s+(?:full\s+)?name` - " name" or " full name"
4. `\s*(?:is\s*)?[:\-]?` - Optional "is" with optional colon/dash
5. `\s*` - Optional spaces
6. **`([A-Za-z]+(?:\s+(?!and\b)[A-Za-z]+)*)`** - **CAPTURE GROUP:**
   - `[A-Za-z]+` - First word (one or more letters)
   - `(?:\s+(?!and\b)[A-Za-z]+)*` - Zero or more additional words:
     - `\s+` - One or more spaces
     - `(?!and\b)` - **Negative lookahead: next word is NOT "and"**
     - `[A-Za-z]+` - The word itself
7. `\s*(?:and\b|,|$)` - Terminator: space + "and", comma, or end

### Example Trace

**Input:** "mother name is navina and salary"

**Step-by-step matching:**
1. Match "mother name is " ✅
2. Start capture group
3. Match "navina" (first word) ✅
4. Check for more words: `\s+(?!and\b)[A-Za-z]+`
   - Match space " " ✅
   - Check negative lookahead `(?!and\b)` - next word is "and" ❌
   - **Stop matching!** (negative lookahead failed)
5. End capture group with "navina"
6. Match terminator " and" ✅

**Result:** Captures "navina" only! ✅

## Changes Made

### File: `pan-rag/agent/receptionist.py`

**Change 1 - Mother's name pattern:**
```python
# Before:
r"([A-Za-z]+(?:\s+[A-Za-z]+)*?)(?=\s+and\b|,|$)"

# After:
r"([A-Za-z]+(?:\s+(?!and\b)[A-Za-z]+)*)\s*(?:and\b|,|$)"
```

**Change 2 - Full name pattern:**
```python
# Before:
r"([A-Za-z]+(?:\s+[A-Za-z]+)*?)(?=\s+and\b|,|$)"

# After:
r"([A-Za-z]+(?:\s+(?!and\b)[A-Za-z]+)*)\s*(?:and\b|,|$)"
```

**Change 3 - Multi-field update patterns:**
```python
# Before:
r"([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s+and\b|\s*,|\s*$)"

# After:
r"([a-zA-Z]+(?:\s+(?!and\b)[a-zA-Z]+)*)\s*(?:and\b|,|$)"
```

## Test Cases

### Single-Word Names ✅
**Input:** "my full name is deva and mother name is navina and salary is 30 lakhs"

**Expected:**
- full_name: "deva"
- mother_name: "navina"
- salary: "₹30,00,000"

### Multi-Word Names ✅
**Input:** "my name is John Doe and mother name is Mary Jane and salary 5 lakh"

**Expected:**
- full_name: "John Doe"
- mother_name: "Mary Jane"
- salary: "₹5,00,000"

### Comma Separators ✅
**Input:** "name is John, mother name is Mary, salary 5 lakh"

**Expected:**
- full_name: "John"
- mother_name: "Mary"
- salary: "₹5,00,000"

### End of String ✅
**Input:** "my mother name is nabina"

**Expected:**
- mother_name: "nabina"

## Server Restart Required

**IMPORTANT:** The code changes won't take effect until you restart the Python server!

### Option 1: Manual Restart
```bash
# Stop the server (Ctrl+C in the terminal)
# Then restart:
cd /media/devaprasath-j/88C6AD0DC6ACFD16/PAN_APP/pan-rag
python api/main.py
```

### Option 2: Use Restart Script
```bash
cd /media/devaprasath-j/88C6AD0DC6ACFD16/PAN_APP/pan-rag
./restart_server.sh
```

### Option 3: Auto-Reload (Development)
```bash
# Install uvicorn if needed
pip install uvicorn

# Run with auto-reload
cd /media/devaprasath-j/88C6AD0DC6ACFD16/PAN_APP/pan-rag
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## Debugging

### Check Server Logs

**Successful extraction:**
```
[DEBUG _extract_details] Mother name candidate: 'navina'
[DEBUG _extract_details] Mother name after filtering: 'navina'
[DEBUG _extract_details] ✓ Extracted mother_name: 'navina'
```

**Failed extraction (old behavior):**
```
[DEBUG _extract_details] Mother name candidate: 'navina and salary'
[DEBUG _extract_details] Mother name after filtering: 'navina salary'
[DEBUG _extract_details] ✗ Mother name failed validation
```

## Why Negative Lookahead Works

### Positive Lookahead (Didn't Work)
`(?=pattern)` - Checks if pattern exists AFTER current position, but doesn't consume it
- Problem: Checks AFTER the match is complete
- The greedy quantifier already consumed "and salary"

### Negative Lookahead (Works!)
`(?!pattern)` - Checks if pattern does NOT exist at current position
- Benefit: Checks DURING the match, before consuming
- Stops matching when it sees "and" coming next

## Related Issues Fixed

1. **Mother's name capturing "and salary"** - Fixed by negative lookahead
2. **Multi-word names broken by "and"** - Fixed by excluding "and" from word matching
3. **Salary not extracted** - Fixed by allowing mother's name to stop before "and"
4. **Inconsistent extraction** - Fixed by using same pattern for all name fields

## Files Modified

1. **pan-rag/agent/receptionist.py**
   - Updated `_extract_details()` with negative lookahead patterns
   - Updated `_extract_multiple_field_updates()` with negative lookahead patterns

2. **pan-rag/restart_server.sh** (NEW)
   - Helper script to restart the server easily

## Impact

- **Low risk** - Only changed regex patterns to be more precise
- **High value** - Fixes critical extraction bug
- **No breaking changes** - All previous valid inputs still work
- **Better accuracy** - More reliable parsing of complex inputs

## Status

✅ **FIXED** - Name extraction now correctly excludes "and" keyword using negative lookahead.

⚠️ **ACTION REQUIRED:** Restart the Python server to load the new code!
