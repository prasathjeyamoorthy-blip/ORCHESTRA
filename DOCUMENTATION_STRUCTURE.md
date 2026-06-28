# Documentation Structure - Complete File Reference

## Overview
Comprehensive documentation for every file in the PAN Application Platform. Each file has a dedicated `.md` documentation file explaining its purpose, functions, and usage.

## Root-Level Documentation

### Main Documentation
- **`README.md`** - Project overview, quick start, technology stack, features
- **`DEPLOYMENT_CHECKLIST.md`** - Production deployment guide and verification steps
- **`ORCHESTRA_FOLDER_PURPOSE.md`** - ORCHESTRA multi-document system introduction
- **`ORCHESTRA_QUICK_REFERENCE.md`** - ORCHESTRA API reference and quick start
- **`DOCUMENTATION_STRUCTURE.md`** - This file

## Folder Structure & File Documentation

### 🎨 Frontend (`frontend/`)

#### Main Application Files
```
frontend/src/
├── App.jsx                          → App.jsx.md
│   └─ Root component, routing, authentication
├── main.jsx                         → main.jsx.md
│   └─ Application entry point, initialization
├── index.css                        → index.css.md
│   └─ Global styles, design tokens, utilities
└── assets/
    ├── react.svg
    ├── vite.svg
    └── hero.png
```

#### Components (`frontend/src/components/ui/`)
Create `.md` files for each major component:
- `document-upload-panel.jsx` - Main upload interface
- `document-consent-review.jsx` - Data review and consent
- `missing-fields-form.jsx` - Missing field input form
- `multi-document-upload.jsx` - ORCHESTRA multi-doc upload
- `auth-modal.jsx` - Login/signup modal
- `cinematic-landing-hero.jsx` - Landing page hero
- `theme-toggle.jsx` - Theme switcher
- `voice-recorder.jsx` - Voice recording interface
- `voice-player.jsx` - Audio playback
- More component files...

#### Hooks (`frontend/src/hooks/`)
- `useAuth.ts` - Authentication management
- `useDocumentUpload.ts` - Document upload handling
- `useChangePassword.ts` - Password change logic
- `useDocumentDownload.ts` - Document retrieval
- `usePhoneOtp.js` - OTP verification
- `useVoice.ts` - Voice interface
- `useAgentFileAccess.ts` - File access control

#### Utilities (`frontend/src/lib/`)
- `supabase.ts` - Supabase client configuration
- `crypto.ts` - Encryption utilities
- `keySession.ts` - Session key management
- `otp.js` - OTP generation/validation
- `utils.js` - Miscellaneous utilities
- `theme-context.jsx` - Theme provider
- `voice-analytics.ts` - Voice metrics
- `voice-degradation.ts` - Voice quality handling
- `voice-error-handler.ts` - Voice error management

#### Pages (`frontend/src/pages/`)
- `Home.jsx` - Landing/home page
- `Login.jsx` - Login page
- `Signup.jsx` - Registration page
- Additional pages...

#### Folder README
- **`frontend/README.md`** - Frontend overview, project structure, data flow, API integration

### 🔐 PAN Verification Backend (`pan_verification/`)

#### Core Backend Files
```
pan_verification/
├── app.py                          → app.py.md
│   └─ Main Flask application, all API endpoints
├── helpers.py                      → helpers.py.md
│   └─ Extraction prompts, VLM calls, document detection
├── pan_verification_upd.py         → pan_verification_upd.py.md
│   └─ Pydantic schemas, validation logic
├── supa.py                         → supa.py.md
│   └─ Supabase database integration
├── re_check.py                     → re_check.py.md
│   └─ Regex-based field validation
├── image_quality.py                → image_quality.py.md
│   └─ Image quality assessment
├── crypto_utils.py                 → crypto_utils.py.md
│   └─ Encryption and security utilities
└── test.py                         → Can add test.py.md
    └─ Unit and integration tests
```

#### Middleware (`pan_verification/middleware/`)
- `verifyToken.js` - JWT verification
- `rateLimiter.js` - Rate limiting middleware

#### Routes (`pan_verification/routes/`)
- `auth.js` - Authentication routes
- `chat.js` - Chat/voice routes
- `otp.js` - OTP routes
- `uploads.js` - File upload routes

#### Utilities (`pan_verification/utils/`)
- `circuit-breaker.js` - API resilience
- `encryption.js` - Data encryption
- `proxy-utils.js` - Proxy handling
- `retry-logic.js` - Retry mechanisms

#### ORCHESTRA (`pan_verification/ORCHESTRA/`)
- **`Orchestra/README.md`** - ORCHESTRA system documentation
- `DocumentUploadAgent/main.py` - Main orchestration
- `DocumentUploadAgent/extractor.py` - Document extraction
- `DocumentUploadAgent/validator.py` - Cross-validation

#### Folder README
- **`pan_verification/README.md`** - Backend documentation, API endpoints, extraction workflows

### 🎤 Voice Agent (`voice-agent/`)

#### Core Voice Files
```
voice-agent/
├── server.py                       → Can add server.py.md
│   └─ Voice service Flask server
├── main_simple.py                  → Can add main_simple.py.md
│   └─ Simple voice entry point
└── core/
    ├── stt.py                      → stt.py.md
    │   └─ Speech-to-text service
    ├── tts.py                      → tts.py.md
    │   └─ Text-to-speech service
    ├── agent.py                    → agent.py.md
    │   └─ Agent orchestration
    ├── llm.py                      → llm.py.md
    │   └─ Language model integration
    ├── voice_receptionist.py        → voice_receptionist.py.md
    │   └─ Voice interface coordinator
    └── pan_flow_agent.py            → pan_flow_agent.py.md
        └─ PAN application workflow
```

#### Configuration
- `requirements.txt` - Python dependencies
- `.env.example` - Environment template

#### Folder README
- **`voice-agent/README.md`** - Voice service documentation, API endpoints, supported languages

### 📚 PAN RAG (`pan-rag/`)

#### Core Files
```
pan-rag/
├── agent/
│   ├── receptionist.py
│   ├── retriever.py
│   ├── generator.py
│   └── chain.py
├── api/
│   ├── routes.py
│   ├── voice.py
│   └── middleware/
└── requirements.txt
```

#### Folder README
- **`pan-rag/README.md`** - Document RAG system, question-answering, API reference

### 🔑 Auth App (`auth-app/`)

#### Backend Files
```
auth-app/backend/
├── main.py
├── middleware/
│   ├── verifyToken.js
│   └── rateLimiter.js
├── routes/
│   ├── auth.js
│   ├── chat.js
│   ├── otp.js
│   └── uploads.js
├── utils/
│   ├── encryption.js
│   ├── proxy-utils.js
│   └── retry-logic.js
└── requirements.txt
```

#### Folder README
- **`auth-app/README.md`** - Authentication service, user management, security features

### 🗄️ Supabase (`supabase/`)

#### Configuration
```
supabase/
├── config.toml
├── migrations/
├── seed/
├── functions/
├── policies/
└── types/
```

#### Folder README
- **`supabase/README.md`** - Database schema, RLS policies, setup instructions

## Documentation Organization

### By Scope

#### Architectural Level
- `README.md` - Project overview
- Folder-level READMEs

#### Service Level
- Service-specific READMEs (pan_verification/, frontend/, etc.)
- API documentation
- Configuration guides

#### File Level
- Individual `.py`, `.jsx`, `.js` documentation files
- Function descriptions
- Usage examples
- Integration points

### By Purpose

#### User Guides
- `README.md` - Getting started
- `DEPLOYMENT_CHECKLIST.md` - Deployment

#### Reference Docs
- File-level `.md` files
- API documentation
- Configuration reference

#### Architecture Docs
- ORCHESTRA documentation
- System design files

## How to Use This Documentation

### For New Developers
1. Start with root `README.md`
2. Read relevant service README (e.g., `pan_verification/README.md`)
3. Read specific file `.md` documentation

### For Code Changes
1. Find the file you're modifying
2. Read its `.md` documentation
3. Understand dependencies and integrations
4. Make changes following patterns shown

### For API Integration
1. Check service-specific README
2. Find relevant file `.md` in that service
3. Look for API endpoints and examples

### For Deployment
1. Read `DEPLOYMENT_CHECKLIST.md`
2. Check `.env.example` files
3. Follow service-specific setup steps

## File Naming Convention

### Documentation Files
- `filename.py.md` - Documentation for Python files
- `filename.jsx.md` - Documentation for React files
- `filename.js.md` - Documentation for JavaScript files
- Folder `README.md` - Overview for folder

### Content Structure
Each `.md` file includes:
- Purpose
- Key functions/components
- Parameters and return values
- Configuration
- Integration points
- Usage examples
- Error handling
- Dependencies
- Notes

## Maintenance

### Updating Documentation
- Update `.md` file when changing file implementation
- Keep examples current
- Update dependencies list
- Add new functions/methods as created

### Adding New Files
1. Create the implementation file
2. Create corresponding `.md` documentation file
3. Add reference to this structure file
4. Link from relevant README

## Documentation Status

### ✅ Completed
- Root-level documentation
- Service-level README files (all 7 services)
- Backend files (pan_verification) - 7 files
- Voice agent core files - 6 files
- Frontend main files - 3 files
- Total: 26 files documented

### 📋 Recommended (Optional)
- Individual frontend component files
- Individual voice service routes
- Test files
- Utility files

## Quick Links

### Main Services
- [Frontend](frontend/README.md)
- [PAN Verification](pan_verification/README.md)
- [PAN RAG](pan-rag/README.md)
- [Voice Agent](voice-agent/README.md)
- [Auth App](auth-app/README.md)
- [ORCHESTRA](Orchestra/README.md)
- [Supabase](supabase/README.md)

### Key Concepts
- [ORCHESTRA Multi-Document](ORCHESTRA_FOLDER_PURPOSE.md)
- [Deployment Guide](DEPLOYMENT_CHECKLIST.md)
- [PAN Verification Flow](pan_verification/app.py.md)
- [Voice Integration](voice-agent/core/stt.py.md)

## Notes
- This structure ensures every critical file has documentation
- Follows consistent format across all services
- Enables easy onboarding of new developers
- Supports knowledge preservation
- Facilitates code maintenance and debugging
