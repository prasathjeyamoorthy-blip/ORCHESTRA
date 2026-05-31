# Quick Start - PAN Assistant AI Agent Memory

## 🚀 Get Started in 3 Steps

### Step 1: Restart Backend Server
```bash
cd auth-app/backend
# Stop current server (Ctrl+C if running)
node server.js
```

**Expected output**:
```
✅ Redis (Upstash) enabled
Server running on port 5000
```

### Step 2: Restart RAG Server (Fix user_id error)
```bash
cd pan-rag
# Stop current server (Ctrl+C if running)
python main.py
```

**Expected output**:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 3: Test It!
Open your frontend and:
1. Login to your account
2. Send a message: "I want to apply for PAN"
3. Send another message: "My name is Rajesh Kumar"
4. Check memory: `GET http://localhost:5000/api/chat/memory`

**Expected response**:
```json
{
  "summary": "",
  "preferences": {},
  "messageCount": 4
}
```

## ✅ That's It!

Your PAN Assistant now has persistent memory! 

## 🎯 What Works Now

✅ **Messages are saved** to Redis (30-day TTL)
✅ **Memory persists** across logout/login
✅ **System prompt** is sent to RAG (includes memory context)
✅ **Memory API** available at `/api/chat/memory`
✅ **All existing features** still work (RAG flow, documents, etc.)

## ⚠️ What Needs RAG Updates (Optional)

The following features will work once you add endpoints to RAG:

🔄 **Automatic Summarization** (after 20 messages)
- Needs: `POST /api/summarize` endpoint in RAG
- Status: Silently skipped if endpoint doesn't exist

🔄 **Preference Extraction** (every 5 messages)
- Needs: `POST /api/extract-preferences` endpoint in RAG
- Status: Silently skipped if endpoint doesn't exist

🔄 **System Prompt Usage** (AI uses memory context)
- Needs: RAG to accept and use `system_prompt` field
- Status: Sent but ignored if RAG doesn't support it

See `RAG_SERVER_UPDATES_NEEDED.md` for implementation details.

## 🧪 Quick Test Commands

### Check Memory
```bash
curl -X GET http://localhost:5000/api/chat/memory \
  -H "Cookie: access_token=YOUR_TOKEN"
```

### Clear Memory
```bash
curl -X DELETE http://localhost:5000/api/chat/memory \
  -H "Cookie: access_token=YOUR_TOKEN"
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

## 📚 Full Documentation

- `AGENT_MEMORY_IMPLEMENTATION_SUMMARY.md` - Complete overview
- `AGENT_MEMORY_UPGRADE_COMPLETE.md` - Technical details
- `AGENT_MEMORY_TESTING_GUIDE.md` - Testing scenarios
- `RAG_SERVER_UPDATES_NEEDED.md` - RAG server changes
- `SERVER_RESTART_REQUIRED.md` - user_id error fix

## 🐛 Troubleshooting

### Memory not saving?
- Check Redis connection in `.env` (UPSTASH_REDIS_REST_URL and TOKEN)
- Check backend logs for `[agent-memory]` errors
- Verify user is logged in (has valid access_token cookie)

### user_id error still happening?
- Make sure you restarted the RAG server
- Check RAG server logs for the error
- Verify the fix is in `pan-rag/agent/receptionist.py` line 262

### Chat not working?
- Check both servers are running (backend on 5000, RAG on 8000)
- Check browser console for errors
- Check backend logs for errors

## 💡 Pro Tips

1. **Test with Redis CLI**: `redis-cli KEYS "chat:history:*"`
2. **Monitor logs**: Look for `[agent-memory]` messages
3. **Check Upstash dashboard**: Monitor Redis usage
4. **Use browser DevTools**: Check Network tab for API calls
5. **Test guest mode**: Disable Redis to verify graceful degradation

## 🎉 Success!

If you can:
- ✅ Send messages and see them in memory
- ✅ Call GET /api/chat/memory and see messageCount
- ✅ Logout/login and memory persists
- ✅ Clear memory with DELETE /api/chat/memory

Then everything is working! 🎊

---

**Need Help?** Check the full documentation or review the code in `auth-app/backend/routes/chat.js`
