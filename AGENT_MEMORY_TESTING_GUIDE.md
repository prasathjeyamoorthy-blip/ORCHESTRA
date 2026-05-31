# PAN Assistant AI Agent Memory - Testing Guide

## Prerequisites
1. Backend server running: `cd auth-app/backend && node server.js`
2. RAG server running: `cd pan-rag && python main.py`
3. Redis (Upstash) configured in `.env`
4. User logged in (has valid access_token cookie)

## Test Scenarios

### 1. Basic Memory Storage
**Goal**: Verify messages are saved to Redis

**Steps**:
1. Send a message: "I want to apply for a PAN card"
2. Check Redis for key: `chat:history:{userId}`
3. Verify it contains the user message

**Expected**:
```json
[
  {
    "role": "user",
    "content": "I want to apply for a PAN card",
    "ts": "2026-05-01T..."
  },
  {
    "role": "assistant",
    "content": "...",
    "ts": "2026-05-01T..."
  }
]
```

### 2. Memory Retrieval
**Goal**: Verify memory is loaded on subsequent requests

**Steps**:
1. Send 3-4 messages in a conversation
2. Call `GET /api/chat/memory`
3. Verify response contains summary, preferences, messageCount

**Expected**:
```json
{
  "summary": "",
  "preferences": {},
  "messageCount": 8
}
```

### 3. Summarization Trigger
**Goal**: Verify summarization happens after 20 messages

**Steps**:
1. Send 21 messages in a conversation
2. Wait 5 seconds (summarization is async)
3. Check Redis for key: `chat:summary:{userId}`
4. Verify it contains a summary
5. Check `chat:history:{userId}` - should be trimmed to 10 messages

**Expected**:
- Summary exists in Redis
- History length = 10 (trimmed from 21)

### 4. Preference Extraction
**Goal**: Verify preferences are extracted every 5 messages

**Steps**:
1. Send messages with personal info:
   - "My name is Rajesh Kumar"
   - "I live in Mumbai"
   - "My PAN is ABCDE1234F"
   - "I prefer Hindi"
   - "I need to link my Aadhaar"
2. Wait 5 seconds (extraction is async)
3. Call `GET /api/chat/memory`
4. Verify preferences are populated

**Expected**:
```json
{
  "preferences": {
    "name": "Rajesh Kumar",
    "city": "Mumbai",
    "pan": "ABCDE1234F",
    "preferredLanguage": "Hindi",
    "aadhaarLinked": "no"
  }
}
```

### 5. Memory Persistence
**Goal**: Verify memory survives logout/login

**Steps**:
1. Send several messages
2. Logout
3. Login again
4. Call `GET /api/chat/memory`
5. Verify memory is still there

**Expected**:
- Memory persists across sessions
- TTL = 30 days

### 6. Memory Clearing
**Goal**: Verify memory can be cleared

**Steps**:
1. Send several messages
2. Call `DELETE /api/chat/memory`
3. Call `GET /api/chat/memory`
4. Verify memory is empty

**Expected**:
```json
{
  "summary": "",
  "preferences": {},
  "messageCount": 0
}
```

### 7. Guest Mode (No Redis)
**Goal**: Verify graceful degradation when Redis is unavailable

**Steps**:
1. Stop Redis or set invalid credentials
2. Send a message
3. Verify chat still works (no crash)
4. Verify response is returned normally

**Expected**:
- Chat works without memory
- No errors in console
- Response is returned

### 8. System Prompt Integration
**Goal**: Verify system prompt is sent to RAG

**Steps**:
1. Send a message
2. Check RAG server logs
3. Verify `system_prompt` field is received

**Expected** (in RAG request):
```json
{
  "question": "...",
  "session_id": "...",
  "user_id": "...",
  "user_context": "...",
  "account_email": "...",
  "system_prompt": "You are PAN Assistant..."
}
```

### 9. Existing Flow Preservation
**Goal**: Verify RAG flow still works

**Steps**:
1. Start PAN application flow
2. Answer guided questions (submission_mode, delivery_mode, etc.)
3. Confirm details
4. Upload documents
5. Verify entire flow completes successfully

**Expected**:
- All guided questions appear
- Field buttons work
- Document upload works
- Flow confirmation works
- Profile is saved

### 10. Long Conversation
**Goal**: Verify memory management over long conversation

**Steps**:
1. Send 50 messages
2. Verify summarization happens multiple times
3. Verify preference extraction happens every 5 messages
4. Verify history is trimmed appropriately
5. Call `GET /api/chat/memory`

**Expected**:
- Summary contains multiple conversation summaries
- Preferences are accumulated
- History length ≤ 20 messages

## Manual Testing with cURL

### Get Memory
```bash
curl -X GET http://localhost:5000/api/chat/memory \
  -H "Cookie: access_token=YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

### Clear Memory
```bash
curl -X DELETE http://localhost:5000/api/chat/memory \
  -H "Cookie: access_token=YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

### Send Message
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Cookie: access_token=YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want to apply for PAN",
    "session_id": "YOUR_SESSION_ID"
  }'
```

## Redis Inspection

### Check Memory Keys
```bash
# Using redis-cli (if local Redis)
redis-cli KEYS "chat:history:*"
redis-cli KEYS "chat:summary:*"
redis-cli KEYS "chat:preferences:*"

# Get specific key
redis-cli GET "chat:history:{userId}"
```

### Using Upstash Console
1. Go to Upstash dashboard
2. Select your Redis instance
3. Use Data Browser
4. Search for keys: `chat:history:*`, `chat:summary:*`, `chat:preferences:*`

## Debugging

### Enable Debug Logging
Add to `chat.js`:
```javascript
console.log('[agent-memory] Loaded memory:', agentMemory);
console.log('[agent-memory] System prompt:', agentSystemPrompt);
console.log('[agent-memory] History length:', agentMemory.history.length);
```

### Check Backend Logs
Look for these log messages:
- `[agent-memory] Saved summary for user ...`
- `[agent-memory] Updated preferences for user ...`
- `[agent-memory] loadAgentMemory error: ...`
- `[agent-memory] Summarization failed: ...`
- `[agent-memory] Preference extraction failed: ...`

### Common Issues

#### Memory not saving
- Check Redis connection (UPSTASH_REDIS_REST_URL and TOKEN in .env)
- Check Redis logs for errors
- Verify user is authenticated (has valid access_token)

#### Summarization not working
- Check RAG server has `/api/summarize` endpoint
- Check RAG server logs for errors
- Verify summarization is triggered (history > 20)

#### Preference extraction not working
- Check RAG server has `/api/extract-preferences` endpoint
- Check RAG server logs for errors
- Verify extraction is triggered (every 5 messages)

#### System prompt not used
- Check RAG server accepts `system_prompt` field
- Check RAG server logs to see if field is received
- Update RAG to use system_prompt in LLM call

## Performance Monitoring

### Response Time
- Memory load should add < 50ms to response time
- Summarization/extraction should not block response
- Check logs for timing: `⏱  [chat] session=... intent=... 0.45s`

### Redis Performance
- Monitor Redis latency in Upstash dashboard
- Check for slow queries
- Verify TTL is working (keys expire after 30 days)

### Memory Usage
- Monitor Redis memory usage
- Each user should use ~10-50KB (depending on conversation length)
- 1000 users ≈ 10-50MB

## Success Criteria

✅ Messages are saved to Redis after each turn
✅ Memory is loaded on subsequent requests
✅ Summarization triggers after 20 messages
✅ Preference extraction triggers every 5 messages
✅ Memory persists across logout/login
✅ Memory can be cleared via DELETE endpoint
✅ Chat works without Redis (guest mode)
✅ Existing RAG flow is preserved
✅ No performance degradation
✅ No errors in logs

## Next Steps After Testing

1. **Add RAG endpoints** for summarization and preference extraction
2. **Update RAG** to use system_prompt field
3. **Add frontend UI** to display/manage memory
4. **Monitor production** for memory usage and performance
5. **Tune TTL** based on usage patterns
6. **Add analytics** to track memory effectiveness
