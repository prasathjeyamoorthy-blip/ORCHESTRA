import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  CheckCircle2, 
  AlertTriangle, 
  AlertCircle, 
  Loader2, 
  User, 
  Phone, 
  Calendar, 
  MapPin, 
  FileText, 
  Shield, 
  Eye, 
  Edit3,
  X,
  Save
} from 'lucide-react'

const FIELD_ICONS = {
  name: User,
  full_name: User,
  first_name: User,
  last_name: User,
  middle_name: User,
  father_name: User,
  father_first_name: User,
  father_middle_name: User,
  father_last_name: User,
  mother_name: User,
  mother_first_name: User,
  mother_middle_name: User,
  mother_last_name: User,
  mobile_number: Phone,
  phone: Phone,
  dob: Calendar,
  gender: User,
  state: MapPin,
  district: MapPin,
  address: MapPin,
  pincode: MapPin,
  area_locality: MapPin,
  flat_room_door: MapPin,
  building_village: MapPin,
  road_street_post: MapPin,
  residential_status: Shield,
  email_id: FileText,
  aadhar_number: FileText,
  aadhaar_number: FileText,
}

const FIELD_COLORS = {
  name: '#10b981',
  full_name: '#10b981',
  first_name: '#10b981',
  last_name: '#10b981',
  middle_name: '#06b6d4',
  father_name: '#3b82f6',
  father_first_name: '#3b82f6',
  father_middle_name: '#60a5fa',
  father_last_name: '#3b82f6',
  mother_name: '#8b5cf6',
  mother_first_name: '#8b5cf6',
  mother_middle_name: '#a78bfa',
  mother_last_name: '#8b5cf6',
  mobile_number: '#8b5cf6',
  phone: '#8b5cf6',
  dob: '#f59e0b',
  gender: '#ef4444',
  state: '#06b6d4',
  district: '#14b8a6',
  address: '#06b6d4',
  pincode: '#06b6d4',
  area_locality: '#06b6d4',
  flat_room_door: '#14b8a6',
  building_village: '#14b8a6',
  road_street_post: '#14b8a6',
  residential_status: '#6366f1',
  email_id: '#ec4899',
  aadhar_number: '#6366f1',
  aadhaar_number: '#6366f1',
}

const CONFIDENCE_LEVELS = {
  high: { color: '#10b981', label: 'High Confidence', icon: CheckCircle2 },
  medium: { color: '#f59e0b', label: 'Medium Confidence', icon: AlertTriangle },
  low: { color: '#ef4444', label: 'Low Confidence', icon: AlertCircle },
}

/**
 * DocumentConsentReview Component
 * 
 * A specialized component for displaying extracted document data and collecting user consent
 * before saving to the database. This component is specifically designed for the document
 * verification workflow where users need to review and confirm auto-extracted data.
 * 
 * Supports all Aadhaar fields including:
 * - Personal info: name (first/middle/last), DOB, gender, phone
 * - Family info: father's name (first/middle/last), mother's name (first/middle/last)
 * - Address: flat/room/door, building/village, road/street/post, area/locality, district, state, pincode
 * - Document info: Aadhaar number, residential status
 * - Contact: mobile number, email
 * 
 * @param {Object} extractedFields - Fields automatically extracted from the document
 * @param {Array} missingFields - Fields that need user input (optional)
 * @param {number} qualityScore - Document quality score (0.0-1.0)
 * @param {string} documentType - Type of document being reviewed
 * @param {string} confidence - Overall extraction confidence ('high'|'medium'|'low')
 * @param {string} sessionId - Session identifier for the verification process
 * @param {string} authId - Authentication identifier
 * @param {Function} onConfirm - Callback when user confirms and saves the data
 * @param {Function} onCancel - Callback when user cancels the process
 * @param {Function} onEdit - Callback when user edits a field (optional)
 * 
 * Features:
 * - Field-by-field display with confidence indicators
 * - Inline editing capabilities for all fields
 * - Quality score and document type display
 * - Validation with specific error messages
 * - Responsive design with accessibility features
 * - Smooth animations and transitions
 * - Organized field sections (Personal, Family, Address, Document)
 * 
 * Usage:
 * <DocumentConsentReview
 *   extractedFields={{
 *     name: "Bhuvaneshkumar",
 *     first_name: "Bhuvaneshkumar",
 *     father_name: "Gopalakrishnan",
 *     mother_name: "Anuradha",
 *     phone: "9003151801",
 *     dob: "18/01/2008",
 *     gender: "Male",
 *     flat_room_door: "21",
 *     building_village: "SEVENTH CROSS STREET",
 *     road_street_post: "PERIYAR NAGAR",
 *     area_locality: "NELLITHOPE",
 *     state: "Pondicherry",
 *     pincode: "605005",
 *     residential_status: "Resident"
 *   }}
 *   missingFields={[]}
 *   qualityScore={0.85}
 *   documentType="Aadhaar Card"
 *   confidence="high"
 *   sessionId="session-123"
 *   authId="auth-456"
 *   onConfirm={(result) => console.log('Confirmed:', result)}
 *   onCancel={() => console.log('Cancelled')}
 * />
 */
export function DocumentConsentReview({ 
  extractedFields = {}, 
  missingFields = [],
  qualityScore,
  documentType = 'Aadhaar Card',
  confidence = 'medium',
  sessionId,
  authId,
  onConfirm,
  onCancel,
  onEdit
}) {
  const [formData, setFormData] = useState(() => {
    // Pre-populate form with extracted fields
    const initialData = {}
    Object.entries(extractedFields).forEach(([key, value]) => {
      if (value && value.trim && value.trim()) {
        initialData[key] = value
      } else if (value) {
        initialData[key] = value
      }
    })
    return initialData
  })
  
  const [editingField, setEditingField] = useState(null)
  const [fieldErrors, setFieldErrors] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showAllFields, setShowAllFields] = useState(false)

  // Get field confidence based on overall confidence and presence in extracted data
  const getFieldConfidence = (fieldName, value) => {
    if (!value || !value.toString().trim()) return 'low'
    if (extractedFields[fieldName]) return confidence
    return 'medium' // User-provided fields
  }

  // Validate individual field
  const validateField = (fieldName, value) => {
    if (!value || !value.toString().trim()) {
      return `${getFieldLabel(fieldName)} is required`
    }

    switch (fieldName) {
      case 'mobile_number':
      case 'phone':
        if (!/^[6-9][0-9]{9}$/.test(value)) {
          return 'Phone number must be 10 digits starting with 6-9'
        }
        break
      case 'aadhar_number':
      case 'aadhaar_number':
        const cleanAadhar = value.replace(/\s|-/g, '')
        if (!/^[0-9]{12}$/.test(cleanAadhar)) {
          return 'Aadhaar number must be 12 digits'
        }
        break
      case 'dob':
        if (!/^\d{2}\/\d{2}\/\d{4}$/.test(value) && !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
          return 'Date format should be DD/MM/YYYY or YYYY-MM-DD'
        }
        break
      case 'pincode':
        if (!/^[0-9]{6}$/.test(value)) {
          return 'Pincode must be 6 digits'
        }
        break
      case 'email_id':
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
          return 'Please enter a valid email address'
        }
        break
      case 'residential_status':
        if (!['Resident', 'Non-Resident'].includes(value)) {
          return 'Residential status must be Resident or Non-Resident'
        }
        break
    }
    return null
  }

  // Get display label for field
  const getFieldLabel = (fieldName) => {
    const labels = {
      name: 'Full Name',
      full_name: 'Full Name',
      first_name: 'First Name',
      middle_name: 'Middle Name',
      last_name: 'Last Name',
      father_name: "Father's Name",
      father_first_name: "Father's First Name",
      father_middle_name: "Father's Middle Name",
      father_last_name: "Father's Last Name",
      mother_name: "Mother's Name",
      mother_first_name: "Mother's First Name",
      mother_middle_name: "Mother's Middle Name",
      mother_last_name: "Mother's Last Name",
      mobile_number: 'Mobile Number',
      phone: 'Phone Number',
      dob: 'Date of Birth',
      gender: 'Gender',
      state: 'State',
      district: 'District',
      address: 'Address',
      pincode: 'Pincode',
      area_locality: 'Area/Locality',
      flat_room_door: 'Flat/Room/Door',
      building_village: 'Building/Village',
      road_street_post: 'Road/Street/Post',
      residential_status: 'Residential Status',
      email_id: 'Email ID',
      aadhar_number: 'Aadhaar Number',
      aadhaar_number: 'Aadhaar Number',
    }
    return labels[fieldName] || fieldName.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const handleFieldEdit = (fieldName, value) => {
    setFormData(prev => ({ ...prev, [fieldName]: value }))
    
    // Clear any existing error for this field
    if (fieldErrors[fieldName]) {
      setFieldErrors(prev => ({ ...prev, [fieldName]: null }))
    }
  }

  const handleFieldSave = (fieldName) => {
    const value = formData[fieldName]
    const error = validateField(fieldName, value)
    
    if (error) {
      setFieldErrors(prev => ({ ...prev, [fieldName]: error }))
      return
    }
    
    setEditingField(null)
    onEdit?.(fieldName, value)
  }

  const handleConfirm = async () => {
    // Validate all fields
    const errors = {}
    const allFields = [...Object.keys(extractedFields), ...missingFields.map(f => typeof f === 'string' ? f : f.field)]
    const requiredFields = [...new Set(allFields)] // Remove duplicates
    
    requiredFields.forEach(fieldName => {
      const value = formData[fieldName]
      const error = validateField(fieldName, value)
      if (error) errors[fieldName] = error
    })

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      return
    }

    setIsSubmitting(true)
    
    try {
      const result = await fetch('/api/documents/confirm', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          session_id: sessionId,
          auth_id: authId,
          extracted_fields: extractedFields,
          user_fields: formData,
        }),
      })
      
      const data = await result.json()
      
      if (data.status === 'success') {
        // Pass both the API response AND the confirmed plain fields back.
        // The parent (document-upload-panel) uses confirmed_fields to update
        // the Redis extraction cache with user-verified plain text data.
        onConfirm?.({ ...data, confirmed_fields: { ...extractedFields, ...formData } })
      } else {
        setFieldErrors({ general: data.message || data.error || 'Failed to save document' })
      }
    } catch (error) {
      setFieldErrors({ general: 'Network error. Please try again.' })
    } finally {
      setIsSubmitting(false)
    }
  }

  // Get all fields to display (extracted + missing)
  const allFields = () => {
    const fields = new Map()
    
    // Add extracted fields
    Object.keys(extractedFields).forEach(key => {
      fields.set(key, { 
        name: key, 
        value: formData[key] || extractedFields[key], 
        isExtracted: true 
      })
    })
    
    // Add missing fields
    missingFields.forEach(field => {
      const fieldName = typeof field === 'string' ? field : field.field
      if (!fields.has(fieldName)) {
        fields.set(fieldName, { 
          name: fieldName, 
          value: formData[fieldName] || '', 
          isExtracted: false 
        })
      }
    })
    
    return Array.from(fields.values())
  }

  const displayFields = allFields()
  const visibleFields = showAllFields ? displayFields : displayFields.slice(0, 12)
  const hasMoreFields = displayFields.length > 12

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="w-full max-w-2xl mx-auto rounded-2xl overflow-hidden"
      style={{ 
        background: 'rgba(8,5,16,0.98)', 
        border: '1px solid rgba(255,255,255,0.06)', 
        boxShadow: '0 12px 48px rgba(0,0,0,0.7)' 
      }}
    >
      {/* Header */}
      <div className="px-6 pt-6 pb-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-400/10 border border-emerald-400/20 flex items-center justify-center">
              <Eye size={20} className="text-emerald-400" />
            </div>
            <div>
              <h3 className="text-white font-bold text-lg">Review Document Data</h3>
              <p className="text-white/60 text-sm">Verify extracted information before saving</p>
            </div>
          </div>
          <button
            onClick={onCancel}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-white/70 hover:text-white transition-all"
          >
            <X size={18} />
          </button>
        </div>
        
        {/* Document Info */}
        <div className="flex flex-wrap gap-3 mb-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-violet-400/10 border border-violet-400/20">
            <Shield size={14} className="text-violet-400" />
            <span className="text-violet-400 text-xs font-medium">{documentType}</span>
          </div>
          
          {qualityScore && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-400/10 border border-emerald-400/20">
              <CheckCircle2 size={14} className="text-emerald-400" />
              <span className="text-emerald-400 text-xs font-medium">
                Quality: {Math.round(qualityScore * 100)}%
              </span>
            </div>
          )}
          
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" 
               style={{ 
                 backgroundColor: `${CONFIDENCE_LEVELS[confidence].color}15`, 
                 border: `1px solid ${CONFIDENCE_LEVELS[confidence].color}30` 
               }}>
            <CONFIDENCE_LEVELS[confidence].icon size={14} style={{ color: CONFIDENCE_LEVELS[confidence].color }} />
            <span className="text-xs font-medium" style={{ color: CONFIDENCE_LEVELS[confidence].color }}>
              {CONFIDENCE_LEVELS[confidence].label}
            </span>
          </div>
        </div>
      </div>

      {/* Fields */}
      <div className="px-6 pb-6 space-y-4">
        <AnimatePresence>
          {visibleFields.map((field) => {
            const fieldName = field.name
            const value = field.value
            const isExtracted = field.isExtracted
            const fieldConfidence = getFieldConfidence(fieldName, value)
            const Icon = FIELD_ICONS[fieldName] || FileText
            const color = FIELD_COLORS[fieldName] || '#6366f1'
            const isEditing = editingField === fieldName
            const error = fieldErrors[fieldName]
            
            return (
              <motion.div
                key={fieldName}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div 
                      className="w-6 h-6 rounded-lg flex items-center justify-center"
                      style={{ backgroundColor: `${color}15`, border: `1px solid ${color}30` }}
                    >
                      <Icon size={14} style={{ color }} />
                    </div>
                    <span className="text-sm font-semibold text-white">
                      {getFieldLabel(fieldName)}
                    </span>
                    {isExtracted && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-400/10 border border-emerald-400/20 text-emerald-400">
                        Auto-extracted
                      </span>
                    )}
                    <div 
                      className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs"
                      style={{ 
                        backgroundColor: `${CONFIDENCE_LEVELS[fieldConfidence].color}15`, 
                        border: `1px solid ${CONFIDENCE_LEVELS[fieldConfidence].color}30`,
                        color: CONFIDENCE_LEVELS[fieldConfidence].color
                      }}
                    >
                      <CONFIDENCE_LEVELS[fieldConfidence].icon size={10} />
                      {fieldConfidence}
                    </div>
                  </div>
                  
                  {!isEditing && (
                    <button
                      onClick={() => setEditingField(fieldName)}
                      className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-white/50 hover:text-white transition-all"
                    >
                      <Edit3 size={14} />
                    </button>
                  )}
                </div>
                
                {isEditing ? (
                  <div className="space-y-2">
                    {fieldName === 'gender' ? (
                      <select
                        value={value}
                        onChange={(e) => handleFieldEdit(fieldName, e.target.value)}
                        className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white text-sm transition-all focus:outline-none focus:ring-2 focus:ring-violet-400/30"
                      >
                        <option value="">Select Gender</option>
                        <option value="Male">Male</option>
                        <option value="Female">Female</option>
                        <option value="Transgender">Transgender</option>
                        <option value="Other">Other</option>
                      </select>
                    ) : fieldName === 'residential_status' ? (
                      <select
                        value={value}
                        onChange={(e) => handleFieldEdit(fieldName, e.target.value)}
                        className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white text-sm transition-all focus:outline-none focus:ring-2 focus:ring-violet-400/30"
                      >
                        <option value="">Select Residential Status</option>
                        <option value="Resident">Resident</option>
                        <option value="Non-Resident">Non-Resident</option>
                      </select>
                    ) : (
                      <input
                        type={fieldName === 'dob' ? 'date' : (fieldName === 'mobile_number' || fieldName === 'phone') ? 'tel' : fieldName === 'email_id' ? 'email' : 'text'}
                        value={value}
                        onChange={(e) => handleFieldEdit(fieldName, e.target.value)}
                        placeholder={`Enter ${getFieldLabel(fieldName)}`}
                        className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white text-sm transition-all focus:outline-none focus:ring-2 focus:ring-violet-400/30 placeholder-white/30"
                        autoFocus
                      />
                    )}
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleFieldSave(fieldName)}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-all"
                      >
                        <Save size={12} />
                        Save
                      </button>
                      <button
                        onClick={() => {
                          setEditingField(null)
                          setFormData(prev => ({ ...prev, [fieldName]: extractedFields[fieldName] || '' }))
                        }}
                        className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-white/70 text-xs font-medium transition-all"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className={`px-4 py-3 rounded-xl border transition-all ${
                    error 
                      ? 'bg-red-400/5 border-red-400/30' 
                      : fieldConfidence === 'high'
                      ? 'bg-emerald-400/5 border-emerald-400/20'
                      : fieldConfidence === 'medium'
                      ? 'bg-yellow-400/5 border-yellow-400/20'
                      : 'bg-red-400/5 border-red-400/20'
                  }`}>
                    <span className={`text-sm ${
                      value ? 'text-white' : 'text-white/40 italic'
                    }`}>
                      {value || 'Not provided'}
                    </span>
                  </div>
                )}
                
                {error && (
                  <div className="flex items-center gap-2 text-red-400 text-xs">
                    <AlertCircle size={12} />
                    {error}
                  </div>
                )}
              </motion.div>
            )
          })}
        </AnimatePresence>
        
        {hasMoreFields && (
          <button
            onClick={() => setShowAllFields(!showAllFields)}
            className="w-full py-2 text-center text-sm text-white/50 hover:text-white/70 transition-colors"
          >
            {showAllFields ? 'Show Less' : `Show ${displayFields.length - 6} More Fields`}
          </button>
        )}
        
        {fieldErrors.general && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-red-400/10 border border-red-400/20 text-red-400 text-sm">
            <AlertCircle size={16} />
            {fieldErrors.general}
          </div>
        )}
        
        {/* Action Buttons */}
        <div className="flex gap-3 pt-4">
          <button
            onClick={onCancel}
            disabled={isSubmitting}
            className="flex-1 px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white/70 hover:text-white text-sm font-medium transition-all active:scale-95 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={isSubmitting || editingField !== null}
            className="flex-1 px-4 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 disabled:opacity-50 text-white text-sm font-bold transition-all active:scale-95 flex items-center justify-center gap-2"
          >
            {isSubmitting ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Confirming...
              </>
            ) : (
              <>
                <CheckCircle2 size={16} />
                Confirm & Save
              </>
            )}
          </button>
        </div>
      </div>
    </motion.div>
  )
}

export default DocumentConsentReview