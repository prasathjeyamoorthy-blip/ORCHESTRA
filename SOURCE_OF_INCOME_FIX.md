# Source of Income Options Fix ✅

## Problem
When typing "Source of income" to change that field, the system was showing the salary input prompt instead of the source of income checkbox options.

## Root Cause
The field detection function `_detect_modification_field()` was checking patterns in the wrong order:

1. ❌ First checked: `(salary|income|earning|annual|pay)` → matched "income" in "source of income"
2. ✅ Then checked: `(source\s+of\s+income|income\s+source)` → never reached!

So "Source of income" was being detected as "salary" field instead of "source_of_income" field.

## Fix Applied
**Reordered the checks** to check for "source of income" BEFORE checking for "salary/income":

```python
# Check "source of income" BEFORE "salary/income" to avoid false matches
if re.search(r"\b(source\s+of\s+income|income\s+source|income\s+type)\b", lower):
    return "source_of_income"
if re.search(r"\b(salary|income|earning|annual|pay)\b", lower):
    return "salary"
```

This ensures more specific patterns are matched before generic ones.

## Test It Now

1. **Restart the RAG server:**
   ```bash
   cd pan-rag
   python api/main.py
   ```

2. **Test the flow:**
   - Go to confirmation screen
   - Type: "source of income"
   - ✅ **Expected:** Should show checkbox options:
     - Salary
     - Income from Business / Profession
     - Income from House property
     - Income from Other sources
     - Capital Gains
     - No income

## Files Modified
- `pan-rag/agent/receptionist.py` (lines 1130-1160)
