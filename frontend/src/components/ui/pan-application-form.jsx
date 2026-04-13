import { useState, useRef } from 'react'
import { ChevronLeft, ChevronRight, Upload, CheckCircle2, ImageIcon, CreditCard, Car, Loader2, User, Mail, IndianRupee, Briefcase, X } from 'lucide-react'

// ── Designation classifier ────────────────────────────────────────
const INCOME_OPTIONS = [
  { id: 'salary', label: 'Salaried', icon: '💼', desc: 'Employed by a company or organisation' },
  { id: 'business', label: 'Business / Profession', icon: '🏢', desc: 'Self-employed, freelancer, or business owner' },
  { id: 'house_property', label: 'House Property', icon: '🏠', desc: 'Rental income from property' },
  { id: 'capital_gains', label: 'Capital Gains', icon: '📈', desc: 'Income from sale of assets or investments' },
  { id: 'other', label: 'Other Sources', icon: '💡', desc: 'Interest, dividends, or miscellaneous income' },
  { id: 'no_income', label: 'No Income', icon: '🎓', desc: 'Student, homemaker, or currently unemployed' },
]

function classifyDesignation(incomeIds) {
  if (incomeIds.includes('salary')) return 'Salaried Individual'
  if (incomeIds.includes('business')) return 'Self-Employed / Business Person'
  if (incomeIds.includes('capital_gains')) return 'Investor'
  if (incomeIds.includes('house_property')) return 'Property Owner'
  if (incomeIds.includes('no_income')) return 'Non-earning Individual'
  return 'Individual'
}

// ── Document slots ────────────────────────────────────────────────
const DOC_SLOTS = [
  { id: 'aadhaar', label: 'Aadhaar Card', desc: 'Front & back scan or photo', icon: CreditCard, accept: '.pdf,.jpg,.jpeg,.png' },
  { id: 'driving_license', label: 'Driving License', desc: 'Valid license — front side', icon: Car, accept: '.pdf,.jpg,.jpeg,.png' },
  { id: 'photograph', label: 'Applicant Photograph', desc: 'Passport-size, white background', icon: ImageIcon, accept: '.jpg,.jpeg,.png' },
]

// ── Steps config ──────────────────────────────────────────────────
const STEPS = [
  { id: 'personal', title: 'Personal Details', icon: User },
  { id: 'income', title: 'Income Source', icon: IndianRupee },
  { id: 'contact', title: 'Contact Info', icon: Mail },
  { id: 'documents', title: 'Documents', icon: Briefcase },
]

// ── Input component ───────────────────────────────────────────────
function Field({ label, required, error, children }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-semibold text-white/50 uppercase tracking-wider">
        {label}{required && <span className="text-rose-400 ml-0.5">*</span>}
      </label>
      {children}
      {error && <p className="text-rose-400 text-xs">{error}</p>}
    </div>
  )
}

function TextInput({ value, onChange, placeholder, type = 'text' }) {
  return (
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-3 text-white text-sm placeholder-white/20 outline-none focus:border-violet-500/50 focus:bg-white/[0.06] transition-all"
    />
  )
}

// ── Doc upload slot ───────────────────────────────────────────────
function DocSlot({ slot, upload, preview, isLoading, error, onFile }) {
  const ref = useRef()
  const Icon = slot.icon
  const done = !!upload

  return (
    <div
      onClick={() => !done && !isLoading && ref.current?.click()}
      className={`relative rounded-xl border transition-all duration-200 overflow-hidden
        ${done ? 'border-emerald-500/30 bg-emerald-500/[0.04]' : 'border-white/[0.07] bg-white/[0.02] hover:bg-white/[0.05] cursor-pointer active:scale-[0.98]'}`}>
      <input ref={ref} type="file" accept={slot.accept} className="hidden"
        onChange={e => onFile(slot.id, e.target.files?.[0])} />
      <div className="flex items-center gap-3 p-3">
        <div className={`w-10 h-10 rounded-lg flex-shrink-0 overflow-hidden flex items-center justify-center ${done ? 'bg-emerald-500/10' : 'bg-white/[0.04]'}`}>
          {preview ? <img src={preview} alt="" className="w-full h-full object-cover" />
            : done ? <CheckCircle2 size={18} className="text-emerald-400" />
            : isLoading ? <Loader2 size={16} className="text-white/30 animate-spin" />
            : <Icon size={16} className="text-white/25" />}
        </div>
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-semibold ${done ? 'text-white' : 'text-white/70'}`}>{slot.label}</p>
          {done ? <p className="text-emerald-400 text-xs mt-0.5 truncate">{upload}</p>
            : error ? <p className="text-rose-400 text-xs mt-0.5">{error}</p>
            : <p className="text-white/25 text-xs mt-0.5">{slot.desc}</p>}
        </div>
        {!done && !isLoading && (
          <div className="flex-shrink-0 flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-white/[0.05] border border-white/[0.07] text-white/40 text-xs">
            <Upload size={10} /> Upload
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main form ─────────────────────────────────────────────────────
export function PanApplicationForm({ sessionId, onComplete, onCancel }) {
  const [step, setStep] = useState(0)
  const [errors, setErrors] = useState({})

  // Form data
  const [motherName, setMotherName] = useState('')
  const [salary, setSalary] = useState('')
  const [email, setEmail] = useState('')
  const [incomeTypes, setIncomeTypes] = useState([])

  // Docs
  const [uploads, setUploads] = useState({})
  const [previews, setPreviews] = useState({})
  const [docBusy, setDocBusy] = useState({})
  const [docErrors, setDocErrors] = useState({})

  const designation = classifyDesignation(incomeTypes)
  const docsUploaded = DOC_SLOTS.filter(s => uploads[s.id]).length
  const allDocsDone = docsUploaded === DOC_SLOTS.length

  function toggleIncome(id) {
    setIncomeTypes(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  function validate() {
    const e = {}
    if (step === 0) {
      if (!motherName.trim()) e.motherName = 'Required'
      if (!salary.trim()) e.salary = 'Required'
    }
    if (step === 1 && incomeTypes.length === 0) e.income = 'Select at least one'
    if (step === 2) {
      if (!email.trim()) e.email = 'Required'
      else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) e.email = 'Invalid email'
    }
    setErrors(e)
    return Object.keys(e).length === 0
  }

  function next() {
    if (!validate()) return
    if (step < STEPS.length - 1) setStep(s => s + 1)
    else if (allDocsDone) onComplete({ motherName, salary, email, incomeTypes, designation, uploads })
  }

  function back() {
    setErrors({})
    setStep(s => s - 1)
  }

  async function handleDocFile(slotId, file) {
    if (!file) return
    setDocBusy(p => ({ ...p, [slotId]: true }))
    setDocErrors(p => ({ ...p, [slotId]: null }))
    if (file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = e => setPreviews(p => ({ ...p, [slotId]: e.target.result }))
      reader.readAsDataURL(file)
    }
    try {
      const form = new FormData()
      form.append('session_id', sessionId || 'anonymous')
      form.append('doc_type', slotId)
      form.append('file', file)
      const res = await fetch('/api/upload', { method: 'POST', body: form })
      if (!res.ok) throw new Error()
      setUploads(p => ({ ...p, [slotId]: file.name }))
    } catch {
      setDocErrors(p => ({ ...p, [slotId]: 'Upload failed — try again' }))
      setPreviews(p => { const n = { ...p }; delete n[slotId]; return n })
    } finally {
      setDocBusy(p => ({ ...p, [slotId]: false }))
    }
  }

  const progress = ((step + (step === STEPS.length - 1 && allDocsDone ? 1 : 0)) / STEPS.length) * 100

  return (
    <div className="w-full rounded-2xl overflow-hidden my-2"
      style={{
        background: 'rgba(14, 10, 26, 0.95)',
        border: '1px solid rgba(255,255,255,0.07)',
        boxShadow: '0 8px 40px rgba(0,0,0,0.4)',
      }}>

      {/* Header */}
      <div className="px-4 pt-4 pb-3">
        <div className="flex items-center justify-between mb-3">
          <p className="text-white/40 text-xs font-mono">Step {step + 1} of {STEPS.length}</p>
          <button onClick={onCancel}
            className="w-7 h-7 rounded-full bg-white/[0.06] hover:bg-white/[0.12] active:scale-95 flex items-center justify-center transition-all"
            aria-label="Close form">
            <X size={14} className="text-white/50" />
          </button>
        </div>

        {/* Step pills */}
        <div className="flex gap-1.5 mb-3">
          {STEPS.map((s, idx) => (
            <div key={s.id} className={`flex-1 h-1 rounded-full transition-all duration-300 ${
              idx < step ? 'bg-violet-500' : idx === step ? 'bg-violet-400' : 'bg-white/[0.07]'
            }`} />
          ))}
        </div>

        <h3 className="text-white font-bold text-base" style={{ fontFamily: 'Archivo, sans-serif' }}>
          {STEPS[step].title}
        </h3>
      </div>

      {/* Step content */}
      <div className="px-4 pb-4 space-y-4">

        {/* ── Step 0: Personal ── */}
        {step === 0 && (
          <>
            <Field label="Mother's Name" required error={errors.motherName}>
              <TextInput value={motherName} onChange={setMotherName} placeholder="As per official records" />
            </Field>
            <Field label="Annual Income / Salary" required error={errors.salary}>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30 text-sm">₹</span>
                <input
                  type="text"
                  value={salary}
                  onChange={e => setSalary(e.target.value)}
                  placeholder="e.g. 5,00,000"
                  className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl pl-8 pr-4 py-3 text-white text-sm placeholder-white/20 outline-none focus:border-violet-500/50 focus:bg-white/[0.06] transition-all"
                />
              </div>
            </Field>
          </>
        )}

        {/* ── Step 1: Income source ── */}
        {step === 1 && (
          <div className="space-y-2">
            {errors.income && <p className="text-rose-400 text-xs">{errors.income}</p>}
            <p className="text-white/40 text-xs mb-3">Select all that apply — we'll classify your designation automatically.</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {INCOME_OPTIONS.map(opt => {
                const selected = incomeTypes.includes(opt.id)
                return (
                  <button key={opt.id} type="button" onClick={() => toggleIncome(opt.id)}
                    className={`text-left p-3 rounded-xl border transition-all duration-150 active:scale-[0.98]
                      ${selected
                        ? 'border-violet-500/50 bg-violet-500/10 text-white'
                        : 'border-white/[0.07] bg-white/[0.02] text-white/60 hover:bg-white/[0.05] hover:text-white/80'
                      }`}>
                    <div className="flex items-center gap-2.5">
                      <span className="text-base leading-none">{opt.icon}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold truncate">{opt.label}</p>
                        <p className="text-[11px] text-white/30 mt-0.5 leading-tight">{opt.desc}</p>
                      </div>
                      <div className={`w-4 h-4 rounded flex-shrink-0 border flex items-center justify-center transition-all
                        ${selected ? 'bg-violet-500 border-violet-500' : 'border-white/20'}`}>
                        {selected && <svg width="8" height="6" viewBox="0 0 8 6" fill="none"><path d="M1 3L3 5L7 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>}
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
            {incomeTypes.length > 0 && (
              <div className="mt-3 px-3 py-2 rounded-lg bg-violet-500/[0.08] border border-violet-500/20">
                <p className="text-violet-300 text-xs">
                  <span className="font-semibold">Classified as:</span> {designation}
                </p>
              </div>
            )}
          </div>
        )}

        {/* ── Step 2: Contact ── */}
        {step === 2 && (
          <Field label="Email Address" required error={errors.email}>
            <TextInput value={email} onChange={setEmail} placeholder="you@example.com" type="email" />
          </Field>
        )}

        {/* ── Step 3: Documents ── */}
        {step === 3 && (
          <div className="space-y-2.5">
            <p className="text-white/40 text-xs">Upload the following documents to complete your application.</p>
            {/* Progress */}
            <div className="flex items-center gap-2 mb-1">
              <div className="flex-1 h-1 rounded-full bg-white/[0.05]">
                <div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-purple-400 transition-all duration-500"
                  style={{ width: `${(docsUploaded / DOC_SLOTS.length) * 100}%` }} />
              </div>
              <span className="text-white/30 text-xs font-mono">{docsUploaded}/{DOC_SLOTS.length}</span>
            </div>
            {DOC_SLOTS.map(slot => (
              <DocSlot key={slot.id} slot={slot}
                upload={uploads[slot.id]} preview={previews[slot.id]}
                isLoading={docBusy[slot.id]} error={docErrors[slot.id]}
                onFile={handleDocFile} />
            ))}
          </div>
        )}
      </div>

      {/* Footer nav */}
      <div className="px-4 pb-4 flex items-center gap-2">
        {step > 0 && (
          <button onClick={back}
            className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] active:scale-95 border border-white/[0.07] text-white/60 hover:text-white text-sm font-medium transition-all">
            <ChevronLeft size={15} /> Back
          </button>
        )}
        <button
          onClick={next}
          disabled={step === STEPS.length - 1 && !allDocsDone}
          className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 active:scale-[0.98] disabled:opacity-30 disabled:cursor-not-allowed text-white text-sm font-bold transition-all shadow-lg shadow-purple-900/20"
          style={{ fontFamily: 'Archivo, sans-serif' }}>
          {step === STEPS.length - 1
            ? allDocsDone ? 'Submit Application →' : `Upload ${DOC_SLOTS.length - docsUploaded} more doc${DOC_SLOTS.length - docsUploaded > 1 ? 's' : ''}`
            : <><span>Continue</span><ChevronRight size={15} /></>
          }
        </button>
      </div>
    </div>
  )
}
