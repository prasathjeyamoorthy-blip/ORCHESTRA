/**
 * otp.js — Phone OTP helpers
 *
 * Calls your own Express backend (/api/otp/*) which uses Message Central to send
 * real SMS to any Indian number — no Supabase phone auth, no Twilio.
 *
 * Phone numbers MUST be in E.164 format: +917695842138
 */

/**
 * sendOtp(phone)
 *
 * @param {string} phone  E.164 format, e.g. "+917695842138"
 * @returns {{ error: string|null }}
 */
export async function sendOtp(phone) {
  try {
    const res = await fetch('/api/otp/send', {
      method:      'POST',
      credentials: 'include',
      headers:     { 'Content-Type': 'application/json' },
      body:        JSON.stringify({ phone }),
    });
    const data = await res.json();
    if (!res.ok) return { error: data.error || 'Failed to send OTP.' };
    return { error: null };
  } catch {
    return { error: 'Network error. Please try again.' };
  }
}

/**
 * verifyOtp(phone, token)
 *
 * @param {string} phone  E.164 format — must match the number used in sendOtp
 * @param {string} token  6-digit OTP from SMS
 * @returns {{ error: string|null }}
 */
export async function verifyOtp(phone, token) {
  try {
    const res = await fetch('/api/otp/verify', {
      method:      'POST',
      credentials: 'include',
      headers:     { 'Content-Type': 'application/json' },
      body:        JSON.stringify({ phone, otp: token }),
    });
    const data = await res.json();
    if (!res.ok) return { error: data.error || 'Verification failed.' };
    return { error: null };
  } catch {
    return { error: 'Network error. Please try again.' };
  }
}
