import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Loader2, CheckCircle2, XCircle } from 'lucide-react'

/**
 * Handles Supabase email-verification redirects.
 *
 * Supabase v2 (PKCE flow) redirects with:  ?code=XXXX
 * Older implicit flow redirects with:      #access_token=XXXX
 *
 * We handle both:
 *  - PKCE: call exchangeCodeForSession(code) → get session
 *  - Implicit: onAuthStateChange fires SIGNED_IN automatically
 */
export default function Verify({ onVerified }) {
  const [status, setStatus] = useState('verifying')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    let cancelled = false

    async function handleVerification() {
      const params = new URLSearchParams(window.location.search)
      const code = params.get('code')

      // ── PKCE flow (Supabase v2 default) ──────────────────────
      if (code) {
        const { data, error } = await supabase.auth.exchangeCodeForSession(code)
        if (cancelled) return
        if (error || !data?.session) {
          setErrorMsg(error?.message || 'Verification failed. The link may have expired.')
          setStatus('error')
          return
        }
        succeed(data.session)
        return
      }

      // ── Implicit / hash flow (older Supabase) ─────────────────
      // onAuthStateChange will fire SIGNED_IN once Supabase parses the hash
      const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
        if (cancelled) return
        if (event === 'SIGNED_IN' && session) {
          succeed(session)
        }
      })

      // Timeout fallback — if nothing fires in 8s, show error
      const timeout = setTimeout(() => {
        if (cancelled) return
        subscription.unsubscribe()
        setErrorMsg('Verification link may have expired. Please try signing up again.')
        setStatus('error')
      }, 8000)

      return () => {
        subscription.unsubscribe()
        clearTimeout(timeout)
      }
    }

    function succeed(session) {
      setStatus('success')
      setTimeout(() => {
        if (cancelled) return
        onVerified({
          id: session.user.id,
          email: session.user.email,
          display_name: session.user.user_metadata?.display_name,
        })
      }, 900)
    }

    handleVerification()
    return () => { cancelled = true }
  }, [onVerified])

  return (
    <div className="fixed inset-0 flex items-center justify-center"
      style={{ background: '#050508', fontFamily: 'Inter, sans-serif' }}>
      <div className="flex flex-col items-center gap-4 text-center px-6">
        {status === 'verifying' && (
          <>
            <Loader2 size={36} className="text-violet-400 animate-spin" />
            <p className="text-white/60 text-sm">Verifying your email…</p>
          </>
        )}
        {status === 'success' && (
          <>
            <CheckCircle2 size={36} className="text-emerald-400" />
            <p className="text-white text-sm font-semibold">Email verified! Taking you in…</p>
          </>
        )}
        {status === 'error' && (
          <>
            <XCircle size={36} className="text-rose-400" />
            <p className="text-white/80 text-sm">{errorMsg}</p>
            <button
              onClick={() => window.location.replace('/')}
              className="mt-2 text-xs text-violet-400 hover:text-violet-300 underline underline-offset-2">
              Back to home
            </button>
          </>
        )}
      </div>
    </div>
  )
}
