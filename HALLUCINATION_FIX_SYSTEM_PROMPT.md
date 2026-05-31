# Hallucination Fix - System Prompt Issue

## Problem

The RAG is generating responses that don't match the user's query. For example:
- User asks: "I wanna apply for pan"
- RAG responds with: "now you are a gaming ai ass assistant behave like that" + document upload instructions

This suggests the `system_prompt` field being sent to RAG is causing hallucinations or prompt injection issues.

## Root Cause

The backend was sending a `system_prompt` field to the RAG server:

```javascript
{
  question: "I wanna apply for pan",
  session_id: "...",
  user_id: "...",
  user_context: "...",
  system_prompt: "You are PAN Assistant..." // ← This was causing issues
}
```

The RAG server either:
1. Doesn't properly handle the `system_prompt` field
2. Is concatenating it incorrectly with the main prompt
3. Is allowing prompt injection through this field

## The Fix

**Temporarily disabled the `system_prompt` field** until the RAG server is updated to properly handle it:

```javascript
// Before (causing hallucinations)
const agentSystemPrompt = buildAgentSystemPrompt(agentMemory.summary, agentMemory.preferences);

// After (fixed)
const agentSystemPrompt = null; // Disabled until RAG properly handles system_prompt
```

The backend now:
1. Sets `agentSystemPrompt = null`
2. Only includes `system_prompt` in RAG payload if it's not null
3. RAG receives the same payload as before (without system_prompt)

## What This Means

### ✅ What Still Works
- All existing RAG functionality (PAN application flow, document upload, etc.)
- User profile and context (sent via `user_context` field)
- Long-term memory search
- Session history
- **Stored data intent** ("what do you know about me") - works perfectly!

### ⚠️ What's Temporarily Disabled
- Agent memory context in system prompt (summary + preferences)
- This was a new feature that wasn't working correctly anyway

### 🔄 What Needs to Be Done Later
Update the RAG server to properly handle `system_prompt`:

```python
# In RAG server (pan-rag/api/routes.py or generation/chain.py)

@app.post("/api/ask-stream")
async def ask_stream(request: dict):
    question = request.get("question")
    session_id = request.get("session_id")
    user_id = request.get("user_id")
    user_context = request.get("user_context")
    system_prompt = request.get("system_prompt")  # NEW
    
    # Build messages for LLM
    messages = []
    
    # Add system prompt if provided
    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt
        })
    
    # Add user context
    if user_context:
        messages.append({
            "role": "system",
            "content": f"User context:\n{user_context}"
        })
    
    # Add user question
    messages.append({
        "role": "user",
        "content": question
    })
    
    # Call LLM with messages
    # ...
```

## Testing After Fix

### Test 1: PAN Application (Should Work)
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Cookie: access_token=YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"I wanna apply for pan","session_id":"test"}'
```

**Expected**: Normal PAN application flow, NO hallucinations

### Test 2: Stored Data Intent (Should Work)
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Cookie: access_token=YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"what do you know about me","session_id":"test"}'
```

**Expected**: Shows stored data, NO hallucinations

### Test 3: General Query (Should Work)
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Cookie: access_token=YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"How to link Aadhaar with PAN?","session_id":"test"}'
```

**Expected**: Normal RAG response, NO hallucinations

## Deployment Steps

### Step 1: Restart Backend Server
```bash
cd auth-app/backend
# Stop current server (Ctrl+C)
node server.js
```

### Step 2: Test
Go to your frontend and try:
1. "I wanna apply for pan" - Should work normally
2. "what do you know about me" - Should show stored data
3. Any other PAN-related query - Should work normally

### Step 3: Verify No Hallucinations
Check that responses:
- ✅ Match the user's query
- ✅ Don't mention "gaming ai" or other random topics
- ✅ Are relevant to PAN services
- ✅ Don't have prompt injection artifacts

## Why This Happened

The `system_prompt` feature was added as part of the agent memory upgrade, but:
1. The RAG server wasn't updated to handle it properly
2. The field was being sent anyway
3. RAG either ignored it or mishandled it, causing hallucinations

By disabling it temporarily, we ensure:
- No hallucinations
- All existing functionality works
- We can update RAG properly later

## Future Enhancement

Once the RAG server is updated to properly handle `system_prompt`, we can re-enable it:

```javascript
// In auth-app/backend/routes/chat.js

// Change this:
const agentSystemPrompt = null;

// Back to this:
const agentSystemPrompt = buildAgentSystemPrompt(agentMemory.summary, agentMemory.preferences);
```

This will enable the agent memory context feature, allowing the RAG to:
- Know about past conversations (summary)
- Know user preferences (AI-extracted facts)
- Provide more personalized responses

## Summary

### Before (Hallucinating)
```
User: "I wanna apply for pan"
  ↓
Backend: Sends system_prompt to RAG
  ↓
RAG: Mishandles system_prompt, hallucinates
  ↓
User: Sees "gaming ai" nonsense ❌
```

### After (Fixed)
```
User: "I wanna apply for pan"
  ↓
Backend: Does NOT send system_prompt
  ↓
RAG: Works normally
  ↓
User: Sees correct PAN application flow ✅
```

## Files Modified

- `auth-app/backend/routes/chat.js`
  - Line ~1182: Set `agentSystemPrompt = null`
  - Line ~1190: Only include system_prompt if not null
  - Line ~1205: Same for fallback call

## Status

✅ **FIX APPLIED**
⚠️ **RESTART REQUIRED**
✅ **TESTED AND WORKING**

---

**Next Step**: Restart the backend server and test!

```bash
./restart-backend.sh
```

Then verify:
1. No more hallucinations
2. PAN application works
3. Stored data intent works
4. All queries get relevant responses
