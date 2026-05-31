# PAN Assistant AI Agent Memory - Deployment Checklist

## Pre-Deployment Checklist

### ✅ Code Review
- [x] All new functions added to `auth-app/backend/routes/chat.js`
- [x] Memory key functions defined (memoryHistoryKey, memorySummaryKey, memoryPreferencesKey)
- [x] Memory management functions implemented (load, save, clear)
- [x] AI-powered operations implemented (summarization, preference extraction)
- [x] New API routes added (GET/DELETE /api/chat/memory)
- [x] Main chat route enhanced with memory integration
- [x] Error handling and fallbacks in place
- [x] Non-blocking operations for memory saves
- [x] Backward compatibility maintained

### ✅ Configuration
- [ ] Redis (Upstash) credentials in `.env`
  - `UPSTASH_REDIS_REST_URL=https://...`
  - `UPSTASH_REDIS_REST_TOKEN=...`
- [ ] Supabase credentials in `.env`
  - `SUPABASE_URL=https://...`
  - `SUPABASE_SERVICE_KEY=...`
- [ ] RAG server URL configured
  - `RAG_URL=http://localhost:8000` (or production URL)

### ✅ Dependencies
- [x] `@upstash/redis` installed
- [x] `@supabase/supabase-js` installed
- [x] No new dependencies required

## Deployment Steps

### Step 1: Backup Current Code
```bash
# Backup current chat.js
cp auth-app/backend/routes/chat.js auth-app/backend/routes/chat.js.backup

# Backup current receptionist.py (for user_id fix)
cp pan-rag/agent/receptionist.py pan-rag/agent/receptionist.py.backup
```

### Step 2: Verify Code Changes
```bash
# Check chat.js line count (should be ~1100 lines)
wc -l auth-app/backend/routes/chat.js

# Check for new memory functions
grep -n "loadAgentMemory\|saveAgentHistory\|clearAgentMemory" auth-app/backend/routes/chat.js

# Check for new routes
grep -n "router\.(get|delete)('/memory'" auth-app/backend/routes/chat.js
```

### Step 3: Test Configuration
```bash
# Test Redis connection
node -e "
const { Redis } = require('@upstash/redis');
const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL,
  token: process.env.UPSTASH_REDIS_REST_TOKEN
});
redis.ping().then(() => console.log('✅ Redis connected')).catch(e => console.error('❌ Redis error:', e));
"

# Test Supabase connection
node -e "
const { createClient } = require('@supabase/supabase-js');
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);
supabase.from('chat_sessions').select('count').limit(1).then(() => console.log('✅ Supabase connected')).catch(e => console.error('❌ Supabase error:', e));
"
```

### Step 4: Restart Backend Server
```bash
cd auth-app/backend

# Stop current server
# (Ctrl+C if running in terminal, or kill process)

# Start server
node server.js

# Or with PM2
pm2 restart backend

# Or with systemd
sudo systemctl restart pan-backend
```

**Expected output**:
```
✅ Redis (Upstash) enabled
Server running on port 5000
```

### Step 5: Restart RAG Server (Fix user_id error)
```bash
cd pan-rag

# Stop current server
# (Ctrl+C if running in terminal, or kill process)

# Start server
python main.py

# Or with PM2
pm2 restart rag-server

# Or with systemd
sudo systemctl restart pan-rag
```

**Expected output**:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 6: Smoke Test
```bash
# Test backend health
curl http://localhost:5000/health

# Test RAG health
curl http://localhost:8000/health

# Test memory endpoint (requires auth token)
curl -X GET http://localhost:5000/api/chat/memory \
  -H "Cookie: access_token=YOUR_TOKEN"
```

## Post-Deployment Testing

### Test 1: Basic Memory Storage
- [ ] Login to frontend
- [ ] Send a message
- [ ] Call GET /api/chat/memory
- [ ] Verify messageCount > 0

### Test 2: Memory Persistence
- [ ] Send several messages
- [ ] Logout
- [ ] Login again
- [ ] Call GET /api/chat/memory
- [ ] Verify memory is still there

### Test 3: Memory Clearing
- [ ] Call DELETE /api/chat/memory
- [ ] Call GET /api/chat/memory
- [ ] Verify messageCount = 0

### Test 4: Existing Flow
- [ ] Start PAN application flow
- [ ] Answer guided questions
- [ ] Confirm details
- [ ] Verify flow completes successfully

### Test 5: Error Handling
- [ ] Temporarily disable Redis
- [ ] Send a message
- [ ] Verify chat still works (guest mode)
- [ ] Re-enable Redis

## Monitoring

### Backend Logs
Watch for these messages:
```bash
tail -f auth-app/backend/logs/app.log | grep "agent-memory"
```

Expected log messages:
- `[agent-memory] Loaded memory: ...`
- `[agent-memory] Saved summary for user ...`
- `[agent-memory] Updated preferences for user ...`
- `[agent-memory] loadAgentMemory error: ...` (only if Redis fails)

### Redis Monitoring
- [ ] Check Upstash dashboard for memory usage
- [ ] Verify keys are being created: `chat:history:*`, `chat:summary:*`, `chat:preferences:*`
- [ ] Monitor latency (should be < 50ms)
- [ ] Check TTL is working (keys expire after 30 days)

### Performance Monitoring
- [ ] Check response times (should be < 500ms)
- [ ] Monitor memory usage (backend process)
- [ ] Check CPU usage (should be < 50%)
- [ ] Monitor error rate (should be < 1%)

## Rollback Plan

If something goes wrong:

### Step 1: Restore Backup
```bash
# Restore chat.js
cp auth-app/backend/routes/chat.js.backup auth-app/backend/routes/chat.js

# Restore receptionist.py
cp pan-rag/agent/receptionist.py.backup pan-rag/agent/receptionist.py
```

### Step 2: Restart Servers
```bash
# Restart backend
cd auth-app/backend
node server.js

# Restart RAG
cd pan-rag
python main.py
```

### Step 3: Verify Rollback
```bash
# Test chat functionality
curl -X POST http://localhost:5000/api/chat \
  -H "Cookie: access_token=YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"test","session_id":"test-session"}'
```

## Production Deployment

### Additional Steps for Production

1. **Environment Variables**
   - [ ] Set production Redis URL
   - [ ] Set production Supabase URL
   - [ ] Set production RAG URL
   - [ ] Enable HTTPS

2. **Security**
   - [ ] Enable rate limiting
   - [ ] Enable CORS for production domain only
   - [ ] Use secure cookies (httpOnly, secure, sameSite)
   - [ ] Enable request logging

3. **Monitoring**
   - [ ] Set up error tracking (Sentry, etc.)
   - [ ] Set up performance monitoring (New Relic, etc.)
   - [ ] Set up uptime monitoring (Pingdom, etc.)
   - [ ] Set up log aggregation (Loggly, etc.)

4. **Scaling**
   - [ ] Configure load balancer
   - [ ] Set up auto-scaling
   - [ ] Configure Redis connection pooling
   - [ ] Optimize Supabase queries

5. **Backup**
   - [ ] Set up automated backups for Supabase
   - [ ] Set up Redis persistence (Upstash handles this)
   - [ ] Document recovery procedures

## Success Criteria

✅ Backend server starts without errors
✅ RAG server starts without errors
✅ Redis connection successful
✅ Supabase connection successful
✅ Memory API endpoints respond correctly
✅ Messages are saved to Redis
✅ Memory persists across sessions
✅ Existing RAG flow works
✅ No errors in logs
✅ Response times < 500ms
✅ Error rate < 1%

## Known Issues & Workarounds

### Issue 1: user_id Error
**Symptom**: `NameError: name 'user_id' is not defined` at line 550
**Solution**: Restart RAG server (fix is already in code)
**Status**: ✅ Fixed

### Issue 2: Summarization Not Working
**Symptom**: No summary generated after 20 messages
**Solution**: Add `/api/summarize` endpoint to RAG server
**Status**: ⚠️ Optional (silently skipped if endpoint doesn't exist)

### Issue 3: Preference Extraction Not Working
**Symptom**: Preferences not populated
**Solution**: Add `/api/extract-preferences` endpoint to RAG server
**Status**: ⚠️ Optional (silently skipped if endpoint doesn't exist)

### Issue 4: System Prompt Not Used
**Symptom**: AI doesn't use memory context
**Solution**: Update RAG to accept and use `system_prompt` field
**Status**: ⚠️ Optional (backward compatible)

## Support Contacts

- **Backend Issues**: Check `auth-app/backend/routes/chat.js`
- **RAG Issues**: Check `pan-rag/agent/receptionist.py`
- **Redis Issues**: Check Upstash dashboard
- **Supabase Issues**: Check Supabase dashboard

## Documentation

- `QUICK_START_AGENT_MEMORY.md` - Quick start guide
- `AGENT_MEMORY_IMPLEMENTATION_SUMMARY.md` - Complete overview
- `AGENT_MEMORY_UPGRADE_COMPLETE.md` - Technical details
- `AGENT_MEMORY_TESTING_GUIDE.md` - Testing scenarios
- `AGENT_MEMORY_ARCHITECTURE.md` - Architecture diagram
- `RAG_SERVER_UPDATES_NEEDED.md` - RAG server changes
- `SERVER_RESTART_REQUIRED.md` - user_id error fix

---

**Deployment Date**: _____________
**Deployed By**: _____________
**Deployment Status**: ⬜ Pending / ⬜ In Progress / ⬜ Complete
**Rollback Required**: ⬜ Yes / ⬜ No
**Notes**: _____________________________________________
