# Frontend - PAN Application Platform

React-based web application providing user interface for document upload, extraction preview, data review, and multi-document processing.

## Overview

The frontend handles:
- User authentication (signup/login)
- Document upload with drag-and-drop
- Real-time image quality feedback
- Extracted data display with icons and validation
- Missing fields form for user input
- Final consent and review screen
- Multi-document upload workflow

## Project Structure

```
frontend/
├── src/
│   ├── components/ui/          # UI components
│   │   ├── document-upload-panel.jsx          # Main upload component
│   │   ├── document-consent-review.jsx        # Data review and consent
│   │   ├── missing-fields-form.jsx            # Missing fields input
│   │   ├── multi-document-upload.jsx          # Multi-doc upload (ORCHESTRA)
│   │   ├── auth-modal.jsx                     # Login/signup modal
│   │   └── ... other components
│   ├── hooks/                   # Custom React hooks
│   │   ├── useAuth.ts                         # Authentication
│   │   ├── useDocumentUpload.ts               # Document handling
│   │   └── ... other hooks
│   ├── lib/                     # Utilities and configs
│   │   ├── supabase.ts                        # Supabase client
│   │   ├── crypto.ts                          # Encryption utilities
│   │   └── theme-context.jsx                  # Theme provider
│   ├── pages/                   # Page components
│   │   ├── Home.jsx                           # Landing page
│   │   ├── Login.jsx                          # Login page
│   │   └── Signup.jsx                         # Signup page
│   ├── App.jsx                  # Main app component
│   ├── main.jsx                 # Entry point
│   └── index.css                # Global styles
├── public/                      # Static assets
│   ├── icons.svg                # Icon sprite
│   └── favicon.svg
├── package.json                 # Dependencies
├── vite.config.js              # Vite configuration
└── README.md                    # This file
```

## Key Components

### DocumentUploadPanel
Main component for single document upload, extraction, and data display.

**Features:**
- Drag-and-drop file upload
- Real-time image quality scoring
- Document type detection
- Field extraction display
- Missing fields detection
- Quality feedback messages

**Props:**
- `onDataExtracted` - Callback when data is extracted
- `authId` - User authentication ID

### DocumentConsentReview
Displays extracted data for user review and consent.

**Features:**
- 25+ field display with icons
- Color-coded by field category
- Confidence badges
- In-line field editing
- Real-time validation
- Consent checkbox
- Submit button

**Props:**
- `extractedData` - Data to display
- `onConfirm` - Callback on user confirmation
- `onCancel` - Callback to cancel

### MissingFieldsForm
Form for user to fill in any missing required fields.

**Features:**
- Display of already-extracted fields (read-only)
- Input fields for missing data
- Field validation
- Submit and cancel buttons
- Summary of extraction progress

**Props:**
- `missingFields` - Array of missing field definitions
- `extractedData` - Already extracted data
- `onComplete` - Callback when form submitted
- `onCancel` - Callback to cancel

### MultiDocumentUpload
Handles multi-document upload and ORCHESTRA processing.

**Features:**
- Multiple file upload
- Document type selection per file
- Progress tracking
- Cross-document validation results
- Merged data display

**Props:**
- `onDataExtracted` - Callback with merged data
- `authId` - User authentication ID

## Data Flow

```
Upload Document
    ↓
Display Quality Feedback
    ↓
Extract Fields (API call)
    ↓
Display Extracted Data
    ↓
Check Missing Fields
    ├─ If missing → Show MissingFieldsForm
    │   ↓
    │   User Fills Fields
    │   ↓
    └─ User Submits
    ↓
Show DocumentConsentReview
    ↓
User Reviews Data
    ↓
User Provides Consent
    ↓
Submit to /api/confirm_save
    ↓
Data Saved to Database
```

## Hooks

### useAuth
Manages user authentication state and operations.

```typescript
const { user, login, signup, logout, isLoading } = useAuth();
```

### useDocumentUpload
Handles document upload and extraction.

```typescript
const {
  uploadDocument,
  extractedData,
  missingFields,
  isLoading,
  error,
  qualityScore
} = useDocumentUpload();
```

### useVoice
Manages voice input/output functionality.

```typescript
const { recordAudio, playAudio, isRecording, transcript } = useVoice();
```

## API Integration

### Upload Endpoint
```javascript
POST /api/verify
Content-Type: multipart/form-data

Parameters:
- auth_id: string
- aadhaar: File

Response:
{
  status: "missing_fields" | "extracted_for_verification",
  extracted_fields: object,
  missing_fields: array,
  all_extracted_data: object,
  quality_score: number
}
```

### Confirm Save Endpoint
```javascript
POST /api/confirm_save
Content-Type: application/json

{
  auth_id: string,
  extracted_fields: object,
  user_fields: object
}

Response:
{
  status: "success",
  doc_id: string,
  person_id: string,
  saved_data: object
}
```

## Environment Variables

```
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_API_BASE_URL=http://localhost:5000
```

## Installation & Setup

```bash
# Install dependencies
npm install

# Create .env file
cp .env.example .env
# Edit .env with your configuration

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Development

### Running Tests
```bash
npm run test
```

### Linting
```bash
npm run lint
```

### Format Code
```bash
npm run format
```

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Performance Optimizations

- Code splitting per route
- Image optimization
- Lazy loading of components
- Caching strategies
- Compression enabled

## Accessibility

- WCAG 2.1 Level AA compliance
- Semantic HTML
- ARIA labels where needed
- Keyboard navigation
- Color contrast ratios met

## Styling

Uses TailwindCSS for utility-first styling with custom components for:
- Cards with shadows and borders
- Buttons with hover states
- Input fields with validation feedback
- Modal dialogs
- Color-coded field displays

## State Management

- React hooks for local state
- Supabase for user state
- Custom context for theme/language

## Error Handling

- Network error display
- Validation error messages
- User-friendly error alerts
- Automatic retry for failed uploads
- Graceful degradation

## Features

### ✅ Completed
- Document upload with validation
- Real-time image quality scoring
- Field extraction display
- Missing fields detection and form
- Consent review screen
- Multi-field display with icons
- Color-coded field categories
- Inline field editing
- Data persistence

### 🔄 In Progress
- Multi-document upload UI
- Advanced validation feedback

### 📋 Planned
- Batch document upload
- Document history view
- Export functionality
- Advanced search

## Troubleshooting

**Upload fails with 401**
- Check authentication status
- Ensure auth token is valid
- Log out and log in again

**Image quality scoring is incorrect**
- Ensure lighting is good
- Check image resolution (minimum 150x150px)
- Verify document is clearly visible

**Missing fields not showing**
- Refresh page
- Check browser console for errors
- Verify API response

## Contributing

Follow the component structure and naming conventions when adding new components.

## License

Proprietary and confidential.
