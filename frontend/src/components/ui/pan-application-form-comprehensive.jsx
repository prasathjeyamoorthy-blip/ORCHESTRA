import { useState, useRef } from 'react'
import { Upload, CheckCircle2, ImageIcon, CreditCard, Car, Loader2, X, Check, AlertCircle } from 'lucide-react'

// ── Income Options ────────────────────────────────────────
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

// ── Document slots ────────────────────────────────────────
const DOC_SLOTS = [
  { id: 'aadhaar', label: 'Aadhaar Card', desc: 'Front & back scan or photo', icon: CreditCard, accept: '.pdf,.jpg,.jpeg,.png' },
  { id: 'driving_license', label: 'Driving License', desc: 'Valid license — front side', icon: Car, accept: '.pdf,.jpg,.jpeg,.png' },
  { id: 'photograph', label: 'Applicant Photograph', desc: 'Passport-size, white background', icon: ImageIcon, accept: '.jpg,.jpeg,.png' },
]

// ── Section Card ─────────────────────────────────────────
function SectionCard({ title, subtitle, icon: Icon, isComplete, children, errors }) {
  const hasErrors = errors && errors.length > 0
  
  return (
    <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] overflow-hidden">
      <div className={`px-5 py-4 flex items-center gap-3 border-b ${
        hasErrors ? 'border-rose-500/20 bg-rose-500/5' : isComplete ? 'border-emerald-500/20 bg-emerald-500/5' : 'border-white/[0.05]'
      }`}>
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
          hasErrors ? 'bg-rose-500/10' : isComplete ? 'bg-emerald-500/10' : 'bg-white/[0.05]'
        }`}>
          {hasErrors ? <AlertCircle size={18} className="text-rose-400" />
            : isComplete ? <Check size={18} className="text-emerald-400" />
            : <Icon size={18} className="text-white/40" />
          }
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-white font-bold text-sm">{title}</h3>
          <p className="text-white/40 text-xs mt-0.5">{subtitle}</p>
        </div>
      </div>
      <div className="px-5 py-4">
        {children}
      </div>
    </div>
  )
}

// ── Input Field ───────────────────────────────────────────
function Field({ label, required, error, children }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-semibold text-white/50 uppercase tracking-wider">
        {label}{required && <span className="text-rose-400 ml-0.5">*</span>}
      </label>
      {children}
      {error && <p className="text-rose-400 text-xs flex items-center gap-1"><AlertCircle size={12} />{error}</p>}
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

// ── Doc upload slot ───────────────────────────────────────
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

// ── Main Comprehensive Form ───────────────────────────────
export function PanApplicationFormComprehensive({ sessionId, initialValues, onComplete, onCancel }) {
  const iv = initialValues || {}
  const [errors, setErrors] = useState({})

  // Form data — pre-fill from initialValues
  const [motherName, setMotherName] = useState(iv.motherName || '')
  const [fatherName, setFatherName] = useState(iv.fatherName || '')
  const [salary, setSalary] = useState(iv.salary || '')
  const [email, setEmail] = useState(iv.email || '')
  const [phone, setPhone] = useState(iv.phone || '')
  const [address, setAddress] = useState(iv.address || '')
  const [city, setCity] = useState(iv.city || '')
  const [state, setState] = useState(iv.state || '')
  const [pincode, setPincode] = useState(iv.pincode || '')
  const [incomeTypes, setIncomeTypes] = useState(iv.incomeTypes || [])

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

  function validateAll() {
    const e = {}
    
    // Personal details
    if (!motherName.trim()) e.motherName = 'Required'
    if (!salary.trim()) e.salary = 'Required'
    
    // Income
    if (incomeTypes.length === 0) e.income = 'Select at least one income source'
    
    // Contact
    if (!email.trim()) e.email = 'Required'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) e.email = 'Invalid email'
    if (!phone.trim()) e.phone = 'Required'
    else if (!/^\d{10}$/.test(phone.replace(/\D/g, ''))) e.phone = 'Must be 10 digits'
    
    // Address
    if (!address.trim()) e.address = 'Required'
    if (!city.trim()) e.city = 'Required'
    if (!state.trim()) e.state = 'Required'
    if (!pincode.trim()) e.pincode = 'Required'
    else if (!/^\d{6}$/.test(pincode)) e.pincode = 'Must be 6 digits'
    
    // Documents
    if (!allDocsDone) e.documents = 'All documents are required'
    
    setErrors(e)
    return Object.keys(e).length === 0
  }

  function handleSubmit() {
    if (!validateAll()) return
    onComplete({ 
      motherName, fatherName, salary, email, phone, address, city, state, pincode,
      incomeTypes, designation, uploads 
    })
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

  // Section completeness
  const personalComplete = motherName.trim() && salary.trim()
  const incomeComplete = incomeTypes.length > 0
  const contactComplete = email.trim() && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) && phone.trim() && /^\d{10}$/.test(phone.replace(/\D/g, ''))
  const addressComplete = address.trim() && city.trim() && state.trim() && pincode.trim() && /^\d{6}$/.test(pincode)
  const docsComplete = allDocsDone

  const totalSections = 5
  const completedSections = [personalComplete, incomeComplete, contactComplete, addressComplete, docsComplete].filter(Boolean).length
  const overallProgress = (completedSections / totalSections) * 100

  return (
    <div className="w-full max-w-5xl mx-auto my-4">
      {/* Header Card */}
      <div className="rounded-2xl border border-white/[0.08] overflow-hidden mb-4"
        style={{
          background: 'rgba(14, 10, 26, 0.95)',
          boxShadow: '0 8px 40px rgba(0,0,0,0.4)',
        }}>
        <div className="px-6 py-5 flex items-center justify-between">
          <div className="flex-1">
            <h2 className="text-white font-bold text-xl mb-2" style={{ fontFamily: 'Archivo, sans-serif' }}>
              PAN Application Form
            </h2>
            <p className="text-white/40 text-sm">Complete all sections below to submit your application</p>
            
            {/* Overall progress bar */}
            <div className="mt-4 flex items-center gap-3">
              <div className="flex-1 h-2 rounded-full bg-white/[0.05]">
                <div 
                  className="h-full rounded-full bg-gradient-to-r from-violet-500 to-purple-400 transition-all duration-500"
                  style={{ width: `${overallProgress}%` }}
                />
              </div>
              <span className="text-white/60 text-sm font-mono min-w-[80px] text-right">
                {completedSections} / {totalSections} sections
              </span>
            </div>
          </div>
          
          <button 
            onClick={onCancel}
            className="ml-6 w-9 h-9 rounded-full bg-white/[0.06] hover:bg-white/[0.12] active:scale-95 flex items-center justify-center transition-all"
            aria-label="Close form">
            <X size={16} className="text-white/50" />
          </button>
        </div>
      </div>

      {/* Form Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        
        {/* Section 1: Personal Details */}
        <SectionCard 
          title="Personal Details" 
          subtitle="Basic personal information"
          icon={CreditCard}
          isComplete={personalComplete}
          errors={[errors.motherName, errors.fatherName, errors.salary].filter(Boolean)}
        >
          <div className="space-y-4">
            <Field label="Mother's Name" required error={errors.motherName}>
              <TextInput value={motherName} onChange={setMotherName} placeholder="As per official records" />
            </Field>
            
            <Field label="Father's Name" error={errors.fatherName}>
              <TextInput value={fatherName} onChange={setFatherName} placeholder="As per official records" />
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
          </div>
        </SectionCard>

        {/* Section 2: Income Sources */}
        <SectionCard 
          title="Income Sources" 
          subtitle="Select all income types that apply"
          icon={Loader2}
          isComplete={incomeComplete}
          errors={[errors.income].filter(Boolean)}
        >
          <div className="space-y-2">
            {errors.income && <p className="text-rose-400 text-xs flex items-center gap-1"><AlertCircle size={12} />{errors.income}</p>}
            <div className="grid grid-cols-1 gap-2">
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
        </SectionCard>

        {/* Section 3: Contact Information */}
        <SectionCard 
          title="Contact Information" 
          subtitle="Email and phone number"
          icon={CheckCircle2}
          isComplete={contactComplete}
          errors={[errors.email, errors.phone].filter(Boolean)}
        >
          <div className="space-y-4">
            <Field label="Email Address" required error={errors.email}>
              <TextInput value={email} onChange={setEmail} placeholder="you@example.com" type="email" />
            </Field>
            
            <Field label="Phone Number" required error={errors.phone}>
              <TextInput value={phone} onChange={setPhone} placeholder="10-digit mobile number" type="tel" />
            </Field>
          </div>
        </SectionCard>

        {/* Section 4: Address */}
        <SectionCard 
          title="Residential Address" 
          subtitle="Current residential details"
          icon={ImageIcon}
          isComplete={addressComplete}
          errors={[errors.address, errors.city, errors.state, errors.pincode].filter(Boolean)}
        >
          <div className="space-y-4">
            <Field label="Street Address" required error={errors.address}>
              <TextInput value={address} onChange={setAddress} placeholder="House no., street, area" />
            </Field>
            
            <div className="grid grid-cols-2 gap-3">
              <Field label="City" required error={errors.city}>
                <TextInput value={city} onChange={setCity} placeholder="City" />
              </Field>
              
              <Field label="State" required error={errors.state}>
                <TextInput value={state} onChange={setState} placeholder="State" />
              </Field>
            </div>
            
            <Field label="PIN Code" required error={errors.pincode}>
              <TextInput value={pincode} onChange={setPincode} placeholder="6-digit PIN" />
            </Field>
          </div>
        </SectionCard>

      </div>

      {/* Section 5: Documents (Full Width) */}
      <div className="mt-4">
        <SectionCard 
          title="Document Uploads" 
          subtitle="Upload required identity and address documents"
          icon={Upload}
          isComplete={docsComplete}
          errors={[errors.documents].filter(Boolean)}
        >
          <div className="space-y-2">
            {errors.documents && <p className="text-rose-400 text-xs flex items-center gap-1"><AlertCircle size={12} />{errors.documents}</p>}
            
            {/* Progress */}
            <div className="flex items-center gap-2 mb-3">
              <div className="flex-1 h-1 rounded-full bg-white/[0.05]">
                <div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-purple-400 transition-all duration-500"
                  style={{ width: `${(docsUploaded / DOC_SLOTS.length) * 100}%` }} />
              </div>
              <span className="text-white/30 text-xs font-mono">{docsUploaded}/{DOC_SLOTS.length}</span>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {DOC_SLOTS.map(slot => (
                <DocSlot key={slot.id} slot={slot}
                  upload={uploads[slot.id]} preview={previews[slot.id]}
                  isLoading={docBusy[slot.id]} error={docErrors[slot.id]}
                  onFile={handleDocFile} />
              ))}
            </div>
          </div>
        </SectionCard>
      </div>

      {/* Submit Button */}
      <div className="mt-6 flex items-center gap-4">
        <div className="flex-1 text-white/40 text-sm">
          {completedSections < totalSections && (
            <span className="flex items-center gap-1.5">
              <AlertCircle size={14} />
              Complete all {totalSections} sections to submit
            </span>
          )}
          {completedSections === totalSections && (
            <span className="flex items-center gap-1.5 text-emerald-400">
              <CheckCircle2 size={14} />
              All sections complete — ready to submit!
            </span>
          )}
        </div>
        
        <button
          onClick={handleSubmit}
          disabled={completedSections < totalSections}
          className="px-8 py-3.5 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 active:scale-[0.98] disabled:opacity-30 disabled:cursor-not-allowed text-white text-sm font-bold transition-all shadow-lg shadow-purple-900/20"
          style={{ fontFamily: 'Archivo, sans-serif' }}>
          Submit Application →
        </button>
      </div>
    </div>
  )
}
