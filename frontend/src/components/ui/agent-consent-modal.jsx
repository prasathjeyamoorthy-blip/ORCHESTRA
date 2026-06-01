/**
 * AgentConsentModal — shown before any file is sent to the agent for processing.
 * User must enter their password to authorize agent access to the decrypted file.
 */
import { useState } from 'react'
import { ShieldAlert, Eye, EyeOff, Loader2, AlertCircle, FileText } from 'lucide-react'

export function AgentConsentModal({ files, onConfirm, onCancel, error, loading }) {
  const [password, setPassword] = useState('')
  const [show,     setShow]     = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    if (!password) return
    onConfirm(password)
  }

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center px-4"
      style={{ background: 'rgba(3,3,8,0.88)' }}>
      <div className="w-full max-w-sm rounded-2xl border border-white/[0.08] shadow-2xl p-6 space-y-4"
        style={{ background: 'rgba(10,8,22,0.98)' }}>

        {/* Header */}
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
            <ShieldAlert size={16} className="text-amber-400" />
          </div>
          <div>
            <p className="text-white text-sm font-semibold">Agent access request</p>
            <p className="text-white/40 text-xs mt-1 leading-relaxed">
              The assistant needs to read your document to process it.
              Enter your password to authorize.
            </p>
          </div>
        </div>

        {/* Files being accessed */}
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2.5 space-y-1.5">
          <p className="text-white/30 text-[10px] uppercase tracking-widest font-semibold mb-2">
            Files requesting access
          </p>
          {files.map((f, i) => (
            <div key={i} className="flex items-center gap-2">
              <FileText size={12} className="text-white/30 flex-shrink-0" />
              <span className="text-white/60 text-xs truncate">{f.name}</span>
            </div>
          ))}
        </div>

        <p className="text-white/25 text-[11px] leading-relaxed">
          Your password is used only in your browser to decrypt the file.
          It is never sent to any server. The agent receives only the decrypted content.
        </p>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="relative">
            <input
              type={show ? 'text' : 'password'}
              placeholder="Account password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoFocus
              className="w-full h-10 rounded-lg bg-white/[0.05] border border-white/[0.1] focus:border-white/30 px-3 pr-10 text-sm text-white placeholder:text-white/30 outline-none transition-colors"
            />
            <button type="button" onClick={() => setShow(p => !p)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors">
              {show ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>

          {error && (
            <div className="flex items-center gap-2 bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-2">
              <AlertCircle size={12} className="text-rose-400 flex-shrink-0" />
              <p className="text-rose-300 text-xs">{error}</p>
            </div>
          )}

          <div className="flex gap-2 pt-1">
            <button type="button" onClick={onCancel}
              className="flex-1 h-9 rounded-lg border border-white/[0.1] text-white/50 hover:text-white hover:border-white/20 text-xs font-medium transition-all">
              Deny
            </button>
            <button type="submit" disabled={loading || !password}
              className="flex-1 h-9 rounded-lg bg-amber-500 text-black text-xs font-semibold flex items-center justify-center gap-1.5 hover:bg-amber-400 disabled:opacity-40 disabled:cursor-not-allowed transition-all">
              {loading
                ? <Loader2 size={13} className="animate-spin" />
                : 'Authorize & Send'
              }
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
