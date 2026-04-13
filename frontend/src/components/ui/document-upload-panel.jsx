import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, CheckCircle2, ImageIcon, CreditCard, Car, Loader2, Upload, ChevronLeft, ChevronRight } from 'lucide-react'
import { GlowCard } from './spotlight-card'

const STAGES = [
  {
    id: 'aadhaar',
    label: 'Aadhaar Card',
    subtitle: 'Identity & Address Proof',
    desc: 'Upload the front and back of your Aadhaar card. Serves as proof of identity, address, and date of birth.',
    icon: CreditCard,
    accept: '.pdf,.jpg,.jpeg,.png',
    glowColor: 'blue',
    accent: '#818cf8',
  },
  {
    id: 'driving_license',
    label: 'Driving License',
    subtitle: 'Secondary Identity Proof',
    desc: 'Upload the front side of your valid driving license. Accepted as an alternative identity and address proof.',
    icon: Car,
    accept: '.pdf,.jpg,.jpeg,.png',
    glowColor: 'purple',
    accent: '#a78bfa',
  },
  {
    id: 'photograph',
    label: 'Applicant Photograph',
    subtitle: 'Passport-size Photo',
    desc: 'Upload a recent passport-size photograph with a white background. This will be printed on your PAN card.',
    icon: ImageIcon,
    accept: '.jpg,.jpeg,.png',
    glowColor: 'orange',
    accent: '#fb7185',
  },
]

const SWIPE_THRESHOLD = 60

export function DocumentUploadPanel({ sessionId, onClose, onAllUploaded }) {
  const [activeIdx, setActiveIdx] = useState(0)
  const [uploads, setUploads] = useState({})
  const [previews, setPreviews] = useState({})
  const [busy, setBusy] = useState({})
  const [errors, setErrors] = useState({})
  const [dragStart, setDragStart] = useState(null)
  const [dragOffset, setDragOffset] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const refs = useRef({})

  const uploaded = STAGES.filter(s => uploads[s.id]).length
  const allDone = uploaded === STAGES.length

  async function handleFile(stageId, file) {
    if (!file) return
    setBusy(p => ({ ...p, [stageId]: true }))
    setErrors(p => ({ ...p, [stageId]: null }))
    if (file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = e => setPreviews(p => ({ ...p, [stageId]: e.target.result }))
      reader.readAsDataURL(file)
    }
    try {
      const form = new FormData()
      form.append('session_id', sessionId || 'anonymous')
      form.append('doc_type', stageId)
      form.append('file', file)
      const res = await fetch('/api/upload', { method: 'POST', body: form })
      if (!res.ok) throw new Error()
      setUploads(p => ({ ...p, [stageId]: file.name }))
    } catch {
      setErrors(p => ({ ...p, [stageId]: 'Upload failed — try again' }))
      setPreviews(p => { const n = { ...p }; delete n[stageId]; return n })
    } finally {
      setBusy(p => ({ ...p, [stageId]: false }))
    }
  }

  function goNext() { if (activeIdx < STAGES.length - 1) setActiveIdx(i => i + 1) }
  function goPrev() { if (activeIdx > 0) setActiveIdx(i => i - 1) }

  function onPointerDown(e) {
    setDragStart(e.clientX ?? e.touches?.[0]?.clientX)
    setIsDragging(true)
  }
  function onPointerMove(e) {
    if (!isDragging || dragStart === null) return
    setDragOffset((e.clientX ?? e.touches?.[0]?.clientX) - dragStart)
  }
  function onPointerUp() {
    if (dragOffset < -SWIPE_THRESHOLD) goNext()
    else if (dragOffset > SWIPE_THRESHOLD) goPrev()
    setDragStart(null); setDragOffset(0); setIsDragging(false)
  }

  const stage = STAGES[activeIdx]
  const done = !!uploads[stage.id]
  const loading = busy[stage.id]
  const err = errors[stage.id]
  const preview = previews[stage.id]
  const Icon = stage.icon

  return (
    <div className="w-full rounded-2xl overflow-hidden my-2 select-none"
      style={{ background: 'rgba(8,5,16,0.98)', border: '1px solid rgba(255,255,255,0.06)', boxShadow: '0 12px 48px rgba(0,0,0,0.7)' }}>

      {/* Hidden file inputs */}
      {STAGES.map(s => (
        <input key={s.id} ref={el => refs.current[s.id] = el}
          type="file" accept={s.accept} className="hidden"
          onChange={e => handleFile(s.id, e.target.files?.[0])} />
      ))}

      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-4 pb-3">
        <div>
          <p className="text-white/25 text-[11px] font-mono uppercase tracking-widest">
            Document {activeIdx + 1} of {STAGES.length}
          </p>
          <h3 className="text-white font-bold text-sm mt-0.5" style={{ fontFamily: 'Archivo, sans-serif' }}>
            Upload Documents
          </h3>
        </div>
        <button onClick={onClose}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 text-xs font-semibold transition-all active:scale-95">
          <X size={12} /> Exit
        </button>
      </div>

      {/* Stage dots */}
      <div className="flex items-center gap-2 px-4 mb-4">
        {STAGES.map((s, i) => (
          <button key={s.id} onClick={() => setActiveIdx(i)}>
            <div className={`rounded-full transition-all duration-300 ${i === activeIdx ? 'w-6 h-2' : 'w-2 h-2'} ${uploads[s.id] ? 'bg-emerald-400' : i === activeIdx ? 'bg-violet-400' : 'bg-white/15'}`} />
          </button>
        ))}
        <div className="flex-1 h-px bg-white/[0.05] ml-1" />
        <span className="text-white/25 text-[11px] font-mono">{uploaded}/{STAGES.length}</span>
      </div>

      {/* Swipeable GlowCard */}
      <div className="px-4 pb-4"
        onMouseDown={onPointerDown} onMouseMove={onPointerMove}
        onMouseUp={onPointerUp} onMouseLeave={onPointerUp}
        onTouchStart={onPointerDown} onTouchMove={onPointerMove} onTouchEnd={onPointerUp}>

        <AnimatePresence mode="wait">
          <motion.div key={stage.id}
            initial={{ opacity: 0, x: 60, scale: 0.96 }}
            animate={{ opacity: 1, x: dragOffset * 0.25, scale: 1 }}
            exit={{ opacity: 0, x: -60, scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 340, damping: 30 }}>

            <GlowCard glowColor={stage.glowColor} className="w-full cursor-grab active:cursor-grabbing">
              <div className="p-5">
                {/* Icon + title */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0"
                      style={{ background: `${stage.accent}15`, border: `1px solid ${stage.accent}30` }}>
                      {preview
                        ? <img src={preview} alt="" className="w-full h-full object-cover rounded-xl" />
                        : done
                          ? <CheckCircle2 size={22} className="text-emerald-400" />
                          : loading
                            ? <Loader2 size={20} className="animate-spin" style={{ color: stage.accent }} />
                            : <Icon size={20} style={{ color: stage.accent }} />
                      }
                    </div>
                    <div>
                      <p className="text-white font-bold text-sm" style={{ fontFamily: 'Archivo, sans-serif' }}>
                        {stage.label}
                      </p>
                      <p className="text-xs mt-0.5" style={{ color: `${stage.accent}90` }}>
                        {stage.subtitle}
                      </p>
                    </div>
                  </div>
                  {done && (
                    <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-400/10 border border-emerald-400/20 rounded-full px-2 py-0.5">
                      Uploaded
                    </span>
                  )}
                </div>

                {/* Description */}
                <p className="text-white/35 text-xs leading-relaxed mb-5">
                  {done ? `✓ ${uploads[stage.id]}` : err || stage.desc}
                </p>

                {/* Upload button */}
                {!done ? (
                  <button onClick={() => refs.current[stage.id]?.click()} disabled={loading}
                    className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm transition-all active:scale-[0.97] disabled:opacity-40"
                    style={{ background: `${stage.accent}15`, border: `1px solid ${stage.accent}30`, color: stage.accent }}>
                    {loading
                      ? <><Loader2 size={15} className="animate-spin" /> Uploading…</>
                      : <><Upload size={15} /> {err ? 'Try Again' : 'Upload File'}</>
                    }
                  </button>
                ) : (
                  <div className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold text-emerald-400 bg-emerald-400/8 border border-emerald-400/20">
                    <CheckCircle2 size={15} /> Done
                  </div>
                )}

                {/* Swipe hint */}
                <div className="flex justify-between mt-3">
                  <span className="text-[10px] text-white/15">{activeIdx > 0 ? '← swipe right' : ''}</span>
                  <span className="text-[10px] text-white/15">{activeIdx < STAGES.length - 1 ? 'swipe left →' : ''}</span>
                </div>
              </div>
            </GlowCard>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Nav */}
      <div className="flex items-center gap-2 px-4 pb-4">
        <button onClick={goPrev} disabled={activeIdx === 0}
          className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.07] text-white/50 hover:text-white text-xs font-medium transition-all active:scale-95 disabled:opacity-20 disabled:cursor-not-allowed">
          <ChevronLeft size={14} /> Prev
        </button>
        {allDone ? (
          <button onClick={() => { onAllUploaded?.(); onClose() }}
            className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 active:scale-[0.98] text-white text-sm font-bold transition-all"
            style={{ fontFamily: 'Archivo, sans-serif' }}>
            Submit All →
          </button>
        ) : (
          <button onClick={goNext} disabled={activeIdx === STAGES.length - 1}
            className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.07] text-white/50 hover:text-white text-xs font-medium transition-all active:scale-95 disabled:opacity-20 disabled:cursor-not-allowed">
            Next <ChevronRight size={14} />
          </button>
        )}
      </div>
    </div>
  )
}
