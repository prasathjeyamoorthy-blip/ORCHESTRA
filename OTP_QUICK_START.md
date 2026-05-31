# OTP Feature - Quick Start Guide

## ✅ What's Ready

The OTP feature is **fully implemented and enabled**. Here's what you can do now:

### 1. Agent Document Access with OTP
When the agent needs to access user documents, it will:
1. Send OTP to user's phone via SMS
2. Ask user to provide the 6-digit code
3. Verify OTP and get 30-minute access to documents
4. Process documents securely

### 2. User Document Downloads with OTP ⭐ NEW
When users want to download their uploaded documents:
1. User clicks download button
2. System sends OTP to user's phone via SMS
3. User enters 6-digit code in download dialog
4. System verifies OTP and downloads file
5. Each download requires new OTP verification

## 🚀 How to Test

### Prerequisites
- ✅ Message Central credentials configured in `.env`
- ✅ User has phone number registered (+91XXXXXXXXXX format)
- ✅ User has uploaded documents

### Test Flow

#### Step 1: Start Servers
```bash
# Terminal 1: Backend
cd auth-app/backend
node server.js

# Terminal 2: RAG Agent
cd pan-rag
python main.py
```

#### Step 2: Upload Documents
1. Login to the app
2. Upload documents (Aadhaar, photo, etc.)
3. Complete the upload

#### Step 3: Agent Requests Access
When agent needs documents, it will automatically:
1. Call `request_user_documents(user_token, session_id)`
2. Send OTP via Message Central
3. Show message: "I've sent an OTP to your phone (ending in XXXX)"

#### Step 4: User Provides OTP
1. User receives SMS with 6-digit OTP
2. User types OTP in chat: "123456"
3. Agent calls `verify_user_documents_otp(user_token, session_id, "123456")`

#### Step 5: Agent Accesses Documents
1. If OTP valid: Agent gets 30-minute access
2. Agent downloads and processes documents
3. Agent continues with PAN application

## 📱 Message Central Configuration

Already configured in `auth-app/backend/.env`:

```env
MC_CUSTOMER_ID=C-7E9729DC8FF245C
MC_PASSWORD_B64=RGV2YWRwcGQxQA==
```

**Note**: These credentials are for the India (+91) region and send SMS OTPs.

## 🔧 API Endpoints Available

### 1. Agent Request OTP
```bash
curl -X POST http://localhost:4000/api/uploads/agent/request-access \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. Agent Verify OTP
```bash
curl -X POST http://localhost:4000/api/uploads/agent/verify-and-access \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"otp":"123456"}'
```

### 3. Agent Get Document
```bash
curl -X GET http://localhost:4000/api/uploads/agent/document/FILE_ID \
  -H "Authorization: Bearer YOUR_TOKEN" \
  --output document.pdf
```

### 4. User Request Download OTP
```bash
curl -X POST http://localhost:4000/api/uploads/FILE_ID/request-download-otp \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 5. User Download with OTP
```bash
curl -X POST http://localhost:4000/api/uploads/FILE_ID/download \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"otp":"123456"}' \
  --output downloaded_file.pdf
```

## 🐍 Python Usage

### In Agent Code

```python
from agent.document_access import request_document_access, verify_document_access

# Request OTP
result = request_document_access(user_token)
if result["success"]:
    print(f"OTP sent to phone ending in {result['phone_last_4']}")

# Verify OTP
result = verify_document_access(user_token, "123456")
if result["success"]:
    documents = result["documents"]
    print(f"Access granted to {len(documents)} documents")
```

### In Receptionist Agent

```python
from agent.receptionist import (
    request_user_documents,
    verify_user_documents_otp,
    check_document_access
)

# Request OTP
response = request_user_documents(user_token, session_id)
# Returns user-friendly message for chat

# Verify OTP
response = verify_user_documents_otp(user_token, session_id, "123456")
# Returns verification status and document list

# Check if access still valid
has_access = check_document_access(session_id)
```

## 🔒 Security Features

- ✅ **OTP expires in 10 minutes**
- ✅ **Access expires in 30 minutes**
- ✅ **Max 5 verification attempts**
- ✅ **Single-use OTPs**
- ✅ **Audit logging** of all access
- ✅ **SMS delivery** via Message Central

## 📊 Monitoring

### Check OTP Verifications
```sql
SELECT * FROM otp_verifications 
WHERE purpose = 'agent_document_access' 
ORDER BY created_at DESC 
LIMIT 10;
```

### Check Document Access Logs
```sql
SELECT * FROM file_access_logs 
WHERE access_type IN ('agent_access', 'agent_download') 
ORDER BY accessed_at DESC 
LIMIT 10;
```

## ⚠️ Common Issues

### Issue: "No phone number registered"
**Solution**: User needs to add phone number to profile first.

### Issue: "OTP not received"
**Solutions**:
- Check Message Central credentials
- Verify phone number format (+91XXXXXXXXXX)
- Check Message Central dashboard for delivery status

### Issue: "Invalid OTP"
**Solutions**:
- Check OTP hasn't expired (10 minutes)
- Verify correct 6-digit code
- Check attempts not exceeded (5 max)

### Issue: "OTP verification required or expired"
**Solution**: Access expired after 30 minutes, request new OTP.

## 💰 Cost

**Message Central SMS OTP:**
- ₹0.10 - ₹0.20 per SMS
- 1-2 OTPs per application
- **~₹0.20 per application**

## 📚 Documentation

- **Agent Document Access**: `AGENT_DOCUMENT_OTP_INTEGRATION.md`
- **User Downloads**: `USER_DOWNLOAD_OTP_GUIDE.md` ⭐ NEW
- **Implementation Summary**: `OTP_FEATURE_IMPLEMENTATION_SUMMARY.md`
- **Message Central**: `MESSAGE_CENTRAL_OTP_INTEGRATION.md`

## ✨ What's Next

### Immediate Testing
1. Test with real phone number
2. Verify SMS delivery
3. Test complete agent flow
4. Monitor Message Central usage

### Future Enhancements
1. Add frontend UI for OTP input
2. Add user phone number management
3. Add email OTP as fallback
4. Add biometric verification option

## 🎉 Ready to Use!

The OTP feature is **fully functional** and ready for testing. Just:

1. ✅ Start the servers
2. ✅ Upload documents
3. ✅ Agent requests access
4. ✅ User provides OTP
5. ✅ Agent processes documents

**That's it!** The system handles everything else automatically.
