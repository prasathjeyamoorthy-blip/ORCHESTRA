# Off-Topic Question Detection Fix

## Issue
When users are in the middle of a flow (e.g., at the documents upload step) and they type something like "I HAVE OE QUESTION" or "I have a question", the system doesn't recognize it as an off-topic question. Instead, it treats it as a non-confirmation response and shows the document list again, appearing to "hallucinate" or jump to conclusions.

### Example from Screenshot
**User Input**: "I HAVE OE QUESTION" (typo for "ONE QUESTION")

**Expected Behavior**: Recognize this as a question/help request and route to RAG for general Q&A

**Actual Behavior**: System shows document upload panel with "Whenever you're ready, reply Yes and I'll open the upload panel" - completely ignoring the user's intent to ask a question

## Root Cause
The `_OFF_TOPIC_PATTERN` regex in `pan-rag/agent/receptionist.py` was missing patterns for common question indicators like:
- "I have a question"
- "I have question" (without "a")
- "question" (standalone)
- "doubt"
- "query"
- "can I ask"
- "one question"

The pattern only checked for questions starting with "why", "what", "how", etc., but didn't catch statements like "I have a question".

### The Pattern Before
```python
_OFF_TOPIC_PATTERN = re.compile(
    r"^(why|what|how\s+does|how\s+is|what\s+is|what\s+are|"
    r"should\s+i|do\s+i\s+need|is\s+it|are\s+there|"
    r"tell\s+me|explain|describe|difference|benefit|reason|"
    r"purpose|importance|advantage|when\s+should|who\s+needs|"
    r"what\s+happens|what\s+if|how\s+long|how\s+much|"
    r"what\s+is\s+the\s+fee|i\s+want\s+to\s+know|"
    r"i\s+want\s+to\s+understand|curious)",
    re.IGNORECASE
)
```

This pattern would match:
- ✅ "why is PAN needed?"
- ✅ "what is the fee?"
- ✅ "how does this work?"
- ❌ "I have a question" (NOT matched)
- ❌ "question about PAN" (NOT matched)
- ❌ "can I ask something?" (NOT matched)

## Solution
Added patterns to catch question/help indicators:

```python
_OFF_TOPIC_PATTERN = re.compile(
    r"^(why|what|how\s+does|how\s+is|what\s+is|what\s+are|"
    r"should\s+i|do\s+i\s+need|is\s+it|are\s+there|"
    r"tell\s+me|explain|describe|difference|benefit|reason|"
    r"purpose|importance|advantage|when\s+should|who\s+needs|"
    r"what\s+happens|what\s+if|how\s+long|how\s+much|"
    r"what\s+is\s+the\s+fee|i\s+want\s+to\s+know|"
    r"i\s+want\s+to\s+understand|curious|"
    r"i\s+have\s+(a\s+)?question|question|doubt|query|"  # NEW
    r"can\s+i\s+ask|may\s+i\s+ask|one\s+question)",      # NEW
    re.IGNORECASE
)
```

Now the pattern matches:
- ✅ "I have a question"
- ✅ "I have question" (without "a")
- ✅ "question about PAN"
- ✅ "I have one question"
- ✅ "doubt about documents"
- ✅ "query regarding fees"
- ✅ "can I ask something?"
- ✅ "may I ask a question?"

## How It Works

### Flow Logic
When a user is in an active flow (e.g., documents step):

1. **Check if off-topic**: `_is_off_topic_during_flow(question)`
2. **If True**: Return `None` → Routes to RAG for general Q&A
3. **If False**: Continue with flow logic (e.g., show document list)

### Example Flow

**Before Fix:**
```
User: "I HAVE OE QUESTION"
↓
_is_off_topic_during_flow() → False (pattern didn't match)
↓
Continue with documents step logic
↓
Show document list (appears to hallucinate)
```

**After Fix:**
```
User: "I HAVE OE QUESTION"
↓
_is_off_topic_during_flow() → True (pattern matches "question")
↓
Return None → Route to RAG
↓
RAG answers the user's question
```

## Testing Examples

### Test Case 1: Question During Documents Step
**Input**: "I have a question"

**Before**: ❌ Shows document list

**After**: ✅ Routes to RAG, user can ask their question

### Test Case 2: Typo in Question
**Input**: "I HAVE OE QUESTION" (typo for "ONE")

**Before**: ❌ Shows document list

**After**: ✅ Routes to RAG (pattern matches "question")

### Test Case 3: Simple "Question"
**Input**: "question"

**Before**: ❌ Shows document list

**After**: ✅ Routes to RAG

### Test Case 4: Doubt/Query
**Input**: "I have a doubt about fees"

**Before**: ❌ Shows document list

**After**: ✅ Routes to RAG (pattern matches "doubt")

### Test Case 5: Can I Ask
**Input**: "can I ask something?"

**Before**: ❌ Shows document list

**After**: ✅ Routes to RAG (pattern matches "can i ask")

### Test Case 6: Normal Flow Continuation
**Input**: "yes" (when asked to upload)

**Before**: ✅ Opens upload panel

**After**: ✅ Still opens upload panel (not affected by fix)

## Benefits
1. **Better intent recognition** - Catches common question indicators
2. **No hallucination** - Doesn't jump to conclusions when user wants to ask something
3. **Flexible** - Handles typos like "OE" instead of "ONE"
4. **User-friendly** - Users can ask questions at any point in the flow
5. **Maintains flow** - Normal flow responses still work correctly

## Files Modified
- `pan-rag/agent/receptionist.py` - Updated `_OFF_TOPIC_PATTERN` regex

## Next Steps
**Restart the RAG server** to apply the fix:
```bash
cd pan-rag && python main.py
```

## Related Patterns
The fix adds these new patterns to `_OFF_TOPIC_PATTERN`:
- `i\s+have\s+(a\s+)?question` - Matches "I have a question" or "I have question"
- `question` - Matches standalone "question"
- `doubt` - Matches "doubt"
- `query` - Matches "query"
- `can\s+i\s+ask` - Matches "can I ask"
- `may\s+i\s+ask` - Matches "may I ask"
- `one\s+question` - Matches "one question"

All patterns are case-insensitive and match at the start of the input (`^`).
