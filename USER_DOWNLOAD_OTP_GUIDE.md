# User Document Download with OTP Verification

## Overview
All user document downloads now require **OTP verification** for maximum security. When a user wants to download their uploaded documents, they must verify their identity via SMS OTP.

## Security Flow

### 1. User Requests Download
- User clicks download button on a document
- System checks if user has phone number registered
- If yes: System sends 6-digit OTP via Message Central SMS
- If no: System prompts user to add phone number first

### 2. User Receives OTP
- User receives SMS with 6-digit OTP
- OTP expires in 10 minutes
- User has max 5 attempts to enter correct OTP

### 3. User Provides OTP
- User enters OTP in download dialog
- System verifies OTP with Message Central
- If valid: File download starts immediately
- If invalid: User gets remaining attempts count

### 4. Download Completes
- File is downloaded to user's device
- Access is logged in `file_access_logs` table
- OTP is marked as used (single-use)

## API Endpoints

### 1. Request OTP for Download
```http
POST /api/uploads/:id/request-download-otp
Authorization: Bearer <user_token>
```

**Parameters:**
- `:id` - File ID to download

**Response (Success):**
```json
{
  "message": "OTP sent to your registered phone number.",
  "phone_last_4": "1234",
  "expires_in_minutes": 10,
  "file_name": "aadhaar.pdf"
}
```

**Response (No Phone):**
```json
{
  "error": "No phone number registered. Please add a phone number to your profile first.",
  "requires_phone": true
}
```

**Response (File Not Found):**
```json
{
  "error": "File not found."
}
```

### 2. Download File with OTP
```http
POST /api/uploads/:id/download
Authorization: Bearer <user_token>
Content-Type: application/json

{
  "otp": "123456"
}
```

**Parameters:**
- `:id` - File ID to download
- `otp` - 6-digit OTP code

**Response (Success):**
- Binary file data
- Content-Type: Based on file mime type
- Content-Disposition: `attachment; filename="original_filename.ext"`

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

**Response (OTP Expired):**
```json
{
  "error": "No pending OTP found or OTP expired. Please request a new one."
}
```

**Response (Wrong File):**
```json
{
  "error": "OTP is not valid for this file."
}
```

### 3. Get Signed URL (DEPRECATED)
```http
GET /api/uploads/:id/url
Authorization: Bearer <user_token>
```

**Response:**
```json
{
  "error": "OTP verification required to download files.",
  "requires_otp": true,
  "file_id": "uuid",
  "message": "Please use POST /:id/request-download-otp to request OTP, then POST /:id/download with OTP to download."
}
```

**Note:** This endpoint is deprecated. All downloads now require OTP verification.

## Frontend Integration

### React/JavaScript Example

```javascript
// Step 1: Request OTP
async function requestDownloadOTP(fileId) {
  try {
    const response = await fetch(`/api/uploads/${fileId}/request-download-otp`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    const data = await response.json();
    
    if (response.ok) {
      // Show OTP input dialog
      showOTPDialog({
        message: `OTP sent to phone ending in ${data.phone_last_4}`,
        fileName: data.file_name,
        expiresIn: data.expires_in_minutes
      });
    } else if (data.requires_phone) {
      // Prompt user to add phone number
      showAddPhoneDialog();
    } else {
      showError(data.error);
    }
  } catch (error) {
    showError('Failed to request OTP');
  }
}

// Step 2: Download with OTP
async function downloadWithOTP(fileId, otp) {
  try {
    const response = await fetch(`/api/uploads/${fileId}/download`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ otp })
    });
    
    if (response.ok) {
      // Get filename from Content-Disposition header
      const contentDisposition = response.headers.get('Content-Disposition');
      const filename = contentDisposition
        ? contentDisposition.split('filename=')[1].replace(/"/g, '')
        : 'download';
      
      // Download file
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      showSuccess('File downloaded successfully');
      closeOTPDialog();
    } else {
      const data = await response.json();
      
      if (data.remaining_attempts !== undefined) {
        showError(`${data.error} (${data.remaining_attempts} attempts remaining)`);
      } else {
        showError(data.error);
        
        if (data.error.includes('Too many failed attempts')) {
          closeOTPDialog();
        }
      }
    }
  } catch (error) {
    showError('Download failed');
  }
}

// Usage
document.getElementById('download-btn').addEventListener('click', () => {
  const fileId = document.getElementById('file-id').value;
  requestDownloadOTP(fileId);
});
```

### Complete UI Flow

```javascript
// OTP Dialog Component
function OTPDialog({ fileId, fileName, phoneLast4, onClose }) {
  const [otp, setOTP] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const handleSubmit = async () => {
    if (otp.length !== 6) {
      setError('Please enter 6-digit OTP');
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(`/api/uploads/${fileId}/download`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ otp })
      });
      
      if (response.ok) {
        // Download file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        a.click();
        window.URL.revokeObjectURL(url);
        
        onClose();
      } else {
        const data = await response.json();
        setError(data.error);
        
        if (data.error.includes('Too many failed attempts')) {
          setTimeout(onClose, 2000);
        }
      }
    } catch (error) {
      setError('Download failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="otp-dialog">
      <h3>Verify OTP to Download</h3>
      <p>OTP sent to phone ending in {phoneLast4}</p>
      <p>File: {fileName}</p>
      
      <input
        type="text"
        maxLength="6"
        placeholder="Enter 6-digit OTP"
        value={otp}
        onChange={(e) => setOTP(e.target.value.replace(/\D/g, ''))}
        disabled={loading}
      />
      
      {error && <p className="error">{error}</p>}
      
      <div className="buttons">
        <button onClick={handleSubmit} disabled={loading || otp.length !== 6}>
          {loading ? 'Verifying...' : 'Download'}
        </button>
        <button onClick={onClose} disabled={loading}>
          Cancel
        </button>
      </div>
      
      <p className="hint">OTP expires in 10 minutes</p>
    </div>
  );
}
```

## User Experience Flow

### Scenario 1: Successful Download

```
User: [Clicks download button on "aadhaar.pdf"]

System: [Sends OTP request]
        [Shows dialog] "OTP sent to phone ending in 1234"

User: [Receives SMS with OTP: 123456]
      [Enters OTP in dialog]
      [Clicks "Download"]

System: [Verifies OTP]
        [Downloads file]
        "File downloaded successfully"
```

### Scenario 2: Invalid OTP

```
User: [Enters wrong OTP: 999999]

System: "❌ Invalid OTP. 4 attempt(s) remaining."

User: [Enters correct OTP: 123456]

System: [Downloads file]
        "File downloaded successfully"
```

### Scenario 3: Too Many Failed Attempts

```
User: [Enters wrong OTP 5 times]

System: "🚫 Too many failed attempts. Please request a new OTP."
        [Closes dialog]

User: [Clicks download button again]

System: [Sends new OTP]
        "OTP sent to phone ending in 1234"
```

### Scenario 4: No Phone Number

```
User: [Clicks download button]

System: "⚠️ Phone Number Required
        
        To download your documents securely, you need to have a phone number registered.
        Please add your phone number to your profile first."
        
        [Shows "Add Phone Number" button]

User: [Clicks "Add Phone Number"]
      [Adds phone: +919876543210]

System: "Phone number added successfully"

User: [Clicks download button again]

System: [Sends OTP]
        "OTP sent to phone ending in 3210"
```

## Security Features

### 1. OTP Expiry
- OTPs expire after **10 minutes**
- User must request new OTP after expiry
- Expired OTPs are automatically cleaned up

### 2. Rate Limiting
- Max **5 verification attempts** per OTP
- After 5 failed attempts, OTP is invalidated
- User must request new OTP

### 3. Single-Use OTPs
- Each OTP can only be verified once
- After successful verification, OTP is marked as `verified = true`
- Prevents replay attacks

### 4. File-Specific OTPs
- Each OTP is tied to a specific file ID
- OTP for file A cannot be used to download file B
- Stored in OTP metadata: `{"file_id": "uuid"}`

### 5. Audit Logging
- All download requests logged
- All OTP verification attempts logged (success/failure)
- Logs include:
  - User ID
  - File ID
  - Access type: `download`
  - OTP verification status
  - IP address
  - User agent
  - Timestamp

## Database Schema

### `otp_verifications` Table

```sql
-- OTP record for user download
INSERT INTO otp_verifications (
  user_id,
  phone,
  verification_id,
  purpose,
  metadata,
  expires_at,
  attempts
) VALUES (
  'user-uuid',
  '+919876543210',
  'mc-verification-id',
  'user_download',
  '{"file_id": "file-uuid"}',
  NOW() + INTERVAL '10 minutes',
  0
);
```

### `file_access_logs` Table

```sql
-- Log download attempt
INSERT INTO file_access_logs (
  user_id,
  file_id,
  access_type,
  otp_verified,
  ip_address,
  user_agent,
  success,
  error_message
) VALUES (
  'user-uuid',
  'file-uuid',
  'download',
  true,
  '192.168.1.1',
  'Mozilla/5.0...',
  true,
  NULL
);
```

## Testing

### 1. Test OTP Request

```bash
curl -X POST http://localhost:4000/api/uploads/FILE_ID/request-download-otp \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response:**
```json
{
  "message": "OTP sent to your registered phone number.",
  "phone_last_4": "1234",
  "expires_in_minutes": 10,
  "file_name": "aadhaar.pdf"
}
```

### 2. Test Download with OTP

```bash
curl -X POST http://localhost:4000/api/uploads/FILE_ID/download \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"otp":"123456"}' \
  --output downloaded_file.pdf
```

**Expected:** File downloads successfully

### 3. Test Invalid OTP

```bash
curl -X POST http://localhost:4000/api/uploads/FILE_ID/download \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"otp":"999999"}'
```

**Expected Response:**
```json
{
  "error": "Invalid OTP. 4 attempt(s) remaining.",
  "remaining_attempts": 4
}
```

### 4. Test Deprecated Endpoint

```bash
curl -X GET http://localhost:4000/api/uploads/FILE_ID/url \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response:**
```json
{
  "error": "OTP verification required to download files.",
  "requires_otp": true,
  "file_id": "uuid",
  "message": "Please use POST /:id/request-download-otp to request OTP, then POST /:id/download with OTP to download."
}
```

## Migration Guide

### For Existing Frontend Code

**Old Code (Deprecated):**
```javascript
// Old: Direct download via signed URL
const response = await fetch(`/api/uploads/${fileId}/url`);
const { url } = await response.json();
window.open(url);
```

**New Code (OTP Required):**
```javascript
// New: OTP-protected download
// Step 1: Request OTP
await fetch(`/api/uploads/${fileId}/request-download-otp`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` }
});

// Step 2: Show OTP dialog
const otp = await showOTPDialog();

// Step 3: Download with OTP
const response = await fetch(`/api/uploads/${fileId}/download`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ otp })
});

const blob = await response.blob();
// ... download blob
```

## Cost Considerations

**Message Central SMS OTP:**
- Cost per SMS: ₹0.10 - ₹0.20
- OTPs per download: 1 (average)
- Cost per download: ₹0.10 - ₹0.20

**Monthly Estimates:**
- 100 downloads: ₹10-20
- 1,000 downloads: ₹100-200
- 10,000 downloads: ₹1,000-2,000

## Troubleshooting

### Issue: OTP Not Received

**Possible Causes:**
1. User has no phone number registered
2. Message Central credentials incorrect
3. Phone number format invalid

**Solutions:**
1. Check user profile for phone number
2. Verify Message Central credentials in `.env`
3. Validate phone number format (+91XXXXXXXXXX)

### Issue: "OTP is not valid for this file"

**Cause:** User requested OTP for file A but trying to download file B

**Solution:** Request new OTP for the correct file

### Issue: Download Fails After OTP Verification

**Possible Causes:**
1. File deleted from storage
2. Storage permissions issue
3. Network error

**Solutions:**
1. Check file exists in Supabase Storage
2. Verify storage bucket permissions
3. Check network connectivity

## Conclusion

All user document downloads now require **OTP verification** for maximum security:

✅ **Two-Factor Authentication** for downloads
✅ **SMS Delivery** via Message Central
✅ **File-Specific OTPs** (cannot reuse for different files)
✅ **Rate Limiting** (max 5 attempts)
✅ **Audit Logging** for compliance
✅ **Single-Use OTPs** (prevents replay attacks)

This ensures that only the legitimate user can download their documents, even if their account is compromised.
