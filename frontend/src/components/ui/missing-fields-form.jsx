import { useState } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle2, AlertCircle, Loader2, User, Phone, Calendar, MapPin, FileText } from 'lucide-react'

const FIELD_ICONS = {
  name: User,
  full_name: User,
  father_name: User,
  mother_name: User,
  mobile_number: Phone,
  dob: Calendar,
  gender: User,
  state: MapPin,
  district: MapPin,
  address: MapPin,
  pincode: MapPin,
  aadhar_number: FileText,
  aadhaar_number: FileText,
}

const FIELD_COLORS = {
  name: '#10b981',
  full_name: '#10b981',
  father_name: '#3b82f6',
  mother_name: '#8b5cf6',
  mobile_number: '#8b5cf6',
  dob: '#f59e0b',
  gender: '#ef4444',
  state: '#06b6d4',
  district: '#06b6d4',
  address: '#06b6d4',
  pincode: '#06b6d4',
  aadhar_number: '#6366f1',
  aadhaar_number: '#6366f1',
}

const CONFIDENCE_LEVELS = {
  high: { color: '#10b981', label: 'High Confidence', icon: CheckCircle2 },
  medium: { color: '#f59e0b', label: 'Medium Confidence', icon: AlertCircle },
  low: { color: '#ef4444', label: 'Low Confidence', icon: AlertCircle },
}

export function MissingFieldsForm({ 
  missingFields = [], 
  extractedFields = {}, 
  sessionId, 
  authId, 
  qualityScore,
  onComplete, 
  onCancel,
  isConsentMode = false, // New prop to distinguish between missing fields and consent modes
  documentType = 'Aadhaar Card', // Add document type for better context
  confidence = 'medium' // Add confidence level for extracted fields
}) {
  const [formData, setFormData] = useState(() => {
    // Pre-populate form with extracted fields
    const initialData = {}
    Object.entries(extractedFields).forEach(([key, value]) => {
      if (value && value.toString().trim()) {
        initialData[key] = value
      }
    })
    return initialData
  })
  const [errors, setErrors] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Get field confidence based on overall confidence and presence in extracted data
  const getFieldConfidence = (fieldName, value) => {
    if (!value || !value.toString().trim()) return 'low'
    if (extractedFields[fieldName]) return confidence
    return 'medium' // User-provided fields
  }

  // Get display label for field
  const getFieldLabel = (fieldName) => {
    const labels = {
      name: 'Full Name',
      full_name: 'Full Name',
      father_name: "Father's Name",
      mother_name: "Mother's Name",
      mobile_number: 'Mobile Number',
      dob: 'Date of Birth',
      gender: 'Gender',
      state: 'State',
      district: 'District',
      address: 'Address',
      pincode: 'Pincode',
      aadhar_number: 'Aadhaar Number',
      aadhaar_number: 'Aadhaar Number',
    }
    return labels[fieldName] || fieldName.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const handleInputChange = (fieldName, value) => {
    setFormData(prev => ({ ...prev, [fieldName]: value }))
    // Clear error when user starts typing
    if (errors[fieldName]) {
      setErrors(prev => ({ ...prev, [fieldName]: null }))
    }
  }

  const validateForm = () => {
    const newErrors = {}
    
    // Get all required fields based on mode
    let allRequiredFields = []
    
    if (isConsentMode) {
      // In consent mode, validate all common fields that exist in formData or extractedFields
      const commonFields = ['name', 'full_name', 'father_name', 'mother_name', 'aadhar_number', 'aadhaar_number', 'mobile_number', 'dob', 'gender', 'state', 'district', 'address', 'pincode']
      allRequiredFields = commonFields
        .filter(field => extractedFields[field] || formData[field])
        .map(field => ({ field, label: getFieldLabel(field) }))
      
      // Add any additional missing fields
      if (missingFields.length > 0) {
        missingFields.forEach(field => {
          const fieldName = typeof field === 'string' ? field : field.field
          if (!allRequiredFields.some(f => f.field === fieldName)) {
            allRequiredFields.push({
              field: fieldName,
              label: typeof field === 'string' ? getFieldLabel(field) : field.label
            })
          }
        })
      }
    } else {
      // In missing fields mode, use only missing fields
      allRequiredFields = missingFields.length > 0 
        ? missingFields.filter(f => f.required !== false)
        : [
            { field: 'name', label: 'Full Name' },
            { field: 'father_name', label: 'Father\'s Name' },
            { field: 'aadhar_number', label: 'Aadhaar Number' },
            { field: 'mobile_number', label: 'Mobile Number' },
            { field: 'dob', label: 'Date of Birth' },
            { field: 'gender', label: 'Gender' },
            { field: 'state', label: 'State' }
          ]
    }
    
    allRequiredFields.forEach(field => {
      const fieldName = typeof field === 'string' ? field : field.field
      const fieldLabel = typeof field === 'string' ? getFieldLabel(field) : field.label
      const value = formData[fieldName]
      
      if (!value || !value.toString().trim()) {
        newErrors[fieldName] = `${fieldLabel} is required`
        return
      }
      
      // Field-specific validation
      if (field.validation) {
        if (field.validation.pattern && !new RegExp(field.validation.pattern).test(value)) {
          newErrors[fieldName] = field.validation.message
        }
        
        if (field.validation.max && new Date(value) > new Date(field.validation.max)) {
          newErrors[fieldName] = field.validation.message
        }
      } else {
        // Default validation for common fields
        if (fieldName === 'mobile_number' && !/^[6-9][0-9]{9}$/.test(value)) {
          newErrors[fieldName] = 'Mobile number must be 10 digits starting with 6-9'
        }
        
        if ((fieldName === 'aadhar_number' || fieldName === 'aadhaar_number') && !/^([0-9]{12}|[Xx*]{8}[0-9]{4})$/.test(value.replace(/\s|-/g, ''))) {
          newErrors[fieldName] = 'Aadhaar number must be 12 digits'
        }
        
        if (fieldName === 'dob' && !/^\d{2}\/\d{2}\/\d{4}$/.test(value) && !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
          newErrors[fieldName] = 'Date format should be DD/MM/YYYY or YYYY-MM-DD'
        }
        
        if (fieldName === 'pincode' && !/^[0-9]{6}$/.test(value)) {
          newErrors[fieldName] = 'Pincode must be 6 digits'
        }
      }
    })
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }
    
    setIsSubmitting(true)
    
    try {
      // Choose endpoint based on mode
      const endpoint = isConsentMode ? '/api/documents/confirm_save' : '/api/complete_document'
      const requestBody = {
        session_id: sessionId,
        auth_id: authId,
        extracted_fields: extractedFields,
        user_fields: formData,
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        credentials: 'include',
        body: JSON.stringify(requestBody),
      })
      
      const result = await response.json()
      
      if (result.status === 'success') {
        onComplete?.(result)
      } else {
        setErrors({ 
          general: result.message || result.error || 
                   `Failed to ${isConsentMode ? 'confirm and save' : 'complete'} document verification` 
        })
      }
    } catch (error) {
      console.error(`Document ${isConsentMode ? 'confirmation' : 'completion'} error:`, error)
      setErrors({ 
        general: `Network error. Please check your connection and try again.` 
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const renderField = (field) => {
    const fieldName = typeof field === 'string' ? field : field.field
    const fieldLabel = typeof field === 'string' ? getFieldLabel(fieldName) : field.label
    const fieldType = typeof field === 'string' ? 'text' : field.type || 'text'
    
    const Icon = FIELD_ICONS[fieldName] || FileText
    const color = FIELD_COLORS[fieldName] || '#6366f1'
    const value = formData[fieldName] || ''
    const error = errors[fieldName]
    
    // Check if this field was auto-extracted
    const isExtracted = extractedFields[fieldName] && extractedFields[fieldName].toString().trim()
    const fieldConfidence = getFieldConfidence(fieldName, value)
    const confidenceConfig = CONFIDENCE_LEVELS[fieldConfidence]

    return (
      <motion.div
        key={fieldName}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
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
            <label className="text-sm font-semibold text-white">
              {fieldLabel}
              <span className="text-red-400 ml-1">*</span>
            </label>
          </div>
          
          {/* Field type and confidence indicators */}
          <div className="flex items-center gap-1">
            {isExtracted && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-400/10 border border-emerald-400/20 text-emerald-400">
                Auto-extracted
              </span>
            )}
            {(isConsentMode || isExtracted) && (
              (() => {
                const Icon = confidenceConfig.icon
                return (
                  <div 
                    className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs"
                    style={{ 
                      backgroundColor: `${confidenceConfig.color}15`, 
                      border: `1px solid ${confidenceConfig.color}30`,
                      color: confidenceConfig.color
                    }}
                  >
                    <Icon size={10} />
                    {fieldConfidence}
                  </div>
                )
              })()
            )}
          </div>
        </div>
        
        {fieldType === 'select' && field.validation?.options ? (
          <select
            value={value}
            onChange={(e) => handleInputChange(fieldName, e.target.value)}
            className={`w-full px-4 py-3 rounded-xl bg-white/5 border text-white text-sm transition-all focus:outline-none focus:ring-2 ${
              error 
                ? 'border-red-400/50 focus:ring-red-400/30' 
                : isExtracted
                ? 'border-emerald-400/50 focus:ring-emerald-400/30'
                : 'border-white/10 focus:ring-violet-400/30'
            }`}
          >
            <option value="">Select {fieldLabel}</option>
            {field.validation.options.map(option => (
              <option key={option} value={option} className="bg-gray-800 text-white">
                {option}
              </option>
            ))}
          </select>
        ) : fieldType === 'date' ? (
          <input
            type="date"
            value={value}
            onChange={(e) => handleInputChange(fieldName, e.target.value)}
            max={field.validation?.max}
            className={`w-full px-4 py-3 rounded-xl bg-white/5 border text-white text-sm transition-all focus:outline-none focus:ring-2 ${
              error 
                ? 'border-red-400/50 focus:ring-red-400/30' 
                : isExtracted
                ? 'border-emerald-400/50 focus:ring-emerald-400/30'
                : 'border-white/10 focus:ring-violet-400/30'
            }`}
          />
        ) : fieldName === 'gender' ? (
          <select
            value={value}
            onChange={(e) => handleInputChange(fieldName, e.target.value)}
            className={`w-full px-4 py-3 rounded-xl bg-white/5 border text-white text-sm transition-all focus:outline-none focus:ring-2 ${
              error 
                ? 'border-red-400/50 focus:ring-red-400/30' 
                : isExtracted
                ? 'border-emerald-400/50 focus:ring-emerald-400/30'
                : 'border-white/10 focus:ring-violet-400/30'
            }`}
          >
            <option value="">Select Gender</option>
            <option value="Male" className="bg-gray-800 text-white">Male</option>
            <option value="Female" className="bg-gray-800 text-white">Female</option>
            <option value="Other" className="bg-gray-800 text-white">Other</option>
          </select>
        ) : (
          <input
            type={fieldName.includes('mobile') ? 'tel' : fieldType}
            value={value}
            onChange={(e) => handleInputChange(fieldName, e.target.value)}
            placeholder={field.placeholder || `Enter ${fieldLabel}`}
            pattern={field.validation?.pattern}
            className={`w-full px-4 py-3 rounded-xl bg-white/5 border text-white text-sm transition-all focus:outline-none focus:ring-2 placeholder-white/30 ${
              error 
                ? 'border-red-400/50 focus:ring-red-400/30' 
                : isExtracted
                ? 'border-emerald-400/50 focus:ring-emerald-400/30'
                : 'border-white/10 focus:ring-violet-400/30'
            }`}
          />
        )}
        
        {error && (
          <div className="flex items-center gap-2 text-red-400 text-xs">
            <AlertCircle size={12} />
            {error}
          </div>
        )}
      </motion.div>
    )
  }

  return (
    <div className="w-full max-w-md mx-auto">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="rounded-2xl overflow-hidden"
        style={{ 
          background: 'rgba(8,5,16,0.98)', 
          border: '1px solid rgba(255,255,255,0.06)', 
          boxShadow: '0 12px 48px rgba(0,0,0,0.7)' 
        }}
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4">
          <div className="flex items-center gap-3 mb-3">
            <div className={`w-8 h-8 rounded-xl flex items-center justify-center ${
              isConsentMode 
                ? 'bg-emerald-400/10 border border-emerald-400/20'
                : 'bg-orange-400/10 border border-orange-400/20'
            }`}>
              <FileText size={18} className={isConsentMode ? 'text-emerald-400' : 'text-orange-400'} />
            </div>
            <div>
              <h3 className="text-white font-bold text-lg">
                {isConsentMode ? 'Review Document Data' : 'Complete Document'}
              </h3>
              <p className="text-white/60 text-sm">
                {isConsentMode 
                  ? 'Verify extracted information before saving'
                  : 'Fill in the missing information'
                }
              </p>
            </div>
          </div>
          
          {/* Document and Quality Info */}
          <div className="flex flex-wrap gap-2 mb-4">
            {documentType && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-violet-400/10 border border-violet-400/20">
                <span className="text-violet-400 text-xs font-medium">{documentType}</span>
              </div>
            )}
            
            {qualityScore && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-400/10 border border-emerald-400/20">
                <CheckCircle2 size={14} className="text-emerald-400" />
                <span className="text-emerald-400 text-xs font-medium">
                  Quality: {Math.round(qualityScore * 100)}%
                </span>
              </div>
            )}
            
            {isConsentMode && (() => {
              const config = CONFIDENCE_LEVELS[confidence]
              const Icon = config.icon
              return (
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" 
                     style={{ 
                       backgroundColor: `${config.color}15`, 
                       border: `1px solid ${config.color}30` 
                     }}>
                  <Icon size={14} style={{ color: config.color }} />
                  <span className="text-xs font-medium" style={{ color: config.color }}>
                    {config.label}
                  </span>
                </div>
              )
            })()}
          </div>
        </div>

        {/* Extracted Fields Summary */}
        {Object.keys(extractedFields).length > 0 && (
          <div className="px-6 pb-4">
            <p className="text-white/40 text-xs mb-2">Already extracted ({Object.keys(extractedFields).length} fields):</p>
            <div className="max-h-40 overflow-y-auto space-y-1.5">
              {Object.entries(extractedFields).map(([key, value]) => (
                <div key={key} className="flex items-start gap-2 text-xs">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1 flex-shrink-0"></div>
                  <div className="min-w-0">
                    <span className="text-white/60">{key.replace(/([A-Z])/g, ' $1').trim()}: </span>
                    <span className="text-white break-words">{String(value).substring(0, 50)}{String(value).length > 50 ? '...' : ''}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 pb-6 space-y-4">
          {/* Render fields based on mode */}
          {isConsentMode ? (
            // In consent mode, show fields that exist in extracted data or are in missing fields
            (() => {
              const fieldsToRender = new Set()
              
              // Add extracted fields
              Object.keys(extractedFields).forEach(field => fieldsToRender.add(field))
              
              // Add missing fields
              missingFields.forEach(field => {
                const fieldName = typeof field === 'string' ? field : field.field
                fieldsToRender.add(fieldName)
              })
              
              // Convert to field objects and render
              return Array.from(fieldsToRender).map(fieldName => {
                // Check if this field has a custom definition in missingFields
                const customField = missingFields.find(f => 
                  (typeof f === 'string' ? f : f.field) === fieldName
                )
                
                if (customField && typeof customField !== 'string') {
                  return renderField(customField)
                } else {
                  // Use default field definition
                  return renderField({
                    field: fieldName,
                    label: getFieldLabel(fieldName),
                    type: fieldName.includes('mobile') ? 'tel' : fieldName === 'dob' ? 'text' : 'text'
                  })
                }
              })
            })()
          ) : (
            // In missing fields mode, show only missing fields
            missingFields.map(renderField)
          )}
          
          {errors.general && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-red-400/10 border border-red-400/20 text-red-400 text-sm">
              <AlertCircle size={16} />
              {errors.general}
            </div>
          )}
          
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white/70 text-sm font-medium transition-all active:scale-95"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 disabled:opacity-50 text-white text-sm font-bold transition-all active:scale-95 flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  {isConsentMode ? 'Confirming...' : 'Saving...'}
                </>
              ) : (
                isConsentMode ? 'Confirm & Save' : 'Complete Document'
              )}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  )
}