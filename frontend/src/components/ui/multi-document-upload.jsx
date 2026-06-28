import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  X, 
  CheckCircle2, 
  Upload, 
  FileText, 
  CreditCard, 
  Loader2,
  Users,
  MapPin,
  Award,
  Banknote,
  Eye,
  AlertTriangle,
  TrendingUp
} from 'lucide-react'
import { GlowCard } from './spotlight-card'

const MULTI_DOCUMENTS = [
  {
    id: 'aadhaar',
    label: 'Aadhaar Card',
    subtitle: 'Primary Identity',
    desc: 'Government-issued identity card with photo and biometric data',
    icon: CreditCard,
    accept: '.pdf,.jpg,.jpeg,.png',
    glowColor: 'blue',
    accent: '#3b82f6',
    priority: 1,
    required: true
  },
  {
    id: 'ration_card',
    label: 'Ration Card',
    subtitle: 'Family/Welfare Document',
    desc: 'Food security card showing family members and entitlements',
    icon: Users,
    accept: '.pdf,.jpg,.jpeg,.png',
    glowColor: 'green',
    accent: '#10b981',
    priority: 2,
    required: false
  },
  {
    id: 'address_proof',
    label: 'Address Proof',
    subtitle: 'Residence Verification',
    desc: 'Bank statement, utility bill, or official address document',
    icon: MapPin,
    accept: '.pdf,.jpg,.jpeg,.png',
    glowColor: 'purple',
    accent: '#8b5cf6',
    priority: 3,
    required: false
  },
  {
    id: 'caste_certificate',
    label: 'Caste Certificate',
    subtitle: 'Social Category',
    desc: 'Government certificate showing caste/community classification',
    icon: Award,
    accept: '.pdf,.jpg,.jpeg,.png',
    glowColor: 'orange',
    accent: '#f59e0b',
    priority: 4,
    required: false
  },
  {
    id: 'pan_card',
    label: 'PAN Card',
    subtitle: 'Tax Identification',
    desc: 'Permanent Account Number for tax and financial transactions',
    icon: Banknote,
    accept: '.pdf,.jpg,.jpeg,.png',
    glowColor: 'red',
    accent: '#ef4444',
    priority: 5,
    required: false
  }
]

export function MultiDocumentUpload({ sessionId, onClose, onComplete, onNotLoggedIn }) {
  const [uploads, setUploads] = useState({})
  const [previews, setPreviews] = useState({})
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState({})
  const [processingResults, setProcessingResults] = useState(null)
  const [showResults, setShowResults] = useState(false)
  const refs = useRef({})

  const uploadedCount = Object.keys(uploads).length
  const hasMinimumDocs = uploads.aadhaar // At least Aadhaar is required

  async function handleFileUpload(docId, file) {
    if (!file) return
    
    setUploads(prev => ({ ...prev, [docId]: file.name }))
    setErrors(prev => ({ ...prev, [docId]: null }))

    // Create preview for images
    if (file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = e => setPreviews(prev => ({ ...prev, [docId]: e.target.result }))
      reader.readAsDataURL(file)
    }
  }

  async function handleProcessAll() {
    if (!hasMinimumDocs) {
      setErrors({ general: 'Aadhaar card is required for multi-document processing' })
      return
    }

    setBusy(true)
    setErrors({})
    
    try {
      const formData = new FormData()
      formData.append('auth_id', sessionId || 'anonymous')

      // Add all uploaded files
      for (const [docId, fileName] of Object.entries(uploads)) {
        const fileInput = refs.current[docId]
        if (fileInput && fileInput.files[0]) {
          formData.append(docId, fileInput.files[0])
        }
      }

      const response = await fetch('/api/multi_documents/verify', {
        method: 'POST',
        body: formData,
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      
      const result = await response.json()

      if (result.status === 'multi_documents_processed') {
        setProcessingResults(result)
        setShowResults(true)
      } else {
        throw new Error(result.error || result.message || 'Processing failed')
      }

    } catch (error) {
      setErrors({ general: error.message || 'Multi-document processing failed. Please try again.' })
    } finally {
      setBusy(false)
    }
  }

  async function handleConfirmResults() {
    if (!processingResults) return

    try {
      const response = await fetch('/api/multi_documents/confirm', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          auth_id: sessionId,
          combined_data: processingResults.combined_data,
          user_corrections: {} // TODO: Allow user to edit fields
        })
      })

      const result = await response.json()

      if (result.status === 'success') {
        onComplete?.(result)
        onClose()
      } else {
        throw new Error(result.error || 'Failed to save results')
      }

    } catch (error) {
      setErrors({ general: error.message || 'Failed to save multi-document results' })
    }
  }

  function removeUpload(docId) {
    setUploads(prev => {
      const newUploads = { ...prev }
      delete newUploads[docId]
      return newUploads
    })
    setPreviews(prev => {
      const newPreviews = { ...prev }
      delete newPreviews[docId]
      return newPreviews
    })
    setErrors(prev => {
      const newErrors = { ...prev }
      delete newErrors[docId]
      return newErrors
    })
  }

  // Show results view
  if (showResults && processingResults) {
    return (
      <div className="w-full rounded-2xl overflow-hidden my-2 select-none"
        style={{ background: 'rgba(8,5,16,0.98)', border: '1px solid rgba(255,255,255,0.06)', boxShadow: '0 12px 48px rgba(0,0,0,0.7)' }}>
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4">
          <div>
            <h3 className="text-white font-bold text-xl">Multi-Document Results</h3>
            <p className="text-white/60 text-sm">ORCHESTRA processed {processingResults.documents_count} documents</p>
          </div>
          <button onClick={onClose}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 text-xs font-semibold transition-all active:scale-95">
            <X size={12} /> Close
          </button>
        </div>

        {/* Confidence Score */}
        <div className="px-6 pb-4">
          <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-400/10 border border-emerald-400/20">
            <TrendingUp className="text-emerald-400" size={24} />
            <div>
              <p className="text-emerald-400 font-semibold">Confidence Score</p>
              <p className="text-white text-2xl font-bold">
                {Math.round((processingResults.confidence_score || 0) * 100)}%
              </p>
              <p className="text-white/60 text-xs">Cross-document validation</p>
            </div>
          </div>
        </div>

        {/* Combined Data Preview */}
        <div className="px-6 pb-4">
          <h4 className="text-white font-semibold mb-3">Merged Data</h4>
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {Object.entries(processingResults.combined_data || {}).map(([key, value]) => (
              <div key={key} className="flex justify-between items-center p-2 rounded-lg bg-white/5">
                <span className="text-white/70 text-sm">{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                <span className="text-white text-sm font-medium">{String(value).substring(0, 30)}{String(value).length > 30 ? '...' : ''}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Validation Results */}
        <div className="px-6 pb-4">
          <h4 className="text-white font-semibold mb-3">Validation Results</h4>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex items-center gap-2 p-3 rounded-lg bg-white/5">
              <CheckCircle2 size={16} className={processingResults.validation?.name_match ? 'text-emerald-400' : 'text-red-400'} />
              <div>
                <p className="text-white text-xs">Name Match</p>
                <p className={`text-xs font-semibold ${processingResults.validation?.name_match ? 'text-emerald-400' : 'text-red-400'}`}>
                  {processingResults.validation?.name_match ? 'Verified' : 'Inconsistent'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 p-3 rounded-lg bg-white/5">
              <CheckCircle2 size={16} className={processingResults.validation?.dob_match ? 'text-emerald-400' : 'text-red-400'} />
              <div>
                <p className="text-white text-xs">DOB Match</p>
                <p className={`text-xs font-semibold ${processingResults.validation?.dob_match ? 'text-emerald-400' : 'text-red-400'}`}>
                  {processingResults.validation?.dob_match ? 'Consistent' : 'Inconsistent'}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="px-6 pb-6 flex gap-3">
          <button
            onClick={() => setShowResults(false)}
            className="flex-1 px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white/70 text-sm font-medium transition-all active:scale-95"
          >
            Back to Upload
          </button>
          <button
            onClick={handleConfirmResults}
            className="flex-1 px-4 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 text-white text-sm font-bold transition-all active:scale-95"
          >
            Confirm & Save
          </button>
        </div>

        {errors.general && (
          <div className="px-6 pb-6">
            <div className="flex items-center gap-2 p-3 rounded-lg bg-red-400/10 border border-red-400/20 text-red-400 text-sm">
              <AlertTriangle size={16} />
              {errors.general}
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="w-full rounded-2xl overflow-hidden my-2 select-none"
      style={{ background: 'rgba(8,5,16,0.98)', border: '1px solid rgba(255,255,255,0.06)', boxShadow: '0 12px 48px rgba(0,0,0,0.7)' }}>

      {/* Hidden file inputs */}
      {MULTI_DOCUMENTS.map(doc => (
        <input
          key={doc.id}
          ref={el => refs.current[doc.id] = el}
          type="file"
          accept={doc.accept}
          className="hidden"
          onChange={e => handleFileUpload(doc.id, e.target.files?.[0])}
        />
      ))}

      {/* Header */}
      <div className="flex items-center justify-between px-6 pt-6 pb-4">
        <div>
          <h3 className="text-white font-bold text-xl">Multi-Document Upload</h3>
          <p className="text-white/60 text-sm">Upload multiple documents for intelligent data merging</p>
        </div>
        <button onClick={onClose}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 text-xs font-semibold transition-all active:scale-95">
          <X size={12} /> Close
        </button>
      </div>

      {/* Upload Progress */}
      <div className="px-6 pb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-white/70 text-sm">Documents Uploaded</span>
          <span className="text-white font-semibold">{uploadedCount}/5</span>
        </div>
        <div className="w-full bg-white/10 rounded-full h-2">
          <div 
            className="bg-gradient-to-r from-violet-600 to-purple-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${(uploadedCount / 5) * 100}%` }}
          />
        </div>
      </div>

      {/* Document Upload Cards */}
      <div className="px-6 pb-4 space-y-3">
        {MULTI_DOCUMENTS.map(doc => {
          const isUploaded = !!uploads[doc.id]
          const hasError = !!errors[doc.id]
          const preview = previews[doc.id]
          const Icon = doc.icon

          return (
            <GlowCard key={doc.id} glowColor={doc.glowColor} className="w-full">
              <div className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div 
                      className="w-10 h-10 rounded-xl flex items-center justify-center"
                      style={{ background: `${doc.accent}15`, border: `1px solid ${doc.accent}30` }}
                    >
                      {preview ? (
                        <img src={preview} alt="" className="w-full h-full object-cover rounded-xl" />
                      ) : isUploaded ? (
                        <CheckCircle2 size={20} className="text-emerald-400" />
                      ) : (
                        <Icon size={20} style={{ color: doc.accent }} />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-white font-semibold text-sm">{doc.label}</p>
                        {doc.required && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 border border-red-500/30">
                            Required
                          </span>
                        )}
                      </div>
                      <p className="text-xs mt-0.5" style={{ color: `${doc.accent}90` }}>
                        {doc.subtitle}
                      </p>
                    </div>
                  </div>
                  
                  {isUploaded && (
                    <button
                      onClick={() => removeUpload(doc.id)}
                      className="text-white/50 hover:text-red-400 transition-colors"
                    >
                      <X size={16} />
                    </button>
                  )}
                </div>

                <p className="text-white/35 text-xs leading-relaxed mb-3">
                  {isUploaded ? `✓ ${uploads[doc.id]}` : hasError ? errors[doc.id] : doc.desc}
                </p>

                {!isUploaded ? (
                  <button
                    onClick={() => refs.current[doc.id]?.click()}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl font-medium text-sm transition-all active:scale-[0.97]"
                    style={{ 
                      background: `${doc.accent}15`, 
                      border: `1px solid ${doc.accent}30`, 
                      color: doc.accent 
                    }}
                  >
                    <Upload size={14} />
                    Upload {doc.label}
                  </button>
                ) : (
                  <div className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium text-emerald-400 bg-emerald-400/8 border border-emerald-400/20">
                    <CheckCircle2 size={14} />
                    Uploaded
                  </div>
                )}
              </div>
            </GlowCard>
          )
        })}
      </div>

      {/* Process Button */}
      <div className="px-6 pb-6">
        {hasMinimumDocs ? (
          <button
            onClick={handleProcessAll}
            disabled={busy}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 disabled:opacity-50 text-white text-sm font-bold transition-all active:scale-95"
          >
            {busy ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Processing with ORCHESTRA...
              </>
            ) : (
              <>
                <Eye size={16} />
                Process {uploadedCount} Documents
              </>
            )}
          </button>
        ) : (
          <div className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-white/5 border border-white/10 text-white/50 text-sm">
            Upload Aadhaar card to proceed
          </div>
        )}

        {errors.general && (
          <div className="flex items-center gap-2 p-3 mt-3 rounded-lg bg-red-400/10 border border-red-400/20 text-red-400 text-sm">
            <AlertTriangle size={16} />
            {errors.general}
          </div>
        )}
      </div>
    </div>
  )
}