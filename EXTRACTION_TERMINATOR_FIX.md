# Extraction Terminator Pattern Fix

## Problem
The name and salary extraction was capturing too much text, including words after "and" keyword.

**User input:** "my full name is deva and mother name is navina and salary is 30 lakhs"

**What was extracted (WRONG):**
- Full name: "prasad" (should be "deva")
- Mother's name: "navina and salary" (should be "navina")
- Salary: ₹4,00,000 (should be ₹30,00,000)

## Root Cause
The terminator pattern in the regex was `(?=\s*(?:and\b|,|\n|$|...))` which uses `\s*` (zero or more spaces). This made the lookahead too flexible and allowed the regex to match beyond the "and" keyword.

### Why It Failed

**Pattern:** `[A-Za-z]+(?:\s+[A-Za-z]+)*` with terminator `(?=\s*(?:and\b|...))`

**Input:** "name is deva and mother"

**What happened:**
1. Regex matches "deva " (with trailing space)
2. Lookahead checks: `\s*` matches zero spaces, then looks for "and"
3. But the greedy `*` in the name pattern already consumed the space
4. Lookahead fails to find "and" at the right position
5. Regex continues matching and captures "and mother" as part of the name

## Solution
Changed the terminator pattern from `(?=\s*(?:and\b|...))` to `(?=\s+and\b|\s*,|\s*$|...)`

### Key Changes

**1. Explicit space before "and":**
- Before: `(?=\s*(?:and\b|...))`
- After: `(?=\s+and\b|\s*,|\s*$|...)`

The `\s+` (one or more spaces) before `and\b` ensures the lookahead requires at least one space before "and", preventing the greedy name pattern from consuming it.

**2. Non-greedy quantifier in name pattern:**
- Before: `[A-Za-z]+(?:\s+[A-Za-z]+)*`
- After: `[A-Za-z]+(?:\s+[A-Za-z]+)*?`

The `*?` makes the pattern non-greedy, so it stops as soon as the terminator is found.

## Changes Made

### File: `pan-rag/agent/receptionist.py`

**Change 1 - Mother's name terminator:**
```python
# Before:
_TERM = r"(?=\s*(?:and\b|,|\n|$|\bsalary\b|...))"

# After:
_TERM = r"(?=\s+and\b|\s*,|\s*$|\bsalary\b|...)"
```

**Change 2 - Full name terminator:**
```python
# Before:
_TERM = r"(?=\s*(?:and\b|,|\n|$|\bmother\b|...))"

# After:
_TERM = r"(?=\s+and\b|\s*,|\s*$|\bmother\b|...)"
```

**Change 3 - Multi-field update patterns:**
```python
# Before:
r"([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s+and\b|\s*$|,)"

# After:
r"([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s+and\b|\s*,|\s*$)"
```

## How It Works Now

### Example 1: "my full name is deva and mother name is navina and salary is 30 lakhs"

**Step 1 - Extract full name:**
- Pattern: `(?:my\s+)?(?:full\s+)?name\s+(?:is\s+)?[:\-]?\s*([A-Za-z]+(?:\s+[A-Za-z]+)*?)(?=\s+and\b|...)`
- Matches: "my full name is deva"
- Captures: "deva"
- Lookahead sees: " and" (space + "and")
- Stops at: "deva" ✅

**Step 2 - Extract mother's name:**
- Pattern: `(?:my\s+)?mother(?:'?s)?\s+(?:full\s+)?name\s*(?:is\s*)?[:\-]?\s*([A-Za-z]+(?:\s+[A-Za-z]+)*?)(?=\s+and\b|...)`
- Matches: "mother name is navina"
- Captures: "navina"
- Lookahead sees: " and" (space + "and")
- Stops at: "navina" ✅

**Step 3 - Extract salary:**
- Pattern: `(?:salary|income)\s*(?:is\s*)?[:\-]?\s*(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)\s*(lakh|...)?`
- Matches: "salary is 30 lakhs"
- Captures: "30" and "lakhs"
- Calculates: 30 × 100,000 = 3,000,000
- Formats: "₹30,00,000" ✅

### Example 2: "name is John, mother name is Mary, salary 5 lakh"

**With commas as separators:**
- Full name: "John" (stops at comma) ✅
- Mother's name: "Mary" (stops at comma) ✅
- Salary: "₹5,00,000" ✅

### Example 3: "my name is Deva Prasath J and mother name is Nabi"

**Multi-word names:**
- Full name: "Deva Prasath J" (stops at " and") ✅
- Mother's name: "Nabi" (stops at end of string) ✅

## Test Cases

### Single-Word Names ✅
- "my full name is deva and mother name is navina"
  - full_name: "deva"
  - mother_name: "navina"

### Multi-Word Names ✅
- "my name is John Doe and mother name is Mary Jane"
  - full_name: "John Doe"
  - mother_name: "Mary Jane"

### With Salary ✅
- "my name is deva and mother name is navina and salary is 30 lakhs"
  - full_name: "deva"
  - mother_name: "navina"
  - salary: "₹30,00,000"

### Comma Separators ✅
- "name is John, mother name is Mary, salary 5 lakh"
  - full_name: "John"
  - mother_name: "Mary"
  - salary: "₹5,00,000"

### End of String ✅
- "my name is deva"
  - full_name: "deva"

### Complex Names ✅
- "my name is Deva Prasath J and mother name is Nabi Begum"
  - full_name: "Deva Prasath J"
  - mother_name: "Nabi Begum"

## Debugging

### Server Logs to Check

**Successful extraction:**
```
[DEBUG _extract_details] Input text: 'my full name is deva and mother name is navina and salary is 30 lakhs'
[DEBUG _extract_details] Mother name candidate: 'navina'
[DEBUG _extract_details] Mother name after filtering: 'navina'
[DEBUG _extract_details] ✓ Extracted mother_name: 'navina'
[DEBUG _extract_details] Full name candidate: 'deva'
[DEBUG _extract_details] Full name after filtering: 'deva'
[DEBUG _extract_details] ✓ Extracted full_name: 'deva'
[DEBUG _extract_details] Salary match: raw_num='30', unit='lakhs'
[DEBUG _extract_details] ✓ Extracted salary: '₹30,00,000'
```

**Failed extraction (old behavior):**
```
[DEBUG _extract_details] Mother name candidate: 'navina and salary'  ❌
[DEBUG _extract_details] ✗ Mother name failed validation
```

## Related Issues Fixed

1. **Names capturing "and" keyword** - Fixed by requiring space before "and" in terminator
2. **Mother's name including salary** - Fixed by proper terminator pattern
3. **Salary not extracted** - Fixed by allowing mother's name to stop at "and"
4. **Multi-word names broken** - Fixed by non-greedy quantifier

## Files Modified

1. **pan-rag/agent/receptionist.py**
   - Updated `_extract_details()` terminator patterns
   - Updated `_extract_multiple_field_updates()` terminator patterns

## Impact

- **Low risk** - Only changed regex terminator patterns to be more precise
- **High value** - Fixes critical extraction bug that was causing wrong data to be saved
- **No breaking changes** - All previous valid inputs still work, now with better accuracy
- **Better extraction** - More reliable parsing of complex multi-field inputs

## Status

✅ **FIXED** - Name and salary extraction now correctly stops at "and" keyword and other terminators.
