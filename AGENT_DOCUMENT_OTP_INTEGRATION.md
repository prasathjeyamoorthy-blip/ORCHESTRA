# Agent Document Access with OTP Verification

## Overview
This implementation adds **OTP-based security** for agent access to user-uploaded documents. When the agent needs to access documents for processing the PAN application, the user must verify their identity via SMS OTP.

## Security Flow

### 1. User Uploads Documents
- User uploads documents (Aadhaar, photos, etc.) via the upload panel
- Documents are stored in Supabase Storage
- Metadata is saved in `user_files` table

### 2. Agent Requests Document Access
When the agent needs to process documents:
1. Agent calls `request_user_documents(user_token, session_id)`
2. System sends 6-digit OTP to user's registered phone via **Message Central**
3. User receives SMS with OTP
4. Agent prompts user: "I've sent an OTP to your phone. Please provide it to continue."

### 3. User Provides OTP
1. User types the 6-digit OTP in chat
2. Agent calls `verify_user_documents_otp(user_token, session_id, otp)`
3. System verifies OTP with Message Central
4. If valid: Agent gets access to documents for 30 minutes
5. If invalid: User gets remaining attempts (max 5 attempts)

### 4. Agent Accesses Documents
- Agent can now download and process documents
- Access is logged in `file_access_logs` table
- Access expires after 30 minutes for security

## API Endpoints

### Agent Document Access

### 1. Request OTP for Agent Access
```http
POST /api/uploads/agent/request-access
Authorization: Bearer <user_token>
```

**Response (Success):**
```json
{
  "message": "OTP sent to your registered phone number.",
  "phone_last_4": "1234",
  "expires_in_minutes": 10,
  "file_count": 3
}
```

**Response (No Phone):**
```json
{
  "error": "No phone number registered. Please add a phone number to your profile first.",
  "requires_phone": true
}
```

**Response (No Documents):**
```json
{
  "error": "No documents found for this user."
}
```

### 2. Verify OTP and Get Document Access
```http
POST /api/uploads/agent/verify-and-access
Authorization: Bearer <user_token>
Content-Type: application/json

{
  "otp": "123456"
}
```

**Response (Success):**
```json
{
  "message": "OTP verified successfully. Agent can now access your documents.",
  "verified": true,
  "documents": [
    {
      "id": "uuid",
      "file_name": "aadhaar.pdf",
      "file_size": 123456,
      "mime_type": "application/pdf",
      "uploaded_at": "2024-01-05T10:00:00Z",
      "encrypted": false
    }
  ],
  "access_granted_at": "2024-01-05T10:00:00Z",
  "access_expires_at": "2024-01-05T10:30:00Z"
}
```

**Response (Invalid OTP):**
```json
{
  "error": "Invalid OTP. 3 attempt(s) remaining.",
  "remaining_attempts": 3
}
```

**Response (Too Many Attempts):**
```json
{
  "error": "Too many failed attempts. Please request a new OTP."
}
```

### 3. Get Document Content (After OTP Verification)
```http
GET /api/uploads/agent/document/:id
Authorization: Bearer <user_token>
```

**Response (Success):**
- Binary file content with appropriate Content-Type header

**Response (OTP Not Verified):**
```json
{
  "error": "OTP verification required or expired. Please verify OTP first.",
  "requires_otp": true
}
```

## Agent Integration

### Python Module: `agent/document_access.py`

#### Class: `DocumentAccessManager`

```python
from agent.document_access import DocumentAccessManager

# Initialize with user token
manager = DocumentAccessManager(user_token)

# Request OTP
result = manager.request_otp()
if result["success"]:
    print(f"OTP sent to phone ending in {result['phone_last_4']}")
    print(f"You have {result['file_count']} documents")

# Verify OTP
result = manager.verify_otp("123456")
if result["success"]:
    print("Access granted!")
    documents = result["documents"]
    
    # Get document content
    for doc in documents:
        content = manager.get_document(doc["id"])
        if content:
            # Process document content
            pass
```

#### Helper Functions

```python
from agent.document_access import (
    request_document_access,
    verify_document_access,
    get_user_documents
)

# Request OTP
result = request_document_access(user_token)

# Verify OTP
result = verify_document_access(user_token, "123456")

# Get document
content = get_user_documents(user_token, document_id)
```

### Receptionist Agent Integration

The receptionist agent has three new functions:

#### 1. `request_user_documents(user_token, session_id)`
Call this when agent needs to access documents:

```python
response = request_user_documents(user_token, session_id)
# Returns dict with OTP request status and user-friendly message
```

#### 2. `verify_user_documents_otp(user_token, session_id, otp)`
Call this when user provides OTP:

```python
response = verify_user_documents_otp(user_token, session_id, "123456")
# Returns dict with verification status and document list
```

#### 3. `check_document_access(session_id)`
Check if agent still has valid access:

```python
has_access = check_document_access(session_id)
if not has_access:
    # Request OTP again
    pass
```

## Agent Flow Example

### Scenario: User completes document upload

```
User: "I've uploaded all my documents"

Agent: [Detects documents uploaded, needs to access them]
       [Calls request_user_documents()]

Agent: "🔐 Document Access Verification Required

       I need to access your uploaded documents to process your PAN application.
       For security, I've sent a 6-digit OTP to your registered phone number (ending in 1234).
       
       Please provide the OTP to continue.
       
       📱 OTP expires in 10 minutes
       📄 Documents to access: 3 file(s)"

User: "123456"

Agent: [Calls verify_user_documents_otp(token, session, "123456")]

Agent: "✅ OTP Verified Successfully!

       I now have access to your documents and can process your PAN application.
       
       Documents available (3):
       - aadhaar.pdf (application/pdf, 123456 bytes)
       - photo.jpg (image/jpeg, 45678 bytes)
       - signature.png (image/png, 12345 bytes)
       
       🔒 Access expires in 30 minutes for security.
       
       Let me review your documents and continue with the application..."

Agent: [Processes documents, extracts information, continues with PAN application]
```

### Scenario: Invalid OTP

```
User: "999999"

Agent: "❌ Invalid OTP

       The OTP you provided is incorrect. Please check and try again.
       
       ⚠️ 4 attempt(s) remaining."

User: "123456"

Agent: "✅ OTP Verified Successfully! ..."
```

### Scenario: Too Many Failed Attempts

```
User: [Enters wrong OTP 5 times]

Agent: "🚫 Too Many Failed Attempts

       You've exceeded the maximum number of OTP verification attempts.
       Please request a new OTP."

User: "Send new OTP"

Agent: [Calls request_user_documents() again]
       "🔐 Document Access Verification Required ..."
```

### Scenario: No Phone Number

```
Agent: [Calls request_user_documents()]

Agent: "⚠️ Phone Number Required

       To access your documents securely, you need to have a phone number registered.
       Please add your phone number to your profile first.
       
       Would you like me to guide you through adding a phone number?"

User: "Yes, help me add phone"

Agent: "Sure! Please provide your phone number in the format +91XXXXXXXXXX"
```

## Database Schema

### `otp_verifications` Table

```sql
CREATE TABLE otp_verifications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  phone TEXT,
  verification_id TEXT,              -- Message Central verification ID
  purpose TEXT NOT NULL,              -- 'agent_document_access', 'file_access', etc.
  verified BOOLEAN DEFAULT FALSE,
  attempts INTEGER DEFAULT 0,
  last_attempt_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  verified_at TIMESTAMPTZ
);
```

### `file_access_logs` Table

```sql
CREATE TABLE file_access_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  file_id UUID NOT NULL REFERENCES user_files(id),
  access_type TEXT NOT NULL,          -- 'agent_access', 'agent_download', 'view', 'download'
  otp_verified BOOLEAN DEFAULT FALSE,
  ip_address TEXT,
  user_agent TEXT,
  success BOOLEAN DEFAULT FALSE,
  error_message TEXT,
  accessed_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Security Features

### 1. OTP Expiry
- OTPs expire after **10 minutes**
- User must request new OTP after expiry

### 2. Access Expiry
- Document access expires after **30 minutes**
- Agent must request new OTP after expiry

### 3. Rate Limiting
- Max **5 verification attempts** per OTP
- After 5 failed attempts, OTP is invalidated
- User must request new OTP

### 4. Audit Logging
- All OTP requests logged with timestamp
- All verification attempts logged (success/failure)
- All document access logged with:
  - User ID
  - File ID
  - Access type (agent_access, agent_download)
  - OTP verification status
  - IP address
  - Timestamp

### 5. Single-Use OTPs
- Each OTP can only be verified once
- After successful verification, OTP is marked as `verified = true`
- Prevents replay attacks

## Message Central Integration

### OTP Service: Message Central
- **Provider**: Message Central CPaaS
- **Base URL**: `https://cpaas.messagecentral.com`
- **Method**: SMS OTP (6-digit codes)
- **Country**: India (+91)

### Environment Variables Required

```env
MC_CUSTOMER_ID=C-7E9729DC8FF245C
MC_PASSWORD_B64=RGV2YWRwcGQxQA==
```

### OTP Flow with Message Central

1. **Get Auth Token**
   ```
   GET /auth/v1/authentication/token
   ?customerId={MC_CUSTOMER_ID}
   &key={MC_PASSWORD_B64}
   &scope=NEW
   &country=91
   ```

2. **Send OTP**
   ```
   POST /verification/v3/send
   ?countryCode=91
   &flowType=SMS
   &mobileNumber={10_digit_number}
   &otpLength=6
   
   Headers: authToken: {token}
   ```

3. **Verify OTP**
   ```
   GET /verification/v3/validateOtp
   ?verificationId={verification_id}
   &code={6_digit_otp}
   
   Headers: authToken: {token}
   ```

## Testing

### 1. Test OTP Request

```bash
# Request OTP for agent access
curl -X POST http://localhost:4000/api/uploads/agent/request-access \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response:**
```json
{
  "message": "OTP sent to your registered phone number.",
  "phone_last_4": "1234",
  "expires_in_minutes": 10,
  "file_count": 3
}
```

### 2. Test OTP Verification

```bash
# Verify OTP
curl -X POST http://localhost:4000/api/uploads/agent/verify-and-access \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"otp":"123456"}'
```

**Expected Response:**
```json
{
  "message": "OTP verified successfully. Agent can now access your documents.",
  "verified": true,
  "documents": [...],
  "access_granted_at": "2024-01-05T10:00:00Z",
  "access_expires_at": "2024-01-05T10:30:00Z"
}
```

### 3. Test Document Access

```bash
# Get document content (after OTP verification)
curl -X GET http://localhost:4000/api/uploads/agent/document/FILE_ID \
  -H "Authorization: Bearer YOUR_TOKEN" \
  --output document.pdf
```

### 4. Test Python Integration

```python
from agent.document_access import DocumentAccessManager

# Initialize
manager = DocumentAccessManager(user_token)

# Request OTP
result = manager.request_otp()
print(result)

# User receives SMS, provides OTP
otp = input("Enter OTP: ")

# Verify OTP
result = manager.verify_otp(otp)
print(result)

# Get documents
if result["success"]:
    for doc in result["documents"]:
        content = manager.get_document(doc["id"])
        print(f"Downloaded {doc['file_name']}: {len(content)} bytes")
```

## Deployment Checklist

- [x] Enable OTP feature in `auth-app/backend/routes/otp.js`
- [x] Add Message Central credentials to `.env`
- [x] Create agent document access endpoints in `uploads.js`
- [x] Create Python document access module
- [x] Integrate OTP verification into receptionist agent
- [ ] Apply database migration for `otp_verifications` table
- [ ] Test OTP sending with real phone number
- [ ] Test OTP verification flow
- [ ] Test agent document access flow
- [ ] Monitor Message Central usage and costs
- [ ] Set up error alerting for failed OTP sends

## Troubleshooting

### Issue: OTP Not Received

**Possible Causes:**
1. User has no phone number registered
2. Message Central credentials incorrect
3. Phone number format invalid (must be +91XXXXXXXXXX)

**Solutions:**
1. Check user profile for phone number
2. Verify `MC_CUSTOMER_ID` and `MC_PASSWORD_B64` in `.env`
3. Validate phone number format

### Issue: OTP Verification Fails

**Possible Causes:**
1. OTP expired (>10 minutes)
2. Wrong OTP code
3. Too many failed attempts

**Solutions:**
1. Request new OTP
2. Double-check OTP code
3. Wait and request new OTP

### Issue: Agent Cannot Access Documents

**Possible Causes:**
1. OTP not verified
2. Access expired (>30 minutes)
3. No documents uploaded

**Solutions:**
1. Verify OTP first
2. Request new OTP
3. Upload documents first

## Cost Considerations

**Message Central Pricing** (approximate):
- SMS OTP: ₹0.10 - ₹0.20 per SMS
- Estimated cost per PAN application: ₹0.10 - ₹0.40 (1-2 OTPs)

**Monthly Estimates:**
- 100 applications: ₹10-40
- 1,000 applications: ₹100-400
- 10,000 applications: ₹1,000-4,000

## Conclusion

The OTP-based document access system provides:

✅ **Two-Factor Authentication** for agent document access
✅ **SMS Delivery** via Message Central
✅ **Time-Limited Access** (30 minutes)
✅ **Rate Limiting** to prevent abuse
✅ **Audit Logging** for compliance
✅ **User Consent** before agent accesses documents

This ensures maximum security and user privacy while allowing the agent to process PAN applications efficiently.
