# Message Central OTP Integration for File Encryption

## Overview
The file encryption system is integrated with **Message Central** (cpaas.messagecentral.com) for OTP-based file access verification. This provides secure, SMS-based two-factor authentication for accessing encrypted documents.

## Current OTP Service

### Provider: Message Central
- **Service**: Message Central CPaaS (Communication Platform as a Service)
- **Base URL**: `https://cpaas.messagecentral.com`
- **Method**: SMS OTP (6-digit codes)
- **Country**: India (+91)
- **OTP Length**: 6 digits
- **Expiry**: 10 minutes

### Authentication Flow
1. **Get Auth Token**: Authenticate with Message Central using customer ID and password
2. **Send OTP**: Request OTP to be sent to user's phone number
3. **Verify OTP**: Validate the OTP code provided by user

## Environment Variables Required

```env
# Message Central Credentials
MC_CUSTOMER_ID=your_customer_id
MC_PASSWORD_B64=your_base64_encoded_password

# Supabase (already configured)
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_service_key
```

### How to Get Message Central Credentials
1. Sign up at https://messagecentral.com
2. Get your Customer ID from the dashboard
3. Generate an API password
4. Base64 encode the password: `echo -n "your_password" | base64`
5. Add to `.env` file

## Integration with File Encryption

### Flow Diagram
```
User Requests File Access
         ↓
System Checks: File Encrypted?
         ↓ (Yes)
System Sends OTP via Message Central
         ↓
User Receives SMS with 6-digit OTP
         ↓
User Provides OTP
         ↓
System Verifies OTP with Message Central
         ↓ (Valid)
System Decrypts File
         ↓
User Gets Decrypted File
```

### API Endpoints

#### 1. Request OTP for File Access
```http
POST /api/uploads/:fileId/request-otp
Authorization: Bearer <token>
```

**What Happens:**
1. System gets user's phone number from Supabase Auth
2. System calls Message Central API to send OTP
3. Message Central sends SMS to user's phone
4. System stores verification ID in database
5. OTP expires after 10 minutes

**Response:**
```json
{
  "message": "OTP sent successfully.",
  "file_id": "uuid"
}
```

#### 2. Decrypt File with OTP
```http
POST /api/uploads/:fileId/decrypt
Authorization: Bearer <token>
Content-Type: application/json

{
  "otp": "123456",
  "userSecret": "encryption_secret"
}
```

**What Happens:**
1. System retrieves verification ID from database
2. System calls Message Central API to verify OTP
3. If valid, system decrypts file
4. System marks OTP as verified (single-use)
5. System logs access attempt
6. System returns decrypted file

**Response:**
- Binary file data with original filename

## Message Central API Details

### 1. Get Authentication Token
```javascript
GET https://cpaas.messagecentral.com/auth/v1/authentication/token
    ?customerId={MC_CUSTOMER_ID}
    &key={MC_PASSWORD_B64}
    &scope=NEW
    &country=91

Headers:
  accept: */*

Response:
{
  "token": "auth_token_here",
  "expiresIn": 3600
}
```

### 2. Send OTP
```javascript
POST https://cpaas.messagecentral.com/verification/v3/send
     ?countryCode=91
     &flowType=SMS
     &mobileNumber={10_digit_number}
     &otpLength=6

Headers:
  authToken: {token_from_step_1}

Response:
{
  "responseCode": 200,
  "message": "SUCCESS",
  "data": {
    "verificationId": "verification_id_here",
    "mobileNumber": "9876543210",
    "responseCode": "200",
    "errorMessage": null,
    "timeout": "60",
    "smsCLI": null,
    "transactionId": null
  }
}
```

### 3. Verify OTP
```javascript
GET https://cpaas.messagecentral.com/verification/v3/validateOtp
    ?verificationId={verification_id}
    &code={6_digit_otp}

Headers:
  authToken: {token_from_step_1}

Response:
{
  "responseCode": 200,
  "message": "SUCCESS",
  "data": {
    "verificationId": "verification_id_here",
    "mobileNumber": "9876543210",
    "verificationStatus": "VERIFICATION_COMPLETED",
    "responseCode": "200",
    "errorMessage": null,
    "transactionId": null
  }
}
```

## Database Schema Updates

### otp_verifications Table (Updated)
```sql
CREATE TABLE otp_verifications (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  phone TEXT,                        -- NEW: Phone number
  verification_id TEXT,              -- NEW: Message Central verification ID
  otp TEXT,                          -- Deprecated (not used with Message Central)
  purpose TEXT,                      -- 'file_access', 'login', etc.
  verified BOOLEAN DEFAULT FALSE,
  attempts INTEGER DEFAULT 0,        -- NEW: Failed attempt counter
  last_attempt_at TIMESTAMPTZ,       -- NEW: Last verification attempt
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  verified_at TIMESTAMPTZ
);
```

## Security Features

### 1. Rate Limiting
- **Per Phone**: Max 3 OTP requests per 10 minutes
- **Per IP**: Max 5 OTP requests per 10 minutes
- **Verification Attempts**: Max 5 attempts per OTP

### 2. OTP Expiry
- OTPs expire after **10 minutes**
- Expired OTPs cannot be verified
- User must request new OTP after expiry

### 3. Single-Use OTPs
- Each OTP can only be verified once
- After successful verification, OTP is marked as `verified = true`
- Prevents replay attacks

### 4. Attempt Tracking
- Failed verification attempts are counted
- After 5 failed attempts, OTP is invalidated
- User must request new OTP

### 5. Audit Logging
- All OTP requests logged with IP address
- All verification attempts logged
- Success/failure status tracked

## Error Handling

### Common Errors

#### 1. User Has No Phone Number
```json
{
  "error": "User has no phone number registered"
}
```
**Solution**: User must add phone number to their profile

#### 2. Message Central Credentials Not Configured
```json
{
  "error": "Message Central credentials not configured"
}
```
**Solution**: Add `MC_CUSTOMER_ID` and `MC_PASSWORD_B64` to `.env`

#### 3. OTP Expired
```json
{
  "error": "OTP expired. Request a new one."
}
```
**Solution**: Request new OTP via `/api/uploads/:id/request-otp`

#### 4. Invalid OTP
```json
{
  "error": "Invalid OTP."
}
```
**Solution**: Check OTP code and try again (max 5 attempts)

#### 5. Too Many Attempts
```json
{
  "error": "Too many failed attempts. Request a new OTP."
}
```
**Solution**: Request new OTP after 10 minutes

## Testing

### Test OTP Flow (Development)

#### 1. Enable Message Central in .env
```env
MC_CUSTOMER_ID=your_customer_id
MC_PASSWORD_B64=your_base64_password
```

#### 2. Ensure User Has Phone Number
```sql
-- Check user's phone
SELECT id, phone FROM auth.users WHERE id = 'user_id';

-- Update user's phone if needed
UPDATE auth.users 
SET phone = '+919876543210' 
WHERE id = 'user_id';
```

#### 3. Request OTP
```bash
curl -X POST http://localhost:5000/api/uploads/FILE_ID/request-otp \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### 4. Check SMS on Phone
- You should receive SMS with 6-digit OTP
- OTP is valid for 10 minutes

#### 5. Decrypt File with OTP
```bash
curl -X POST http://localhost:5000/api/uploads/FILE_ID/decrypt \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"otp":"123456","userSecret":"your_secret"}' \
  --output decrypted_file.pdf
```

### Test Without Message Central (Development Only)

For development/testing without Message Central:

1. **Mock OTP Verification**: Temporarily modify `verifyOTP()` to accept any 6-digit code
2. **Console Logging**: OTP is logged to console (not sent via SMS)
3. **Database Check**: Verify OTP records in `otp_verifications` table

## Production Deployment

### Checklist

- [ ] Sign up for Message Central account
- [ ] Get Customer ID and API password
- [ ] Base64 encode password
- [ ] Add credentials to production `.env`
- [ ] Test OTP sending with real phone number
- [ ] Verify SMS delivery
- [ ] Test OTP verification flow
- [ ] Monitor Message Central dashboard for usage
- [ ] Set up billing alerts
- [ ] Configure rate limiting
- [ ] Enable audit logging

### Cost Considerations

**Message Central Pricing** (approximate):
- SMS OTP: ₹0.10 - ₹0.20 per SMS
- Verification API calls: Included
- Monthly minimum: Check with Message Central

**Estimated Costs**:
- 100 file accesses/month: ₹10-20
- 1,000 file accesses/month: ₹100-200
- 10,000 file accesses/month: ₹1,000-2,000

## Monitoring

### Metrics to Track

1. **OTP Success Rate**: % of OTPs successfully verified
2. **Failed Attempts**: Number of failed verification attempts
3. **Expiry Rate**: % of OTPs that expire before verification
4. **Average Verification Time**: Time between send and verify
5. **Message Central API Errors**: Failed API calls

### Logging

All OTP operations are logged:
```javascript
console.log(`OTP sent to user ${userId} at ${phone}`);
console.log(`OTP verified for user ${userId}`);
console.error('Message Central send error:', error);
```

Check logs for:
- OTP send failures
- Verification failures
- API errors
- Rate limit hits

## Troubleshooting

### Issue: OTP Not Received

**Possible Causes:**
1. Wrong phone number format (must be +91XXXXXXXXXX)
2. Message Central credentials incorrect
3. Insufficient Message Central balance
4. Phone number blocked/invalid

**Solutions:**
1. Verify phone number format
2. Check Message Central dashboard
3. Top up Message Central account
4. Test with different phone number

### Issue: OTP Verification Fails

**Possible Causes:**
1. OTP expired (>10 minutes)
2. Wrong OTP code
3. OTP already used
4. Too many failed attempts

**Solutions:**
1. Request new OTP
2. Double-check OTP code
3. Ensure OTP not already verified
4. Wait 10 minutes and request new OTP

### Issue: Message Central API Errors

**Possible Causes:**
1. Invalid credentials
2. API rate limits exceeded
3. Network issues
4. Message Central service down

**Solutions:**
1. Verify credentials in `.env`
2. Check Message Central dashboard for limits
3. Check network connectivity
4. Check Message Central status page

## Alternative OTP Providers

If you want to switch from Message Central, the code supports:

### 1. Twilio
- Replace Message Central API calls with Twilio API
- Update `sendOtpViaMessageCentral()` and `verifyOtpWithMessageCentral()`
- Add Twilio credentials to `.env`

### 2. AWS SNS
- Use AWS SNS for SMS delivery
- Update OTP functions to use AWS SDK
- Add AWS credentials to `.env`

### 3. Firebase Auth
- Use Firebase Phone Authentication
- Update to use Firebase SDK
- Add Firebase config to `.env`

## Conclusion

The file encryption system is fully integrated with **Message Central** for secure, SMS-based OTP verification. This provides:

✅ **Two-Factor Authentication** for file access
✅ **SMS Delivery** via Message Central
✅ **Rate Limiting** to prevent abuse
✅ **Audit Logging** for compliance
✅ **Single-Use OTPs** for security
✅ **Automatic Expiry** after 10 minutes

Users must verify their identity via OTP before accessing encrypted files, ensuring maximum security even if encryption keys are compromised.
