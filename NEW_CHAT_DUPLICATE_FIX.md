# New Chat Duplicate Questions Fix ✅

## Problem
When opening a new chat, the "Source of Income" checkbox options (and potentially other guided questions) were appearing multiple times on the screen.

## Root Cause
When creating a new chat session, the `guidedQuestion` state from the previous session was not being cleared. This caused guided questions from the old session to persist and appear in the new chat.

## Fix Applied
Added `setGuidedQuestion(null)` to the `createNewSession()` function to clear any guided questions when starting a new chat.

### File: `frontend/src/App.jsx`

**Before:**
```javascript
async function createNewSession() {
  try {
    const res = await fetch('/api/chat/sessions', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    })
    const data = await res.json()
    setSessions(prev => [data.session, ...prev])
    setSessionId(data.session.id)
    sessionIdRef.current = data.session.id
    setMessages([])
    setStarted(false)
  } catch { /* ignore */ }
}
```

**After:**
```javascript
async function createNewSession() {
  try {
    const res = await fetch('/api/chat/sessions', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    })
    const data = await res.json()
    setSessions(prev => [data.session, ...prev])
    setSessionId(data.session.id)
    sessionIdRef.current = data.session.id
    setMessages([])
    setGuidedQuestion(null)  // ← Clear guided questions from previous session
    setStarted(false)
  } catch { /* ignore */ }
}
```

## How It Works

The frontend has a special `guidedQuestion` state that holds the current guided question (with options) to display in a sliding panel. When you:

1. **Complete a flow in Session A** → `guidedQuestion` is set to show options
2. **Click "New Chat"** → Creates Session B
3. **Without the fix:** `guidedQuestion` from Session A still shows in Session B
4. **With the fix:** `guidedQuestion` is cleared, so Session B starts clean

## Testing

1. **Start a PAN application flow:**
   - Send a message to start the flow
   - Go through steps until you see guided questions (checkboxes/radio buttons)

2. **Create a new chat:**
   - Click the "New Chat" button
   - ✅ **Expected:** Clean slate, no guided questions visible
   - ❌ **Before fix:** Old guided questions would still appear

3. **Switch between sessions:**
   - Create multiple sessions
   - Switch between them
   - ✅ **Expected:** Each session shows only its own guided questions

## Note

The `switchSession()` function already had `setGuidedQuestion(null)` (line 716), so switching between existing sessions was working correctly. This fix ensures that creating a NEW session also clears the guided question state.

## Files Modified
- `frontend/src/App.jsx` (line 709)
