/**
 * usePhoneOtp.js
 *
 * Hook that manages the two-step phone OTP flow:
 *   1. User enters phone → sendOtp() → SMS sent
 *   2. User enters 6-digit code → verifyOtp() → session returned
 *
 * After successful verification the caller receives the Supabase session
 * so it can sync httpOnly cookies with the Express backend via
 * POST /api/auth/sync-session (already implemented in auth.js).
 *
 * Usage:
 *   const { step, phone, setPhone, otp, setOtp,
 *           sendCode, verifyCode, loading, error } = usePhoneOtp()
 */
import { useState } from 'react'
import { sendOtp, verifyOtp } from '../lib/otp'

// Validates E.164 format: starts with +, followed by 7–15 digits
function isE164(phone) {
  return /^\+[1-9]\d{6,14}$/.test(phone.trim())
}

export function usePhoneOtp() {
  // 'phone' → waiting for phone input
  // 'otp'   → SMS sent, waiting for 6-digit code
  // 'done'  → verified successfully
  const [step,    setStep]    = useState('phone')
  const [phone,   setPhone]   = useState('')
  const [otp,     setOtp]     = useState('')
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)

  /**
   * sendCode()
   * Validates the phone number and triggers the SMS OTP.
   * Advances step to 'otp' on success.
   */
  async function sendCode() {
    setError(null)

    const trimmed = phone.trim()
    if (!isE164(trimmed)) {
      setError('Enter a valid phone number in E.164 format (e.g. +919876543210)')
      return false
    }

    setLoading(true)
    try {
      const { error: otpErr } = await sendOtp(trimmed)
      if (otpErr) {
        setError(otpErr)
        return false
      }
      setStep('otp')
      return true
    } finally {
      setLoading(false)
    }
  }

  /**
   * verifyCode()
   * Verifies the 6-digit OTP against the backend (Redis).
   * On success advances step to 'done'.
   * Returns true on success, null on failure.
   */
  async function verifyCode() {
    setError(null)

    const code = otp.trim()
    if (!/^\d{6}$/.test(code)) {
      setError('Enter the 6-digit code from your SMS')
      return null
    }

    setLoading(true)
    try {
      const { error: verifyErr } = await verifyOtp(phone.trim(), code)
      if (verifyErr) {
        setError(verifyErr)
        return null
      }
      setStep('done')
      return true
    } finally {
      setLoading(false)
    }
  }

  /** Reset back to the phone-entry step (e.g. user wants to change number) */
  function reset() {
    setStep('phone')
    setPhone('')
    setOtp('')
    setError(null)
  }

  return {
    step,       // 'phone' | 'otp' | 'done'
    phone, setPhone,
    otp,   setOtp,
    sendCode,
    verifyCode,
    reset,
    loading,
    error,
  }
}
