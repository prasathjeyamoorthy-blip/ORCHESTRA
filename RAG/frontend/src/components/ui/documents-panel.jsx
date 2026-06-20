import { useEffect, useState, useCallback } from 'react'
import { X, Download, FileText, Loader2, ShieldCheck, AlertCircle, Lock, Eye, EyeOff, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useDocumentDownload } from '../../hooks/useDocumentDownload'
import { supabase } from '../../lib/supabase'

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

// Map storage filename patterns → human-readable doc type label
function guessDocType(filename) {
  if (!filename) return null
  const f = filename.toLowerCase()
  if (f.includes('aadhaar') || f.includes('aadhar'))  return 'Aadhaar Card'
  if (f.includes('driving') || f.includes('license'))  return 'Driving License'
  if (f.includes('photo') || f.includes('photograph')) return 'Photograph'
  if (f.includes('pan'))                               return 'PAN Card'
  if (f.includes('passport'))                          return 'Passport'
  if (f.includes('voter'))                             return 'Voter ID'
  if (f.includes('birth'))                             return 'Birth Certificate'
  if (f.includes('income') || f.includes('salary'))   return 'Income Proof'
  return null
}

const DOC_ICONS = {
  'Aadhaar Card':       '🪪',
  'Driving License':    '🚗',
  'Photograph':         '📷',
  'PAN Card':           '💳',
  'Passport':           '📕',
  'Voter ID':           '🗳️',
  'Birth Certificate':  '📄',
  'Income Proof':       '💰',
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
  const [docs, setDocs]             = useState([])
  const [fetching, setFetching]     = useState(false)
  const [pendingDoc, setPendingDoc] = useState(null)
  const [pwError, setPwError]       = useState(null)
  const [userName, setUserName]     = useState('')

  // ── Load documents ──────────────────────────────────────────────
  const loadDocs = useCallback(async () => {
    setFetching(true)
    try {
      const result = await listDocuments(onNotLoggedIn)
      setDocs(result)
    } finally {
      setFetching(false)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Get current user's name for personalised header ─────────────
  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      if (!data?.user) return
      const name =
        data.user.user_metadata?.full_name ||
        data.user.user_metadata?.name ||
        data.user.email?.split('@')[0] ||
        ''
      setUserName(name)
    })
  }, [])

  // ── Fetch when panel opens ──────────────────────────────────────
  useEffect(() => {
    if (!open) return
    loadDocs()
  }, [open, loadDocs])

  // ── Realtime subscription — auto-refresh when a new row is inserted ──
  useEffect(() => {
    if (!open) return

    const channel = supabase
      .channel('document_meta_changes')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'document_meta' },
        () => loadDocs()
      )
      .on(
        'postgres_changes',
        { event: 'DELETE', schema: 'public', table: 'document_meta' },
        () => loadDocs()
      )
      .subscribe()

    return () => { supabase.removeChannel(channel) }
  }, [open, loadDocs])

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
      setPwError(error || 'Incorrect password.')
    }
  }

  const firstName = userName.split(' ')[0]

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
            <div>
              <span className="text-white text-sm font-semibold">Encrypted Documents</span>
              {firstName && (
                <p className="text-white/35 text-[11px] mt-0.5">
                  {firstName}'s secure vault
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Manual refresh */}
            <button
              onClick={loadDocs}
              disabled={fetching}
              className="p-1.5 rounded-lg text-white/25 hover:text-white/60 hover:bg-white/[0.06] transition-all disabled:opacity-30"
              title="Refresh"
            >
              <RefreshCw size={13} className={fetching ? 'animate-spin' : ''} />
            </button>
            <button onClick={onClose} className="text-white/30 hover:text-white/70 transition-colors p-1">
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Doc count summary */}
        {!fetching && docs.length > 0 && (
          <div className="px-5 py-2.5 border-b border-white/[0.04] flex items-center justify-between">
            <span className="text-white/30 text-[11px]">
              {docs.length} file{docs.length !== 1 ? 's' : ''} stored
            </span>
            <span className="text-emerald-400/60 text-[10px] flex items-center gap-1">
              <ShieldCheck size={10} /> End-to-end encrypted
            </span>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
          {fetching && (
            <div className="flex items-center justify-center py-12 text-white/30">
              <Loader2 size={20} className="animate-spin" />
            </div>
          )}

          {!fetching && docs.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
              <div className="w-14 h-14 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center">
                <FileText size={24} className="text-white/15" />
              </div>
              <div>
                <p className="text-white/40 text-sm font-medium">No documents yet</p>
                {firstName && (
                  <p className="text-white/20 text-xs mt-1">
                    {firstName}, upload via the chat to store them here
                  </p>
                )}
                {!firstName && (
                  <p className="text-white/20 text-xs mt-1 max-w-[200px]">
                    Files you upload via the chat are encrypted and stored here
                  </p>
                )}
              </div>
            </div>
          )}

          {docs.map(doc => {
            const docType = guessDocType(doc.originalFilename)
            const icon    = DOC_ICONS[docType] || '📄'
            return (
              <div key={doc.id}
                className="flex items-center gap-3 bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] rounded-xl px-3 py-3 transition-all group">
                {/* Icon */}
                <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-white/[0.05] flex items-center justify-center text-base">
                  {icon}
                </div>

                <div className="flex-1 min-w-0">
                  {/* Doc type badge */}
                  {docType && (
                    <p className="text-emerald-400/70 text-[10px] font-semibold uppercase tracking-wider mb-0.5">
                      {docType}
                    </p>
                  )}
                  {/* Filename */}
                  <p className="text-white/80 text-xs font-medium truncate">{doc.originalFilename}</p>
                  {/* Meta */}
                  <p className="text-white/30 text-[10px] mt-0.5">
                    {formatBytes(doc.fileSizeBytes)}
                    {doc.fileSizeBytes && doc.createdAt ? ' · ' : ''}
                    {formatDate(doc.createdAt)}
                  </p>
                </div>

                {/* Download */}
                <button
                  onClick={() => handleDownloadClick(doc)}
                  className="flex-shrink-0 p-1.5 rounded-lg text-white/25 hover:text-white hover:bg-white/[0.08] transition-all opacity-0 group-hover:opacity-100"
                  title="Decrypt and download"
                >
                  <Download size={14} />
                </button>
              </div>
            )
          })}
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
