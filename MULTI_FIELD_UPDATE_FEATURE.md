# Multi-Field Update Feature

## Problem
When users clicked "Change something" at the confirmation step, they could only change ONE field at a time. This was tedious if they wanted to update multiple fields.

**Previous behavior:**
1. User clicks "Change something"
2. Agent shows menu of fields
3. User says "change my name"
4. Agent asks for new name
5. User provides name
6. Agent shows confirmation again
7. If user wants to change another field, they have to repeat steps 1-6

## Solution
Implemented multi-field update capability that allows users to change multiple fields in a single message.

**New behavior:**
1. User clicks "Change something"
2. Agent shows menu with examples of multi-field updates
3. User says: **"change my name to John and mother name to Mary and salary to 5 lakh"**
4. Agent extracts all three updates and shows confirmation immediately ✅

## Implementation

### New Function: `_extract_multiple_field_updates()`

This function parses user input and extracts multiple field updates in a single pass.

**Supported patterns:**

#### Name Updates
- "name to John"
- "name is John"
- "change my name to John"
- "update name John"

#### Mother's Name Updates
- "mother name to Mary"
- "mother name is Mary"
- "change my mother name to Mary"
- "update mom name Mary"

#### Email Updates
- Any valid email address: "john@example.com"
- "email to john@example.com"
- "change email john@example.com"

#### Salary Updates
- "salary to 5 lakh"
- "salary is 500000"
- "income 5,00,000"
- "change salary to 5 lakh"
- "update income 500000"

#### Submission Mode Updates
- "submission to aadhaar"
- "submission mode online"
- "change submission to upload"

#### Delivery Mode Updates
- "delivery to physical"
- "delivery to soft"
- "pan delivery email"

#### Aadhaar Photo Updates
- "aadhaar photo to yes"
- "aadhaar photo is no"

### Integration Points

**1. PRIORITY 3 - User clicks "Change something":**
```python
# NEW: Try to extract multiple field updates first
updates_made = _extract_multiple_field_updates(flow, inp, user_input)

if updates_made:
    # User provided multiple updates - apply them and show confirmation
    flow.state["pending_modification"] = None
    flow.save()
    return _build_confirmation(flow)

# Fall back to single field detection if no updates extracted
field = _detect_modification_field(inp)
if field:
    # ... existing single-field logic
```

**2. PRIORITY 4 - User responds to "what to change" prompt:**
```python
# NEW: Try to extract multiple field updates first
updates_made = _extract_multiple_field_updates(flow, inp, user_input)

if updates_made:
    # User provided multiple updates - apply them and show confirmation
    flow.state["pending_modification"] = None
    flow.save()
    return _build_confirmation(flow)

# Fall back to single field detection
field = _detect_modification_field(inp)
# ... existing single-field logic
```

**3. Updated menu message:**
```markdown
Sure! Which detail would you like to change?

- **Full name** — currently: *John Doe*
- **Mother's name** — currently: *Jane Doe*
- **Email** — currently: *john@example.com*
- **Annual income** — currently: *₹5,00,000*
- **Submission mode** — currently: *Aadhaar-based Online (eKYC)*
- **PAN delivery** — currently: *Physical + e-PAN*
- **Aadhaar photo on PAN** — currently: *Yes*
- **Source of income** — currently: *Salary*
- **Address for communication** — currently: *Residence*
- **Residential status** — currently: *Resident*
- **Representative Assessee** — currently: *No*

**You can change multiple fields at once!**
Examples:
- *"change my name to John and salary to 5 lakh"*
- *"update email to john@example.com and mother name to Mary"*
- Or just tell me one field: *"change my name"*
```

## Usage Examples

### Example 1: Change Multiple Fields
**User:** "change my name to Devaprasath and mother name to Nabi and salary to 10 lakh"

**Agent extracts:**
- full_name: "Devaprasath"
- mother_name: "Nabi"
- salary: "₹10,00,000"

**Agent response:** Shows updated confirmation with all three changes applied ✅

### Example 2: Change Name and Email
**User:** "update name to John Doe and email john.doe@example.com"

**Agent extracts:**
- full_name: "John Doe"
- email: "john.doe@example.com"

**Agent response:** Shows updated confirmation ✅

### Example 3: Change Single Field (Still Works)
**User:** "change my name"

**Agent response:** "Please provide your **full name exactly as it appears on your Aadhaar card**:"

**User:** "John Doe"

**Agent response:** Shows updated confirmation ✅

### Example 4: Complex Update
**User:** "change name to Mary Jane, mother name to Sarah Jane, email mary@example.com, and salary to 8 lakh"

**Agent extracts:**
- full_name: "Mary Jane"
- mother_name: "Sarah Jane"
- email: "mary@example.com"
- salary: "₹8,00,000"

**Agent response:** Shows updated confirmation with all four changes ✅

## Pattern Recognition

The function uses regex patterns with terminators to extract values:

### Terminator Pattern
Values are extracted until one of these is encountered:
- `and` keyword
- Comma `,`
- End of string `$`

This allows natural language like:
- "name to John and mother name to Mary" ✅
- "name to John, mother name to Mary" ✅
- "name to John" ✅

### Word Filtering
Common words are filtered out to extract clean values:
- "my name is John" → extracts "John"
- "change my mother name to Mary" → extracts "Mary"
- "update salary to 5 lakh" → extracts "5 lakh"

### Validation
All extracted values are validated:
- Names: Must pass `_is_valid_name()` check
- Email: Must match email regex pattern
- Salary: Must be valid number with optional unit

## Benefits

1. **Faster workflow** - Change multiple fields in one message instead of multiple back-and-forth exchanges
2. **Natural language** - Users can express changes naturally: "change X to Y and Z to W"
3. **Backward compatible** - Single-field changes still work exactly as before
4. **Flexible syntax** - Supports multiple patterns and separators (and, comma, etc.)
5. **Better UX** - Reduces friction and number of interactions needed

## Edge Cases Handled

### Case 1: No Updates Detected
**User:** "change something"

**Behavior:** Falls back to showing menu and asking which field to change (existing behavior)

### Case 2: Partial Updates
**User:** "change name to John and something else"

**Behavior:** Extracts "John" for name, ignores "something else", shows confirmation with name updated

### Case 3: Invalid Values
**User:** "change name to 123 and salary to abc"

**Behavior:** Both fail validation, no updates made, falls back to single-field detection

### Case 4: Mixed Valid/Invalid
**User:** "change name to John and salary to abc"

**Behavior:** Extracts "John" for name (valid), ignores salary (invalid), shows confirmation with name updated

## Testing Checklist

- [ ] Test single field update: "change my name"
- [ ] Test two field update: "change name to John and salary to 5 lakh"
- [ ] Test three field update: "change name to John and mother name to Mary and email john@example.com"
- [ ] Test with commas: "change name to John, mother name to Mary"
- [ ] Test with mixed separators: "change name to John and mother name to Mary, salary 5 lakh"
- [ ] Test case preservation: "change name to deva" → should store "deva" (lowercase)
- [ ] Test multi-word names: "change name to John Doe and mother name to Mary Jane"
- [ ] Test email extraction: "update email john@example.com and name John"
- [ ] Test salary with units: "change salary to 10 lakh and name John"
- [ ] Test invalid values: "change name to 123" → should fall back to menu
- [ ] Test from menu prompt: Click "Change something" → type multi-field update
- [ ] Test from direct input: At confirmation, type "no, change X and Y"

## Files Modified

1. **pan-rag/agent/receptionist.py**
   - Added `_extract_multiple_field_updates()` function
   - Updated PRIORITY 3 handler to try multi-field extraction first
   - Updated PRIORITY 4 handler to try multi-field extraction first
   - Updated menu message to show multi-field examples

## Impact

- **Low risk** - Falls back to existing single-field logic if no updates detected
- **High value** - Significantly improves UX for users who need to change multiple fields
- **No breaking changes** - All existing single-field flows still work
- **Better discoverability** - Menu now shows examples of multi-field updates

## Status

✅ **IMPLEMENTED** - Users can now change multiple fields in a single message at the confirmation step.
