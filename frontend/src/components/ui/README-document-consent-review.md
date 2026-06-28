# DocumentConsentReview Component

## Overview

The `DocumentConsentReview` component is a specialized React component designed for the PAN verification integration workflow. It displays extracted document data and collects user consent before saving information to the database.

## Purpose

This component replaces the direct auto-save behavior with a user consent workflow where:
1. Document data is extracted using OCR/AI
2. Users review the extracted information
3. Users can edit any incorrect fields
4. Users explicitly confirm before data is saved

## Features

### ✅ Completed Acceptance Criteria

1. **Display extracted fields with confidence indicators** - Each field shows confidence level (high/medium/low) with appropriate visual indicators
2. **Show document type and quality score prominently** - Header displays document type and quality percentage
3. **Highlight fields that need attention** - Low confidence and missing fields are visually highlighted
4. **Provide edit capabilities for all fields** - Click edit icon to modify any field inline
5. **Include clear confirm/cancel options** - Bottom action buttons for user decision
6. **Show field-specific validation errors** - Real-time validation with specific error messages

### Key Features

- **Confidence Indicators**: Visual badges showing extraction confidence (high/medium/low)
- **Inline Editing**: Click-to-edit functionality for all fields
- **Field Validation**: Real-time validation for mobile numbers, Aadhaar numbers, dates, etc.
- **Progressive Disclosure**: Shows first 6 fields by default, expandable to show more
- **Responsive Design**: Works on desktop and mobile devices
- **Accessibility**: Proper ARIA labels and keyboard navigation
- **Smooth Animations**: Framer Motion animations for better UX

## Usage

```jsx
import { DocumentConsentReview } from './components/ui/document-consent-review'

<DocumentConsentReview
  extractedFields={{
    name: "John Doe",
    father_name: "Robert Doe", 
    mobile_number: "9876543210",
    aadhar_number: "123456789012"
  }}
  missingFields={[]}
  qualityScore={0.85}
  documentType="Aadhaar Card"
  confidence="high"
  sessionId="session-123"
  authId="auth-456"
  onConfirm={(result) => {
    // Handle successful confirmation
    console.log('Data saved:', result)
  }}
  onCancel={() => {
    // Handle cancellation
    console.log('User cancelled')
  }}
  onEdit={(fieldName, value) => {
    // Handle field edits (optional)
    console.log(`Field ${fieldName} changed to:`, value)
  }}
/>
```

## Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `extractedFields` | Object | Yes | Auto-extracted field values from document |
| `missingFields` | Array | No | Fields that need user input |
| `qualityScore` | Number | No | Document quality score (0.0-1.0) |
| `documentType` | String | No | Type of document (default: "Aadhaar Card") |
| `confidence` | String | No | Overall confidence ('high'/'medium'/'low') |
| `sessionId` | String | Yes | Session identifier for API calls |
| `authId` | String | Yes | Authentication identifier |
| `onConfirm` | Function | Yes | Callback when user confirms data |
| `onCancel` | Function | Yes | Callback when user cancels |
| `onEdit` | Function | No | Callback when user edits a field |

## Validation Rules

### Mobile Number
- Must be exactly 10 digits
- Must start with 6, 7, 8, or 9

### Aadhaar Number  
- Must be exactly 12 digits
- Spaces and hyphens are automatically removed

### Date of Birth
- Supports DD/MM/YYYY and YYYY-MM-DD formats

### Pincode
- Must be exactly 6 digits

### Required Fields
All fields with values in `extractedFields` or listed in `missingFields` are considered required.

## Integration

### With Document Upload Panel

The component integrates with `DocumentUploadPanel` for the verification workflow:

```jsx
// In DocumentUploadPanel
import { DocumentConsentReview } from './document-consent-review'

// Replace MissingFieldsForm with DocumentConsentReview
<DocumentConsentReview
  extractedFields={verificationData.extractedFields}
  missingFields={verificationData.missingFields}
  qualityScore={verificationData.qualityScore}
  documentType={verificationData.documentType}
  confidence={verificationData.confidence}
  sessionId={verificationData.sessionId}
  authId={verificationData.authId}
  onConfirm={handleVerificationComplete}
  onCancel={handleVerificationCancel}
/>
```

## API Integration

The component makes a POST request to `/api/documents/confirm` when the user confirms:

```javascript
{
  session_id: sessionId,
  auth_id: authId,
  extracted_fields: extractedFields,
  user_fields: formData // Current form values including edits
}
```

Expected response format:
```javascript
{
  status: 'success',
  data: { /* saved document data */ }
}
```

## Styling

The component uses:
- Tailwind CSS for styling
- Custom color schemes for different field types
- Framer Motion for animations
- Lucide React for icons

## Testing Considerations

When implementing tests:
- Mock framer-motion animations
- Mock fetch API calls
- Test field validation rules
- Test edit/save workflows
- Test error handling
- Test responsive behavior

## Future Enhancements

Potential improvements:
- Add field-specific help text
- Implement undo/redo for edits
- Add keyboard shortcuts
- Support for file attachments
- Bulk edit mode
- Field comparison with previous versions