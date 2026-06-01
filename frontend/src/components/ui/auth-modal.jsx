import { useState } from 'react'
import { motion, AnimatePresence, useMotionValue, useTransform } from 'framer-motion'
import { Mail, Lock, Eye, EyeClosed, ArrowRight, User, Loader2, Phone, KeyRound } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '../../hooks/useAuth'
import { usePhoneOtp } from '../../hooks/usePhoneOtp'

function Input({ className, type, ...props }) {
  return (
    <input
      type={type}
      className={cn(
        'flex h-10 w-full min-w-0 rounded-lg border bg-white/5 border-transparent px-3 py-1 text-sm text-white placeholder:text-white/30 outline-none transition-colors',
        'focus:border-white/20 focus:bg-white/10',
        'disabled:pointer-events-none disabled:opacity-50',
        className
      )}
      {...props}
    />
  )
}

// Border beams — use translate instead of top/left/right/bottom to stay on GPU
function BorderBeams() {
  const base = 'absolute bg-gradient-to-r from-transparent via-white/70 to-transparent pointer-events-none'
  return (
    <div className="absolute -inset-px rounded-2xl overflow-hidden pointer-events-none" aria-hidden>
      {/* top */}
      <motion.div
        className={cn(base, 'h-px w-1/2 top-0')}
        initial={{ x: '-100%' }}
        animate={{ x: '300%' }}
        transition={{ duration: 3, ease: 'linear', repeat: Infinity, repeatDelay: 0.8 }}
      />
      {/* bottom */}
      <motion.div
        className={cn(base, 'h-px w-1/2 bottom-0 rotate-180')}
        initial={{ x: '-100%' }}
        animate={{ x: '300%' }}
        transition={{ duration: 3, ease: 'linear', repeat: Infinity, repeatDelay: 0.8, delay: 1.5 }}
      />
      {/* left — rotated vertical beam */}
      <motion.div
        className={cn(base, 'w-px h-1/2 left-0 bg-gradient-to-b')}
        initial={{ y: '-100%' }}
        animate={{ y: '300%' }}
        transition={{ duration: 3, ease: 'linear', repeat: Infinity, repeatDelay: 0.8, delay: 0.75 }}
      />
      {/* right */}
      <motion.div
        className={cn(base, 'w-px h-1/2 right-0 bg-gradient-to-b')}
        initial={{ y: '-100%' }}
        animate={{ y: '300%' }}
        transition={{ duration: 3, ease: 'linear', repeat: Infinity, repeatDelay: 0.8, delay: 2.25 }}
      />
    </div>
  )
}

export function AuthModal({ onClose, onLogin, initialTab = 'login' }) {
  const [tab, setTab] = useState(initialTab)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
  const [focusedInput, setFocusedInput] = useState(null)
  const [errors, setErrors] = useState({})
  const [serverMsg, setServerMsg] = useState('')
  const [serverOk, setServerOk] = useState(false)

  // OTP step — shown after successful email+password auth
  // pendingUser holds the user object while we wait for phone verification
  const [pendingUser, setPendingUser] = useState(null)
  const {
    step: otpStep, phone, setPhone, otp, setOtp,
    sendCode, verifyCode, reset: resetOtp, loading: otpLoading, error: otpError,
  } = usePhoneOtp()

  const { login, register, loading, error: authError } = useAuth()

  // 3D tilt — only on non-touch devices
  const mouseX = useMotionValue(0)
  const mouseY = useMotionValue(0)
  const rotateX = useTransform(mouseY, [-300, 300], [6, -6])
  const rotateY = useTransform(mouseX, [-300, 300], [-6, 6])

  function handleMouseMove(e) {
    const rect = e.currentTarget.getBoundingClientRect()
    mouseX.set(e.clientX - rect.left - rect.width / 2)
    mouseY.set(e.clientY - rect.top - rect.height / 2)
  }
  function handleMouseLeave() { mouseX.set(0); mouseY.set(0) }

  function switchTab(t) {
    setTab(t); setErrors({}); setServerMsg(''); setServerOk(false)
    setPassword(''); setConfirm('')
  }

  function validate() {
    const e = {}
    if (!email.trim()) e.email = 'Required'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) e.email = 'Invalid email'
    if (!password) e.password = 'Required'
    if (tab === 'signup') {
      if (password.length < 8) e.password = 'Min 8 characters'
      else if (!/[A-Z]/.test(password)) e.password = 'Needs an uppercase letter'
      else if (!/[0-9]/.test(password)) e.password = 'Needs a number'
      else if (!/[^A-Za-z0-9]/.test(password)) e.password = 'Needs a special character'
      if (password !== confirm) e.confirm = 'Passwords do not match'
    }
    setErrors(e)
    return Object.keys(e).length === 0
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setServerMsg(''); setServerOk(false)
    if (!validate()) return

    if (tab === 'login') {
      const ok = await login(email, password)
      if (!ok) return   // authError is set inside the hook
      // PHONE VERIFICATION DISABLED - Login directly without OTP
      const { supabase } = await import('../../lib/supabase')
      const { data: { user } } = await supabase.auth.getUser()
      const userData = { 
        id: user.id, 
        email: user.email, 
        display_name: user.user_metadata?.display_name ?? user.email 
      }
      onLogin(userData)  // Complete login immediately
    } else {
      const ok = await register(email, password)
      if (!ok) return
      // PHONE VERIFICATION DISABLED - Register and login directly without OTP
      const { supabase } = await import('../../lib/supabase')
      const { data: { user } } = await supabase.auth.getUser()
      const userData = { 
        id: user.id, 
        email: user.email, 
        display_name: displayName || user.email 
      }
      onLogin(userData)  // Complete login immediately
    }
  }

  // ── OTP: send SMS code ───────────────────────────────────────────
  async function handleSendOtp(e) {
    e.preventDefault()
    await sendCode()
  }

  // ── OTP: verify code and complete login ──────────────────────────
  async function handleVerifyOtp(e) {
    e.preventDefault()
    const result = await verifyCode()
    if (!result) return  // error shown by hook

    // OTP verified — complete the login flow immediately
    // (session cookies were already set during email+password login)
    onLogin(pendingUser)
  }

  const inputRow = (id, icon, inputType, placeholder, value, setter) => {
    const Icon = icon
    const focused = focusedInput === id
    return (
      <div className={cn('relative', focused && 'z-10')}>
        <div className="relative flex items-center rounded-lg overflow-hidden">
          <Icon className={cn(
            'absolute left-3 w-4 h-4 pointer-events-none transition-colors duration-200',
            focused ? 'text-white' : 'text-white/40'
          )} />
          <Input
            type={id === 'password' || id === 'confirm' ? (showPw ? 'text' : 'password') : inputType}
            placeholder={placeholder}
            value={value}
            onChange={e => setter(e.target.value)}
            onFocus={() => setFocusedInput(id)}
            onBlur={() => setFocusedInput(null)}
            className="pl-10 pr-10"
          />
          {(id === 'password' || id === 'confirm') && (
            <button type="button" onClick={() => setShowPw(p => !p)}
              className="absolute right-3 text-white/40 hover:text-white transition-colors duration-200">
              {showPw ? <Eye className="w-4 h-4" /> : <EyeClosed className="w-4 h-4" />}
            </button>
          )}
        </div>
        {errors[id] && <p className="text-rose-400 text-[11px] mt-1 pl-1">{errors[id]}</p>}
      </div>
    )
  }

  return (
    // Backdrop — no backdrop-filter blur (causes flicker), use dark overlay instead
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4 py-6 overflow-y-auto"
      style={{ background: 'rgba(3,3,8,0.88)' }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      {/* Static background glow — no animation, no blur */}
      <div className="fixed inset-0 pointer-events-none" aria-hidden>
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[70vw] h-[45vh] rounded-b-[50%] bg-purple-500/10"
          style={{ filter: 'blur(60px)' }} />
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[50vw] h-[40vh] rounded-t-full bg-violet-600/10"
          style={{ filter: 'blur(50px)' }} />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.96 }}
        transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
        className="relative w-full max-w-sm mx-auto will-change-transform"
        style={{ perspective: 1200 }}
      >
        <motion.div
          style={{ rotateX, rotateY }}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          className="relative"
        >
          <BorderBeams />

          {/* Card — no backdrop-blur to prevent flicker */}
          <div className="relative rounded-2xl border border-white/[0.07] shadow-2xl overflow-hidden"
            style={{ background: 'rgba(8,6,18,0.97)' }}>

            {/* ── Header ── */}
            <div className="px-6 pt-6 pb-4 text-center space-y-2">
              {/* Logo */}
              <div className="mx-auto w-11 h-11 rounded-full border border-white/10 bg-white/[0.06] flex items-center justify-center">
                <span className="text-lg font-black text-white/90" style={{ fontFamily: 'Archivo, sans-serif' }}>P</span>
              </div>

              <h1 className="text-xl font-black text-white" style={{ fontFamily: 'Archivo, sans-serif' }}>
                {pendingUser
                  ? otpStep === 'otp' ? 'Enter OTP' : 'Verify your phone'
                  : tab === 'login' ? 'Welcome back' : 'Create account'}
              </h1>
              <p className="text-white/40 text-xs">
                {pendingUser
                  ? otpStep === 'otp'
                    ? `We sent a 6-digit code to ${phone}`
                    : 'One last step — verify your phone number'
                  : tab === 'login' ? 'Sign in to your PAN assistant' : 'Get started with PAN services'}
              </p>
            </div>

            {/* ── OTP flow (shown after password auth succeeds) ── */}
            {pendingUser ? (
              <div className="px-6 pb-6 space-y-3">

                {/* Step 1: phone number entry */}
                {otpStep === 'phone' && (
                  <form onSubmit={handleSendOtp} className="space-y-3">
                    <div className="relative flex items-center rounded-lg overflow-hidden">
                      <Phone className="absolute left-3 w-4 h-4 text-white/40 pointer-events-none" />
                      {/* Fixed +91 country code prefix */}
                      <span className="absolute left-9 text-sm text-white/60 pointer-events-none select-none">+91</span>
                      <Input
                        type="tel"
                        placeholder="9876543210"
                        value={phone.replace(/^\+91/, '')}
                        onChange={e => {
                          // Strip any non-digit characters and prepend +91
                          const digits = e.target.value.replace(/\D/g, '').slice(0, 10)
                          setPhone(digits ? `+91${digits}` : '')
                        }}
                        className="pl-16"
                        autoFocus
                        maxLength={10}
                      />
                    </div>
                    <p className="text-white/30 text-[11px]">
                      Enter your 10-digit mobile number
                    </p>
                    {otpError && (
                      <p className="text-rose-400 text-xs px-3 py-2 rounded-lg border border-rose-500/20 bg-rose-500/10">
                        {otpError}
                      </p>
                    )}
                    <button
                      type="submit"
                      disabled={otpLoading}
                      className="w-full h-10 rounded-lg bg-white text-black text-sm font-semibold flex items-center justify-center gap-1.5 hover:bg-white/90 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150"
                    >
                      {otpLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <>Send OTP <ArrowRight className="w-3.5 h-3.5" /></>}
                    </button>
                    <button
                      type="button"
                      onClick={() => { setPendingUser(null); resetOtp() }}
                      className="w-full text-xs text-white/40 hover:text-white/70 transition-colors"
                    >
                      ← Back to sign in
                    </button>
                  </form>
                )}

                {/* Step 2: OTP code entry */}
                {otpStep === 'otp' && (
                  <form onSubmit={handleVerifyOtp} className="space-y-3">
                    <div className="relative flex items-center rounded-lg overflow-hidden">
                      <KeyRound className="absolute left-3 w-4 h-4 text-white/40 pointer-events-none" />
                      <Input
                        type="text"
                        inputMode="numeric"
                        maxLength={6}
                        placeholder="6-digit code"
                        value={otp}
                        onChange={e => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                        className="pl-10 tracking-[0.3em] text-center"
                        autoFocus
                      />
                    </div>
                    {otpError && (
                      <p className="text-rose-400 text-xs px-3 py-2 rounded-lg border border-rose-500/20 bg-rose-500/10">
                        {otpError === 'Token has expired or is invalid'
                          ? 'Incorrect or expired code. Check your SMS and try again, or resend.'
                          : otpError}
                      </p>
                    )}
                    <button
                      type="submit"
                      disabled={otpLoading || otp.length !== 6}
                      className="w-full h-10 rounded-lg bg-white text-black text-sm font-semibold flex items-center justify-center gap-1.5 hover:bg-white/90 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150"
                    >
                      {otpLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <>Verify <ArrowRight className="w-3.5 h-3.5" /></>}
                    </button>
                    <button
                      type="button"
                      onClick={() => resetOtp()}
                      className="w-full text-xs text-white/40 hover:text-white/70 transition-colors"
                    >
                      ← Change phone number
                    </button>
                    {/* Resend OTP link */}
                    <button
                      type="button"
                      onClick={async () => { setOtp(''); await sendCode() }}
                      disabled={otpLoading}
                      className="w-full text-xs text-violet-400 hover:text-violet-300 transition-colors disabled:opacity-40"
                    >
                      Didn't receive it? Resend OTP
                    </button>
                  </form>
                )}
              </div>
            ) : (
              /* ── Email + password form ── */
              <form onSubmit={handleSubmit} className="px-6 pb-6 space-y-3">

              {/* Display name — shown only for signup, no height animation (causes reflow) */}
              <div className={cn('overflow-hidden transition-all duration-200',
                tab === 'signup' ? 'max-h-20 opacity-100' : 'max-h-0 opacity-0 pointer-events-none')}>
                {inputRow('name', User, 'text', 'Display name (optional)', displayName, setDisplayName)}
              </div>

              {inputRow('email', Mail, 'email', 'Email address', email, setEmail)}
              {inputRow('password', Lock, 'password',
                tab === 'signup' ? '8+ chars, uppercase, number, symbol' : 'Password',
                password, setPassword)}

              {/* Confirm password */}
              <div className={cn('overflow-hidden transition-all duration-200',
                tab === 'signup' ? 'max-h-20 opacity-100' : 'max-h-0 opacity-0 pointer-events-none')}>
                {inputRow('confirm', Lock, 'password', 'Confirm password', confirm, setConfirm)}
              </div>

              {/* Remember me / Forgot */}
              {tab === 'login' && (
                <div className="flex items-center justify-between pt-0.5">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <div className="relative">
                      <input type="checkbox" checked={rememberMe} onChange={() => setRememberMe(p => !p)}
                        className="appearance-none h-4 w-4 rounded border border-white/20 bg-white/5 checked:bg-white checked:border-white focus:outline-none transition-colors duration-150" />
                      {rememberMe && (
                        <div className="absolute inset-0 flex items-center justify-center text-black pointer-events-none">
                          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        </div>
                      )}
                    </div>
                    <span className="text-xs text-white/50">Remember me</span>
                  </label>
                  <button type="button" className="text-xs text-white/50 hover:text-white transition-colors duration-150">
                    Forgot password?
                  </button>
                </div>
              )}

              {/* Server message */}
              {(serverMsg || authError) && (
                <p className={cn('text-xs px-3 py-2 rounded-lg border',
                  serverOk
                    ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                    : 'text-rose-400 bg-rose-500/10 border-rose-500/20'
                )}>
                  {serverMsg || authError}
                </p>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                className="w-full mt-1 h-10 rounded-lg bg-white text-black text-sm font-semibold flex items-center justify-center gap-1.5 hover:bg-white/90 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150"
              >
                {loading
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <>{tab === 'login' ? 'Sign in' : 'Create account'} <ArrowRight className="w-3.5 h-3.5" /></>
                }
              </button>

              {/* Divider */}
              <div className="flex items-center gap-3 py-1">
                <div className="flex-1 border-t border-white/[0.06]" />
                <span className="text-[11px] text-white/30">or</span>
                <div className="flex-1 border-t border-white/[0.06]" />
              </div>

              {/* Google */}
              <button
                type="button"
                className="w-full h-10 rounded-lg bg-white/5 border border-white/10 hover:border-white/20 hover:bg-white/[0.08] flex items-center justify-center gap-2 text-xs font-medium text-white/70 hover:text-white transition-all duration-150"
              >
                <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Continue with Google
              </button>

              {/* Switch tab */}
              <p className="text-center text-xs text-white/40 pt-1">
                {tab === 'login' ? "Don't have an account? " : 'Already have an account? '}
                <button type="button" onClick={() => switchTab(tab === 'login' ? 'signup' : 'login')}
                  className="text-white/70 hover:text-white font-semibold transition-colors duration-150 underline underline-offset-2">
                  {tab === 'login' ? 'Sign up' : 'Sign in'}
                </button>
              </p>
            </form>
            )}
          </div>
        </motion.div>
      </motion.div>
    </div>
  )
}
