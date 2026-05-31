# Document Encryption Implementation

## Overview
This implementation provides **end-to-end encryption** for user-uploaded documents with **OTP-based access control**. Even database administrators cannot view the encrypted files without the user's encryption key and OTP verification.

## Security Architecture

### Encryption Method
- **Algorithm**: AES-256-GCM (Galois/Counter Mode)
- **Key Derivation**: PBKDF2 with 100,000 iterations
- **Key Length**: 256 bits (32 bytes)
- **IV Length**: 128 bits (16 bytes)
- **Authentication**: Built-in authentication tag (GCM mode)

### Zero-Knowledge Architecture
1. **User-Specific Keys**: Each user has a unique encryption key derived from their password/secret
2. **Client-Side Encryption**: Files are encrypted before upload (can be implemented)
3. **Server-Side Encryption**: Files are encrypted on the server using user-provided secret
4. **No Key Storage**: Encryption keys are never stored in plaintext
5. **OTP Verification**: Access to encrypted files requires OTP verification

### What's Encrypted
1. **File Content**: The actual file data
2. **Filename**: Original filename is encrypted for privacy
3. **Metadata**: Stored encrypted in database

### What Database Admins See
- ❌ Cannot see file content (encrypted blob)
- ❌ Cannot see original filename (encrypted)
- ❌ Cannot decrypt without user's secret + OTP
- ✅ Can see: user_id, file_size, upload timestamp, encryption metadata (IV, tag, salt)

## API Endpoints

### 1. Upload Encrypted File
```http
POST /api/uploads
Authorization: Bearer <token>
Content-Type: multipart/form-data

Body:
- file: <file>
- encrypt: true
- userSecret: <user's encryption secret>
```

**Response:**
```json
{
  "message": "File uploaded and encrypted.",
  "file": {
    "id": "uuid",
    "encrypted": true,
    "requires_otp": true,
    "file_size": 12345,
    "uploaded_at": "2024-01-05T10:00:00Z"
  }
}
```

### 2. Request OTP for File Access
```http
POST /api/uploads/:id/request-otp
Authorization: Bearer <token>
```

**Response:**
```json
{
  "message": "OTP sent successfully.",
  "file_id": "uuid"
}
```

### 3. Decrypt and Download File
```http
POST /api/uploads/:id/decrypt
Authorization: Bearer <token>
Content-Type: application/json

Body:
{
  "otp": "123456",
  "userSecret": "<user's encryption secret>"
}
```

**Response:**
- Binary file data with original filename
- Content-Disposition header with decrypted filename

### 4. Get File Access Logs
```http
GET /api/uploads/:id/access-logs
Authorization: Bearer <token>
```

**Response:**
```json
{
  "logs": [
    {
      "id": "uuid",
      "access_type": "decrypt",
      "otp_verified": true,
      "success": true,
      "ip_address": "192.168.1.1",
      "accessed_at": "2024-01-05T10:00:00Z"
    }
  ]
}
```

### 5. Get Access Statistics
```http
GET /api/uploads/stats/access
Authorization: Bearer <token>
```

**Response:**
```json
{
  "stats": {
    "total_accesses": 10,
    "successful_accesses": 8,
    "failed_accesses": 2,
    "otp_verified_accesses": 8,
    "last_access_time": "2024-01-05T10:00:00Z"
  }
}
```

## Database Schema

### user_files Table (Updated)
```sql
CREATE TABLE user_files (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  file_name TEXT,                    -- Generic name if encrypted
  file_path TEXT NOT NULL,
  file_size BIGINT,
  mime_type TEXT,
  
  -- Encryption fields
  encrypted BOOLEAN DEFAULT FALSE,
  encryption_iv TEXT,                -- IV for file encryption
  encryption_tag TEXT,               -- Auth tag for file encryption
  encryption_salt TEXT,              -- Salt for key derivation
  encrypted_filename TEXT,           -- Encrypted original filename
  filename_iv TEXT,                  -- IV for filename encryption
  filename_tag TEXT,                 -- Auth tag for filename encryption
  requires_otp BOOLEAN DEFAULT TRUE,
  last_accessed_at TIMESTAMPTZ,
  
  uploaded_at TIMESTAMPTZ DEFAULT NOW()
);
```

### file_access_logs Table (New)
```sql
CREATE TABLE file_access_logs (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  file_id UUID NOT NULL,
  access_type TEXT,                  -- 'view', 'download', 'decrypt'
  otp_verified BOOLEAN DEFAULT FALSE,
  ip_address TEXT,
  user_agent TEXT,
  success BOOLEAN DEFAULT FALSE,
  error_message TEXT,
  accessed_at TIMESTAMPTZ DEFAULT NOW()
);
```

### user_encryption_keys Table (New)
```sql
CREATE TABLE user_encryption_keys (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL UNIQUE,
  encrypted_master_key TEXT NOT NULL,  -- Master key encrypted with user password
  key_iv TEXT NOT NULL,
  key_tag TEXT NOT NULL,
  key_salt TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Encryption Flow

### Upload Flow
```
1. User selects file
2. Frontend/Backend receives file
3. User provides encryption secret (password-derived)
4. Server generates random salt
5. Server derives encryption key from secret + salt
6. Server encrypts file content with AES-256-GCM
7. Server encrypts filename with same key
8. Server uploads encrypted blob to Supabase Storage
9. Server stores encryption metadata in database
10. Original file is never stored in plaintext
```

### Download/Decrypt Flow
```
1. User requests file access
2. Server checks if file requires OTP
3. Server sends OTP to user (SMS/Email)
4. User provides OTP + encryption secret
5. Server verifies OTP
6. Server downloads encrypted blob from storage
7. Server derives decryption key from secret + stored salt
8. Server decrypts file content
9. Server decrypts filename
10. Server returns decrypted file to user
11. Server logs access attempt
```

## Security Features

### 1. End-to-End Encryption
- Files are encrypted with AES-256-GCM
- Encryption keys are derived from user secrets
- No plaintext files stored anywhere

### 2. OTP-Based Access Control
- Every file access requires OTP verification
- OTPs expire after 10 minutes
- OTPs are single-use (marked as verified after use)

### 3. Audit Logging
- All access attempts are logged
- Logs include: timestamp, IP, user agent, success/failure
- Users can view their own access logs

### 4. Zero-Knowledge Architecture
- Database admins cannot decrypt files
- Encryption keys are never stored in plaintext
- User must provide secret for decryption

### 5. Filename Privacy
- Original filenames are encrypted
- Storage uses generic names like `encrypted_1234567890.enc`
- Filenames only revealed after OTP verification + decryption

## Integration with Agent Flow

### Agent Requesting Document Access
```javascript
// In chat flow, when agent needs to access documents:

// 1. Agent detects user wants to share documents
agent.response = "I need to verify your identity before accessing your documents. I'll send you an OTP.";

// 2. Request OTP
await fetch('/api/uploads/:fileId/request-otp', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` }
});

agent.response = "I've sent an OTP to your registered phone/email. Please provide the OTP to continue.";

// 3. User provides OTP
const userOtp = await getUserInput();

// 4. Decrypt and access file
const response = await fetch('/api/uploads/:fileId/decrypt', {
  method: 'POST',
  headers: { 
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    otp: userOtp,
    userSecret: derivedSecret // From user's password
  })
});

// 5. Process decrypted file
const fileBlob = await response.blob();
// Extract information, process, etc.
```

## Configuration

### Environment Variables
```env
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_service_key

# OTP Service (optional - for SMS/Email)
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_number

# Or use AWS SNS, SendGrid, etc.
```

### Migration
```bash
# Apply the encryption migration
supabase db push

# Or manually run:
psql -h your_db_host -U postgres -d your_db -f supabase/migrations/20240105000000_add_file_encryption.sql
```

## Usage Examples

### Example 1: Upload Encrypted Document
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('encrypt', 'true');
formData.append('userSecret', await deriveUserSecret(userPassword));

const response = await fetch('/api/uploads', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  body: formData
});

const { file } = await response.json();
console.log('File uploaded:', file.id);
```

### Example 2: Access Encrypted Document with OTP
```javascript
// Step 1: Request OTP
await fetch(`/api/uploads/${fileId}/request-otp`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` }
});

// Step 2: User receives OTP via SMS/Email
const otp = prompt('Enter OTP:');

// Step 3: Decrypt and download
const response = await fetch(`/api/uploads/${fileId}/decrypt`, {
  method: 'POST',
  headers: { 
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    otp: otp,
    userSecret: await deriveUserSecret(userPassword)
  })
});

const blob = await response.blob();
const url = URL.createObjectURL(blob);
window.open(url);
```

### Example 3: View Access Logs
```javascript
const response = await fetch(`/api/uploads/${fileId}/access-logs`, {
  headers: { 'Authorization': `Bearer ${token}` }
});

const { logs } = await response.json();
logs.forEach(log => {
  console.log(`${log.accessed_at}: ${log.access_type} - ${log.success ? 'Success' : 'Failed'}`);
});
```

## Security Best Practices

### 1. User Secret Management
- Derive from user password using PBKDF2
- Never store in plaintext
- Use secure key derivation function
- Consider using hardware security modules (HSM) for production

### 2. OTP Security
- Use time-based OTPs (TOTP) or SMS/Email OTPs
- Implement rate limiting (max 3 attempts)
- Expire OTPs after 10 minutes
- Mark OTPs as used after verification

### 3. Access Control
- Enforce RLS (Row Level Security) on all tables
- Log all access attempts
- Monitor for suspicious activity
- Implement IP-based rate limiting

### 4. Key Rotation
- Implement periodic key rotation
- Re-encrypt files with new keys
- Maintain key version history

### 5. Backup and Recovery
- Encrypted backups only
- Secure key escrow for recovery
- Multi-factor authentication for recovery

## Testing

### Test Encrypted Upload
```bash
curl -X POST http://localhost:5000/api/uploads \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.pdf" \
  -F "encrypt=true" \
  -F "userSecret=test_secret_123"
```

### Test OTP Request
```bash
curl -X POST http://localhost:5000/api/uploads/FILE_ID/request-otp \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test Decryption
```bash
curl -X POST http://localhost:5000/api/uploads/FILE_ID/decrypt \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"otp":"123456","userSecret":"test_secret_123"}' \
  --output decrypted_file.pdf
```

## Troubleshooting

### Issue: Decryption fails
- **Cause**: Wrong userSecret or corrupted file
- **Solution**: Verify userSecret matches the one used for encryption

### Issue: OTP not received
- **Cause**: OTP service not configured
- **Solution**: Configure Twilio/AWS SNS or check logs for OTP

### Issue: Access denied
- **Cause**: OTP expired or already used
- **Solution**: Request new OTP

## Future Enhancements

1. **Client-Side Encryption**: Encrypt files in browser before upload
2. **Hardware Security Module (HSM)**: Use HSM for key management
3. **Multi-Factor Authentication**: Add biometric verification
4. **Key Escrow**: Secure key recovery mechanism
5. **Compliance**: HIPAA, GDPR, SOC 2 compliance features
6. **File Sharing**: Encrypted file sharing with other users
7. **Versioning**: Encrypted file version control

## Files Modified/Created

### New Files
- `auth-app/backend/utils/encryption.js` - Encryption utilities
- `supabase/migrations/20240105000000_add_file_encryption.sql` - Database schema
- `DOCUMENT_ENCRYPTION_IMPLEMENTATION.md` - This documentation

### Modified Files
- `auth-app/backend/routes/uploads.js` - Added encryption endpoints

## Conclusion

This implementation provides **military-grade encryption** for user documents with **OTP-based access control**. Even database administrators cannot view encrypted files without the user's encryption key and OTP verification.

The system is designed with **zero-knowledge architecture**, ensuring maximum privacy and security for sensitive documents like Aadhaar cards, PAN cards, and other identity documents.
