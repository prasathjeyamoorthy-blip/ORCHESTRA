import { useEffect, useState } from 'react'
import { X, Download, FileText, Loader2, ShieldCheck, AlertCircle, Lock, Eye, EyeOff } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useDocumentDownload } from '../../hooks/useDocumentDownload'

function formatBytes(n) {
  if (!n) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

// ── Password confirmation modal ───────────────────────────────────
function PasswordModal({ doc, onConfirm, onCancel, error, loading }) {
  const [password, setPassword] = useState('')
  const [show, setShow]         = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    if (!password) return
    onConfirm(password)
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center px-4"
      style={{ background: 'rgba(3,3,8,0.85)' }}>
      <div className="w-full max-w-sm rounded-2xl border border-white/[0.08] shadow-2xl p-6 space-y-4"
        style={{ background: 'rgba(10,8,22,0.98)' }}>

        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center flex-shrink-0">
            <Lock size={15} className="text-amber-400" />
          </div>
          <div>
            <p className="text-white text-sm font-semibold">Confirm your password</p>
            <p className="text-white/40 text-xs mt-0.5 truncate max-w-[220px]">{doc.originalFilename}</p>
          </div>
        </div>

        <p className="text-white/40 text-xs leading-relaxed">
          Enter your account password to decrypt and download this file.
          Your password is never sent to any server.
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
              Cancel
            </button>
            <button type="submit" disabled={loading || !password}
              className="flex-1 h-9 rounded-lg bg-white text-black text-xs font-semibold flex items-center justify-center gap-1.5 hover:bg-white/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all">
              {loading ? <Loader2 size={13} className="animate-spin" /> : <><Download size={13} /> Decrypt & Download</>}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Main panel ────────────────────────────────────────────────────
export function DocumentsPanel({ open, onClose, onNotLoggedIn }) {
  const { listDocuments, download, downloading, error } = useDocumentDownload()
  const [docs, setDocs]           = useState([])
  const [fetching, setFetching]   = useState(false)
  const [pendingDoc, setPendingDoc] = useState(null)   // doc waiting for password
  const [pwError, setPwError]     = useState(null)

  useEffect(() => {
    if (!open) return
    setFetching(true)
    listDocuments(onNotLoggedIn)
      .then(setDocs)
      .finally(() => setFetching(false))
  }, [open])

  function handleDownloadClick(doc) {
    setPwError(null)
    setPendingDoc(doc)
  }

  async function handlePasswordConfirm(password) {
    setPwError(null)
    const ok = await download(pendingDoc, password, onNotLoggedIn)
    if (ok) {
      setPendingDoc(null)
    } else {
      // error is set inside the hook — mirror it to the modal
      setPwError(error || 'Incorrect password.')
    }
  }

  return (
    <>
      {/* Backdrop */}
      {open && (
        <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      )}

      {/* Password modal */}
      {pendingDoc && (
        <PasswordModal
          doc={pendingDoc}
          onConfirm={handlePasswordConfirm}
          onCancel={() => { setPendingDoc(null); setPwError(null) }}
          error={pwError}
          loading={downloading}
        />
      )}

      {/* Panel */}
      <div className={cn(
        'fixed top-0 right-0 h-full z-50 w-80 sm:w-96 flex flex-col',
        'bg-[#0d0d18] border-l border-white/[0.07] shadow-2xl',
        'transition-transform duration-300',
        open ? 'translate-x-0' : 'translate-x-full'
      )}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06]">
          <div className="flex items-center gap-2">
            <ShieldCheck size={15} className="text-emerald-400" />
            <span className="text-white text-sm font-semibold">Encrypted Documents</span>
          </div>
          <button onClick={onClose} className="text-white/30 hover:text-white/70 transition-colors">
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
          {fetching && (
            <div className="flex items-center justify-center py-12 text-white/30">
              <Loader2 size={20} className="animate-spin" />
            </div>
          )}

          {!fetching && docs.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
              <FileText size={32} className="text-white/10" />
              <p className="text-white/30 text-sm">No documents yet</p>
              <p className="text-white/20 text-xs max-w-[200px]">
                Files you upload via the chat are encrypted and stored here
              </p>
            </div>
          )}

          {docs.map(doc => (
            <div key={doc.id}
              className="flex items-center gap-3 bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] rounded-xl px-3 py-3 transition-all group">
              <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-white/[0.05] flex items-center justify-center">
                <FileText size={14} className="text-white/40" />
              </div>

              <div className="flex-1 min-w-0">
                <p className="text-white/80 text-xs font-medium truncate">{doc.originalFilename}</p>
                <p className="text-white/30 text-[10px] mt-0.5">
                  {formatBytes(doc.fileSizeBytes)} · {formatDate(doc.createdAt)}
                </p>
              </div>

              <button
                onClick={() => handleDownloadClick(doc)}
                className="flex-shrink-0 p-1.5 rounded-lg text-white/30 hover:text-white hover:bg-white/[0.08] transition-all"
                title="Decrypt and download"
              >
                <Download size={14} />
              </button>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-white/[0.06]">
          <p className="text-white/20 text-[10px] text-center leading-relaxed">
            Password required to decrypt each download.<br />
            Your password never leaves your browser.
          </p>
        </div>
      </div>
    </>
  )
}
