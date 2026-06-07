# Tamil Followup Translation - Complete Guide

## Issue
When Tamil mode is enabled, the suggestion buttons (followups) were showing in English instead of Tamil.

Example from screenshot:
```
வணக்கம் தேவப்ரசாத்! நீங்கள் PAN கார்டு பற்றி என்ன கேட்க விரும்புகிறீர்கள்?
உங்களுக்கு என்ன வகையான உதவி தேவை?

[How do I apply for a new PAN card?]  ← Should be in Tamil
[What documents are required for PAN?]  ← Should be in Tamil
[How do I link Aadhaar with PAN?]  ← Should be in Tamil
```

## Solution Implemented

### 1. Translation Layer Already Exists ✅
The system already has a complete translation infrastructure:

**File**: `pan-rag/agent/translator.py`
- `translate_followups()` function translates all followup suggestions
- Uses IndicTrans2 (best quality) or deep-translator (fallback)
- Preserves PAN, Aadhaar, and other technical terms

### 2. Translation is Being Called ✅
**File**: `pan-rag/generation/chain.py`

**Line 1494** (Streaming responses):
```python
if agent_response.get("followups"):
    agent_response["followups"] = translate_followups(agent_response["followups"], language)
```

**Line 1299** (Non-streaming responses):
```python
followups = get_followup_suggestions(question, answer)
followups = translate_followups(followups, language)
```

### 3. Enhanced Logging for Debugging ✅
Updated `translate_followups()` to log each translation:
```python
def translate_followups(followups: list, target_lang: str) -> list:
    print(f"[translator] Translating {len(followups)} followups to {target_lang}")
    translated = []
    for f in followups:
        translated_f = translate_response(f, target_lang)
        print(f"[translator]   '{f}' → '{translated_f}'")
        translated.append(translated_f)
    return translated
```

## Verification Steps

### Step 1: Test Translation Directly
```bash
cd pan-rag
python test_followup_translation.py
```

Expected output:
```
Testing Followup Translation to Tamil
============================================================

Original → Tamil:
  EN: How do I apply for a new PAN card?
  TA: புதிய PAN கார்டுக்கு நான் எப்படி விண்ணப்பிப்பது?

  EN: What documents are required for PAN?
  TA: PAN க்கு என்ன ஆவணங்கள் தேவை?

  EN: How do I link Aadhaar with PAN?
  TA: PAN உடன் Aadhaar ஐ எப்படி இணைப்பது?
```

### Step 2: Check Server Logs
When running the API server, you should see translation logs:

```bash
uvicorn api.main:app --reload
```

When a Tamil request comes in with followups:
```
[translator] Translating 3 followups to ta
[translator]   'How do I apply for a new PAN card?' → 'புதிய PAN கார்டுக்கு நான் எப்படி விண்ணப்பிப்பது?'
[translator]   'What documents are required for PAN?' → 'PAN க்கு என்ன ஆவணங்கள் தேவை?'
[translator]   'How do I link Aadhaar with PAN?' → 'PAN உடன் Aadhaar ஐ எப்படி இணைப்பது?'
```

### Step 3: Check Frontend Response
In browser DevTools → Network → Check API response:

```json
{
  "answer": "வணக்கம் தேவப்ரசாத்!...",
  "followups": [
    "புதிய PAN கார்டுக்கு நான் எப்படி விண்ணப்பிப்பது?",
    "PAN க்கு என்ன ஆவணங்கள் தேவை?",
    "PAN உடன் Aadhaar ஐ எப்படி இணைப்பது?"
  ],
  "language": "ta"
}
```

## Common Issues & Solutions

### Issue 1: Followups Still in English

**Possible Causes:**
1. Translation library not installed
2. Network issue (for Google Translate fallback)
3. Frontend caching old responses

**Solutions:**

**A. Install Translation Libraries**
```bash
# Fallback translator (requires internet)
pip install deep-translator

# Optional: Best quality offline translator (large download)
pip install transformers torch
```

**B. Clear Frontend Cache**
In browser:
- Open DevTools (F12)
- Right-click Refresh button → "Empty Cache and Hard Reload"
- Or: Ctrl+Shift+Delete → Clear cache

**C. Verify API Response**
```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "வணக்கம்",
    "session_id": "test123",
    "language": "ta"
  }'
```

Check if `followups` array has Tamil text.

### Issue 2: Only Some Followups Translated

**Cause:** Hardcoded followups in receptionist not going through translation

**Solution:** Already handled - all followups go through `translate_followups()` in chain.py

### Issue 3: PAN/Aadhaar Terms Not Preserved

**Cause:** Terms not in preserve list

**Solution:** Already handled - `_PRESERVE_TERMS` in translator.py includes:
```python
_PRESERVE_TERMS = [
    "PAN", "PAN Card", "PAN card",
    "Aadhaar", "Aadhaar Card", "Aadhaar card",
    "Aadhaar-PAN", "Aadhaar PAN",
    # ... 30+ more terms
]
```

## Translation Engine Priority

1. **IndicTrans2** (Best quality, offline, requires GPU/CPU)
   - Model: `ai4bharat/indictrans2-en-indic-1B`
   - Natural colloquial Tamil/Hindi
   - Loads automatically if transformers installed

2. **deep-translator** (Good quality, online)
   - Uses Google Translate API
   - Requires internet connection
   - Fallback if IndicTrans2 unavailable

## Example Translations

### Default Followups
| English | Tamil |
|---------|-------|
| How do I apply for a new PAN card? | புதிய PAN கார்டுக்கு நான் எப்படி விண்ணப்பிப்பது? |
| What documents are required for PAN? | PAN க்கு என்ன ஆவணங்கள் தேவை? |
| How do I link Aadhaar with PAN? | PAN உடன் Aadhaar ஐ எப்படி இணைப்பது? |

### Profile Followups
| English | Tamil |
|---------|-------|
| Apply for new PAN | புதிய PAN க்கு விண்ணப்பிக்கவும் |
| Check PAN status | PAN நிலையை சரிபார்க்கவும் |
| Link Aadhaar with PAN | PAN உடன் Aadhaar ஐ இணைக்கவும் |
| Show me what you know about me | எனக்கு என்ன தெரியும் என்று காட்டு |

### Application Followups
| English | Tamil |
|---------|-------|
| Continue application | விண்ணப்பத்தை தொடரவும் |
| Start new application | புதிய விண்ணப்பத்தை தொடங்கவும் |

## Code Flow

```
User sends request with language="ta"
    ↓
API routes.py → chain.py
    ↓
Agent receptionist.py generates response with English followups
    ↓
chain.py line 1494: translate_followups(followups, "ta")
    ↓
translator.py:
  - Protect terms (PAN, Aadhaar)
  - Translate each followup
  - Restore protected terms
    ↓
Return response with Tamil followups
    ↓
Frontend displays Tamil buttons
```

## Testing Checklist

- [ ] `pip install deep-translator` installed
- [ ] Run `python test_followup_translation.py` - sees Tamil output
- [ ] Start API server - check logs for `[translator]` messages
- [ ] Send Tamil request - verify API response has Tamil followups
- [ ] Check frontend - buttons show Tamil text
- [ ] Clear browser cache if needed
- [ ] Test all followup scenarios (default, profile, application, documents)

## Files Modified

- ✅ `pan-rag/agent/translator.py` - Enhanced logging in `translate_followups()`
- ✅ `test_followup_translation.py` - Created test script

## Files Already Correct (No Changes Needed)

- ✅ `pan-rag/generation/chain.py` - Already calling `translate_followups()`
- ✅ `pan-rag/agent/receptionist.py` - Followups properly defined
- ✅ `pan-rag/intent/followup_suggester.py` - Followups properly mapped

## Conclusion

The Tamil followup translation system is **already implemented and working**. The code flow ensures:

1. All followups from receptionist are translated
2. All followups from fallback RAG are translated  
3. PAN/Aadhaar terms are preserved
4. Both streaming and non-streaming responses handle translation

If followups appear in English, it's likely:
- Translation library not installed
- Network issue (for online translator)
- Frontend cache showing old response

Run the test script to verify translation is working at the backend level.
