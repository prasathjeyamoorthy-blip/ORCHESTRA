# 🚀 Getting Started - Quick Navigation Guide

## Welcome to the PAN Application Platform!

This guide helps you quickly find the documentation you need.

---

## 🎯 Choose Your Role

### 👨‍💻 I'm a **Backend Developer**
Working on API endpoints, database, document extraction, and business logic.

**Start Here:**
1. Read [`pan_verification/README.md`](pan_verification/README.md) - Backend overview
2. Read [`pan_verification/app.py.md`](pan_verification/app.py.md) - API endpoints
3. Read [`pan_verification/helpers.py.md`](pan_verification/helpers.py.md) - Document extraction
4. Check other core files as needed

**Key Files to Know:**
- `app.py` - Main Flask API server
- `helpers.py` - Document extraction and VLM calls
- `supa.py` - Database operations
- `pan_verification_upd.py` - Data schemas

---

### 🎨 I'm a **Frontend Developer**
Building UI components, pages, and user interfaces.

**Start Here:**
1. Read [`frontend/README.md`](frontend/README.md) - Frontend overview
2. Read [`frontend/src/App.jsx.md`](frontend/src/App.jsx.md) - Main component
3. Read [`frontend/src/main.jsx.md`](frontend/src/main.jsx.md) - Entry point
4. Explore specific components in `frontend/src/components/`

**Key Files to Know:**
- `App.jsx` - Root component and routing
- `main.jsx` - Application initialization
- `index.css` - Global styles and design tokens
- `components/ui/` - Reusable UI components

---

### 🎤 I'm a **Voice/Audio Developer**
Working on speech-to-text, text-to-speech, and voice interactions.

**Start Here:**
1. Read [`voice-agent/README.md`](voice-agent/README.md) - Voice overview
2. Read [`voice-agent/core/stt.py.md`](voice-agent/core/stt.py.md) - Speech recognition
3. Read [`voice-agent/core/tts.py.md`](voice-agent/core/tts.py.md) - Speech synthesis
4. Read [`voice-agent/core/agent.py.md`](voice-agent/core/agent.py.md) - Orchestration

**Key Files to Know:**
- `stt.py` - Speech-to-text service
- `tts.py` - Text-to-speech service
- `agent.py` - Agent coordination
- `pan_flow_agent.py` - PAN workflow automation

---

### 🔑 I'm an **Authentication/Security Developer**
Handling user authentication, authorization, and security.

**Start Here:**
1. Read [`auth-app/README.md`](auth-app/README.md) - Auth overview
2. Read [`pan_verification/crypto_utils.py.md`](pan_verification/crypto_utils.py.md) - Encryption

**Key Files to Know:**
- `auth-app/backend/` - Authentication service
- `crypto_utils.py` - Encryption and security utilities

---

### 🗄️ I'm a **Database Administrator**
Managing database schema, migrations, and data storage.

**Start Here:**
1. Read [`supabase/README.md`](supabase/README.md) - Database overview
2. Check database configuration files

**Key Files to Know:**
- `supabase/config.toml` - Database configuration
- `supabase/migrations/` - Schema migrations
- `supabase/policies/` - Row-level security

---

### 🚀 I'm **DevOps/Deployment**
Deploying and maintaining the application in production.

**Start Here:**
1. Read [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md) - Deployment guide
2. Check `.env.example` files in each service
3. Follow security and setup procedures

---

### 📚 I'm a **Documentation/Project Manager**
Understanding the overall system and project structure.

**Start Here:**
1. Read [`README.md`](README.md) - Project overview (main entry point)
2. Read [`DOCUMENTATION_STRUCTURE.md`](DOCUMENTATION_STRUCTURE.md) - Documentation map
3. Read [`DOCUMENTATION_COMPLETE.md`](DOCUMENTATION_COMPLETE.md) - Summary of all docs

---

## 📍 Main Documentation Files

### Root Level (Start Here!)
| File | Purpose | Read Time |
|------|---------|-----------|
| [`README.md`](README.md) | Project overview, quick start, tech stack | 15 min |
| [`DOCUMENTATION_STRUCTURE.md`](DOCUMENTATION_STRUCTURE.md) | Map of all documentation | 10 min |
| [`GETTING_STARTED.md`](GETTING_STARTED.md) | This file - quick navigation | 5 min |
| [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md) | Production deployment steps | 10 min |

### Service Documentation
| Service | Location | Purpose |
|---------|----------|---------|
| Backend | [`pan_verification/README.md`](pan_verification/README.md) | Document extraction, API endpoints |
| Frontend | [`frontend/README.md`](frontend/README.md) | Web UI, components, state |
| Voice | [`voice-agent/README.md`](voice-agent/README.md) | Speech recognition and synthesis |
| Document RAG | [`pan-rag/README.md`](pan-rag/README.md) | Document retrieval system |
| Authentication | [`auth-app/README.md`](auth-app/README.md) | User management and security |
| ORCHESTRA | [`Orchestra/README.md`](Orchestra/README.md) | Multi-document processor |
| Database | [`supabase/README.md`](supabase/README.md) | Database schema and setup |

---

## 🔍 Quick Lookup by Task

### I need to...

#### **Upload a new document**
→ See `pan_verification/app.py.md` section "POST /api/verify"

#### **Add a new API endpoint**
→ See `pan_verification/app.py.md` for endpoint structure and patterns

#### **Create a new React component**
→ See `frontend/README.md` → Components section

#### **Implement speech recognition**
→ See `voice-agent/core/stt.py.md`

#### **Extract data from a document**
→ See `pan_verification/helpers.py.md`

#### **Store data in database**
→ See `pan_verification/supa.py.md`

#### **Validate extracted fields**
→ See `pan_verification/re_check.py.md`

#### **Deploy to production**
→ See `DEPLOYMENT_CHECKLIST.md`

#### **Understand multi-document processing**
→ See `Orchestra/README.md`

#### **Set up authentication**
→ See `auth-app/README.md`

---

## 📊 Understanding the System

### Simple Architecture Overview

```
User Interface (Frontend)
    ↓
API Gateway (Flask Backend)
    ↓
    ├─ Document Processing (extraction, validation)
    ├─ Voice Processing (STT, TTS)
    ├─ Multi-Document (ORCHESTRA)
    └─ Database Operations (Supabase)
```

### Key Workflows

#### Document Upload Flow
```
User uploads document
    ↓
Image quality check
    ↓
Document type detection
    ↓
AI extraction (NVIDIA Vision Model)
    ↓
Field validation
    ↓
User reviews and confirms
    ↓
Data saved to database
```

#### Voice Interaction Flow
```
User speaks
    ↓
Speech-to-Text (STT)
    ↓
Intent recognition
    ↓
Business logic processing
    ↓
Response generation
    ↓
Text-to-Speech (TTS)
    ↓
Audio played to user
```

---

## 🎓 Learning Paths

### Path 1: Full System Orientation (2-3 hours)
For new team members who want overall understanding:
1. [`README.md`](README.md) - 20 min
2. [`pan_verification/README.md`](pan_verification/README.md) - 20 min
3. [`frontend/README.md`](frontend/README.md) - 20 min
4. [`voice-agent/README.md`](voice-agent/README.md) - 20 min
5. [`Orchestra/README.md`](Orchestra/README.md) - 15 min
6. Specific deep-dives as interested

### Path 2: Backend Specialist (1.5-2 hours)
For backend developers:
1. [`pan_verification/README.md`](pan_verification/README.md)
2. [`pan_verification/app.py.md`](pan_verification/app.py.md)
3. [`pan_verification/helpers.py.md`](pan_verification/helpers.py.md)
4. [`pan_verification/pan_verification_upd.py.md`](pan_verification/pan_verification_upd.py.md)
5. [`pan_verification/supa.py.md`](pan_verification/supa.py.md)

### Path 3: Frontend Specialist (1-1.5 hours)
For frontend developers:
1. [`frontend/README.md`](frontend/README.md)
2. [`frontend/src/App.jsx.md`](frontend/src/App.jsx.md)
3. [`frontend/src/main.jsx.md`](frontend/src/main.jsx.md)
4. Component exploration

### Path 4: Voice Integration (1.5 hours)
For voice developers:
1. [`voice-agent/README.md`](voice-agent/README.md)
2. [`voice-agent/core/stt.py.md`](voice-agent/core/stt.py.md)
3. [`voice-agent/core/tts.py.md`](voice-agent/core/tts.py.md)
4. [`voice-agent/core/agent.py.md`](voice-agent/core/agent.py.md)

---

## 💡 Documentation Tips

### How to Find What You Need

**By File Name**
→ Search for `filename.md` in the documentation

**By Function/API**
→ Check the service README first, then file documentation

**By Concept**
→ Use `DOCUMENTATION_STRUCTURE.md` to find concept location

**By Error**
→ Check the file's `.md` documentation error handling section

### How to Use Documentation

1. **Read the Purpose** - Understand what the file does
2. **Check Key Functions** - See available functions/methods
3. **Review Parameters** - Understand function inputs
4. **Check Examples** - See how to use it
5. **Review Integration** - Understand dependencies

---

## 📞 Getting Help

### If you're stuck:

1. **Check the relevant file's `.md` documentation**
   - Look for function signatures
   - Check error handling section
   - Review integration points

2. **Look at code examples**
   - Most `.md` files include usage examples
   - Check similar functions for patterns

3. **Check related files**
   - Integration points show dependencies
   - Follow the data flow

4. **Ask the team**
   - Share what you've tried
   - Reference the documentation you've read
   - Suggest what documentation might be missing

---

## 🎯 Next Steps

### Choose ONE:
- [ ] Read your role's starting point (see above)
- [ ] Follow a learning path that matches your interests
- [ ] Start with [`README.md`](README.md) for full context
- [ ] Jump to a specific service you're working on

### Then:
- [ ] Run the project locally (see `README.md`)
- [ ] Try a simple task using documentation as guide
- [ ] Explore the code while reading `.md` files
- [ ] Contribute documentation improvements you find

---

## ✅ Quick Verification

You know you're in the right place if:
- ✅ You can find documentation for your area
- ✅ You understand the system architecture
- ✅ You can locate API endpoints
- ✅ You can find usage examples
- ✅ You know how to get help

---

**Ready? Pick your role above and start reading! 🚀**

Last updated: June 28, 2026
