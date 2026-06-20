const router = require('express').Router();
const { createClient } = require('@supabase/supabase-js');

const BASE_URL = 'https://cpaas.messagecentral.com';

// ── Multi-account credentials (fallback if primary expires) ─────────────────
const MC_ACCOUNTS = [
  {
    customerId:  process.env.MC_CUSTOMER_ID,
    passwordB64: process.env.MC_PASSWORD_B64,
  },
  {
    customerId:  process.env.MC_CUSTOMER_ID_2,
    passwordB64: process.env.MC_PASSWORD_B64_2,
  },
  {
    customerId:  process.env.MC_CUSTOMER_ID_3,
    passwordB64: process.env.MC_PASSWORD_B64_3,
  },
].filter(a => a.customerId && a.passwordB64); // only include configured accounts

// ── Security: Rate limiting and anti-spam ────────────────────────────────────
const RATE_LIMIT_WINDOW = 10 * 60 * 1000; // 10 minutes in ms
const MAX_OTP_PER_PHONE = 3;
const MAX_OTP_PER_IP = 5;
const MAX_VERIFY_ATTEMPTS = 5;

// Rate limit tracking
const phoneRateLimits = new Map(); // phone -> { count, resetAt }
const ipRateLimits = new Map();    // ip -> { count, resetAt }

// Helper: Check and update rate limit
function checkRateLimit(store, key, maxAttempts, identifier) {
  const now = Date.now();
  const record = store.get(key);
  
  if (!record || now > record.resetAt) {
    // Create new record
    const resetAt = now + RATE_LIMIT_WINDOW;
    store.set(key, { count: 1, resetAt });
    // Auto-cleanup after window expires
    setTimeout(() => store.delete(key), RATE_LIMIT_WINDOW);
    return true;
  }
  
  if (record.count >= maxAttempts) {
    console.log(`[otp/send] BLOCKED - rate limit exceeded for ${identifier}: ${key}`);
    return false;
  }
  
  record.count++;
  return true;
}

// Helper: Validate Indian phone number
function validateIndianPhone(phone) {
  // Must be exactly +91 followed by 10 digits (total 13 chars)
  return /^\+91\d{10}$/.test(phone);
}

// Get auth token from a specific MC account
async function getAuthTokenForAccount({ customerId, passwordB64 }) {
  const url = `${BASE_URL}/auth/v1/authentication/token?customerId=${customerId}&key=${passwordB64}&scope=NEW&country=91`;
  const res = await fetch(url, { headers: { accept: '*/*' } });

  if (!res.ok) {
    throw new Error(`MC auth failed (${customerId}): ${res.status} ${res.statusText}`);
  }

  const data = await res.json();
  if (!data.token) {
    throw new Error(`No token returned (${customerId}): ${JSON.stringify(data)}`);
  }

  return data.token;
}

// Get auth token — tries primary account first, falls back to secondary on failure
async function getAuthToken() {
  if (MC_ACCOUNTS.length === 0) {
    throw new Error('No Message Central credentials configured. Set MC_CUSTOMER_ID and MC_PASSWORD_B64 in .env');
  }

  let lastError;
  for (const account of MC_ACCOUNTS) {
    try {
      const token = await getAuthTokenForAccount(account);
      // Attach customerId so callers know which account is active
      return { token, customerId: account.customerId };
    } catch (err) {
      console.warn(`[MC] Account ${account.customerId} failed auth, trying next: ${err.message}`);
      lastError = err;
    }
  }
  throw new Error(`All Message Central accounts failed: ${lastError?.message}`);
}

// Send OTP via Message Central
async function sendOtpMC(mobile) {
  const { token } = await getAuthToken();
  const number = mobile.replace(/^\+91/, '').replace(/^\+/, '');
  const url = `${BASE_URL}/verification/v3/send?countryCode=91&flowType=SMS&mobileNumber=${number}&otpLength=6`;

  const res = await fetch(url, {
    method: 'POST',
    headers: { authToken: token }
  });

  if (!res.ok) {
    throw new Error(`Message Central send failed: ${res.status} ${res.statusText}`);
  }

  const data = await res.json();
  console.log('[MC send response]', JSON.stringify(data));

  if (data.responseCode !== 200) {
    throw new Error(`MC error: ${data.message || JSON.stringify(data)}`);
  }

  if (!data.data?.verificationId) {
    throw new Error(`No verificationId in response: ${JSON.stringify(data)}`);
  }

  return data.data.verificationId;
}

// Verify OTP via Message Central
async function verifyOtpMC(verificationId, otp) {
  const { token } = await getAuthToken();
  const url = `${BASE_URL}/verification/v3/validateOtp?verificationId=${verificationId}&code=${otp}`;

  const res = await fetch(url, { headers: { authToken: token } });

  if (!res.ok) {
    console.error(`[MC verify] HTTP error: ${res.status} ${res.statusText}`);
    return false;
  }

  const data = await res.json();
  console.log('[MC verify response]', JSON.stringify(data));

  return data?.data?.verificationStatus === 'VERIFICATION_COMPLETED';
}

// In-memory store for verificationId and attempt tracking
// Structure: phone -> { verificationId, attempts, createdAt }
const verificationStore = new Map();

const supabaseAdmin = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

// POST /api/otp/send
router.post('/send', async (req, res) => {
  /* TEMPORARILY DISABLED - UNCOMMENT TO ENABLE
  console.log('[otp/send] OTP feature is temporarily disabled');
  return res.status(503).json({ 
    error: 'Phone verification is temporarily unavailable. Please try again later.' 
  });
  */
  
  // ORIGINAL CODE - NOW ENABLED
  const { phone } = req.body;
  
  // Validate phone format
  if (!phone || typeof phone !== 'string') {
    return res.status(400).json({ error: 'Phone must be E.164 format e.g. +917695842138' });
  }
  
  const normalizedPhone = phone.trim();
  
  // Security: Only allow Indian numbers
  if (!validateIndianPhone(normalizedPhone)) {
    return res.status(400).json({ 
      error: 'Only Indian phone numbers (+91XXXXXXXXXX) are supported.' 
    });
  }
  
  // Check if there's an existing verification that can be replaced
  const existingRecord = verificationStore.get(normalizedPhone);
  const canResend = !existingRecord || existingRecord.attempts >= MAX_VERIFY_ATTEMPTS;
  
  // Security: Rate limiting by phone number (but allow resend after max attempts)
  if (!canResend && !checkRateLimit(phoneRateLimits, normalizedPhone, MAX_OTP_PER_PHONE, 'phone')) {
    return res.status(429).json({ 
      error: 'Too many OTP requests. Please wait 10 minutes.' 
    });
  }
  
  // Security: Rate limiting by IP address
  const clientIp = req.ip || req.connection.remoteAddress || 'unknown';
  if (!checkRateLimit(ipRateLimits, clientIp, MAX_OTP_PER_IP, 'IP')) {
    return res.status(429).json({ 
      error: 'Too many OTP requests. Please wait 10 minutes.' 
    });
  }
  
  try {
    const verificationId = await sendOtpMC(normalizedPhone);
    
    // Store verificationId with attempt tracking (reset attempts for new OTP)
    verificationStore.set(normalizedPhone, {
      verificationId,
      attempts: 0,
      createdAt: Date.now()
    });
    
    // Auto-cleanup after 10 minutes
    setTimeout(() => {
      verificationStore.delete(normalizedPhone);
    }, RATE_LIMIT_WINDOW);
    
    console.log(`[otp/send] OTP sent to ${normalizedPhone}`);
    return res.json({ message: 'OTP sent.' });
  } catch (err) {
    console.error('[otp/send] ERROR:', err.message);
    return res.status(500).json({ error: err.message });
  }
});

// POST /api/otp/verify
router.post('/verify', async (req, res) => {
  /* TEMPORARILY DISABLED - UNCOMMENT TO DISABLE
  console.log('[otp/verify] OTP feature is temporarily disabled');
  return res.status(503).json({ 
    error: 'Phone verification is temporarily unavailable. Please try again later.' 
  });
  */
  
  // ORIGINAL CODE - NOW ENABLED
  try {
    const { phone, otp } = req.body;
    
    if (!phone || !otp) {
      return res.status(400).json({ error: 'Phone and OTP required.' });
    }
    if (!/^\d{6}$/.test(otp.trim())) {
      return res.status(400).json({ error: 'OTP must be 6 digits.' });
    }
    
    const normalizedPhone = phone.trim();
    const normalizedOtp = otp.trim();
    
    const record = verificationStore.get(normalizedPhone);
    if (!record) {
      return res.status(401).json({ error: 'OTP expired. Request a new one.' });
    }
    
    // Security: Check attempt limit
    if (record.attempts >= MAX_VERIFY_ATTEMPTS) {
      console.log(`[otp/verify] BLOCKED - max attempts exceeded for ${normalizedPhone}`);
      verificationStore.delete(normalizedPhone);
      return res.status(429).json({ 
        error: 'Too many failed attempts. Request a new OTP.' 
      });
    }
    
    // Verify OTP with Message Central
    const valid = await verifyOtpMC(record.verificationId, normalizedOtp);
    
    if (!valid) {
      // Increment failed attempt counter
      record.attempts++;
      console.log(`[otp/verify] FAILED attempt ${record.attempts}/${MAX_VERIFY_ATTEMPTS} for ${normalizedPhone}`);
      
      // Check if this was the last allowed attempt
      if (record.attempts >= MAX_VERIFY_ATTEMPTS) {
        verificationStore.delete(normalizedPhone);
        return res.status(429).json({ 
          error: 'Too many failed attempts. Request a new OTP.' 
        });
      }
      
      return res.status(401).json({ 
        error: `Incorrect OTP. Try again. (${record.attempts}/${MAX_VERIFY_ATTEMPTS} attempts used)` 
      });
    }
    
    // OTP is valid - clean up
    verificationStore.delete(normalizedPhone);
    
    // Update Supabase user phone if session exists
    const accessToken = req.cookies?.access_token;
    if (accessToken) {
      try {
        const { data: { user } } = await supabaseAdmin.auth.getUser(accessToken);
        if (user) {
          await supabaseAdmin.auth.admin.updateUserById(user.id, {
            phone: normalizedPhone, 
            phone_confirm: true,
          });
        }
      } catch (e) {
        console.warn('[otp/verify] phone update skipped:', e.message);
      }
    }
    
    return res.json({ message: 'Phone verified successfully.' });
  } catch (err) {
    console.error('[otp/verify] ERROR:', err.message);
    return res.status(500).json({ error: err.message || 'Verification failed.' });
  }
});

module.exports = router;
