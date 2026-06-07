# Tamil Transliteration Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                     (React Frontend - Port 3000)                │
│                                                                 │
│  User types: "naa kudiiruppu nilai update pannaum"            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTP POST /api/chat
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NODE.JS BACKEND (Port 5000)                  │
│                    auth-app/backend/routes/chat.js              │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. Receive message                                       │  │
│  │ 2. Load user context (profile + history)                │  │
│  │ 3. Forward to RAG server                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTP POST /api/ask-stream
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PYTHON RAG SERVER (Port 8000)                  │
│                    pan-rag/api/routes.py                        │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ TRANSLITERATION CHECK                                    │  │
│  │ ┌────────────────────────────────────────────────────┐  │  │
│  │ │ 1. Is message Tamil romanization?                  │  │  │
│  │ │    → Pattern matching (< 5ms)                      │  │  │
│  │ │                                                     │  │  │
│  │ │ 2. If YES: Transliterate to Tamil script          │  │  │
│  │ │    → LLM call (~200-500ms)                         │  │  │
│  │ │    → Output: நான் குடும்ப நிலை மாற்ற வேண்டும்      │  │  │
│  │ │                                                     │  │  │
│  │ │ 3. Extract field intent                            │  │  │
│  │ │    → LLM call (~300-700ms)                         │  │  │
│  │ │    → Output: {field: "mother_name", intent: "update"} │  │
│  │ │                                                     │  │  │
│  │ │ 4. Update FlowManager state                        │  │  │
│  │ │    → fm.state["mother_name"] = value               │  │  │
│  │ │                                                     │  │  │
│  │ │ 5. Format response (Tamil + English)               │  │  │
│  │ │    → Return to user                                │  │  │
│  │ └────────────────────────────────────────────────────┘  │  │
│  │                                                          │  │
│  │ If NO: Continue to normal RAG processing                │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

```

## Component Interaction Flow

```
┌───────────┐
│   User    │
└─────┬─────┘
      │ "naa sambalam update pannaum"
      ▼
┌───────────────────────┐
│  Frontend (React)     │
│  - Chat UI            │
│  - Message input      │
└──────────┬────────────┘
           │ POST /api/chat
           ▼
┌───────────────────────────────────┐
│  Backend (Node.js)                │
│  - Session management             │
│  - User context loading           │
│  - Profile cache (Redis)          │
└──────────┬────────────────────────┘
           │ POST /api/ask-stream
           ▼
┌───────────────────────────────────────────────────┐
│  RAG Server (Python FastAPI)                      │
│  ┌─────────────────────────────────────────────┐  │
│  │  routes.py (ask_stream endpoint)            │  │
│  │  ├─→ handle_transliteration_request()       │  │
│  │  │    ├─→ is_tamil_romanized()              │  │
│  │  │    │    └─→ Regex pattern matching       │  │
│  │  │    │                                      │  │
│  │  │    ├─→ transliterate_to_tamil()          │  │
│  │  │    │    └─→ LLM.invoke()                 │  │
│  │  │    │                                      │  │
│  │  │    ├─→ extract_field_intent()            │  │
│  │  │    │    └─→ LLM.invoke()                 │  │
│  │  │    │                                      │  │
│  │  │    └─→ format_field_update_response()    │  │
│  │  │                                           │  │
│  │  └─→ Normal RAG processing (if not Tamil)   │  │
│  └─────────────────────────────────────────────┘  │
│                                                    │
│  ┌─────────────────────────────────────────────┐  │
│  │  transliteration.py (Core Module)           │  │
│  │  ├─→ TamilTransliterator class              │  │
│  │  │    ├─→ TAMIL_PATTERNS (regex)            │  │
│  │  │    ├─→ FIELD_MAPPING (dict)              │  │
│  │  │    ├─→ is_tamil_romanized()              │  │
│  │  │    ├─→ transliterate_to_tamil()          │  │
│  │  │    ├─→ extract_field_intent()            │  │
│  │  │    └─→ _llm_extract_intent()             │  │
│  │  │                                           │  │
│  │  ├─→ handle_transliteration_request()       │  │
│  │  └─→ format_field_update_response()         │  │
│  └─────────────────────────────────────────────┘  │
│                                                    │
│  ┌─────────────────────────────────────────────┐  │
│  │  agent/flow_manager.py                      │  │
│  │  └─→ FlowManager.state[field] = value       │  │
│  └─────────────────────────────────────────────┘  │
└────────────┬──────────────────────────────────────┘
             │ SSE Stream
             ▼
┌───────────────────────────────────┐
│  Backend (Node.js)                │
│  - Append to history              │
│  - Update profile cache           │
│  - Save to Supabase              │
└──────────┬────────────────────────┘
           │ SSE Stream
           ▼
┌───────────────────────┐
│  Frontend (React)     │
│  - Display Tamil      │
│  - Display English    │
│  - Show follow-ups    │
└──────────┬────────────┘
           ▼
┌───────────┐
│   User    │
└───────────┘
```

## Data Flow Diagram

```
INPUT: "naa sambalam update pannaum"
  │
  ├─→ Pattern Detection
  │     Input: Raw message string
  │     Process: Regex matching against TAMIL_PATTERNS
  │     Output: is_tamil = True
  │     Time: < 5ms
  │
  ├─→ Transliteration
  │     Input: "naa sambalam update pannaum"
  │     Process: LLM prompt → Invoke
  │     Output: "நான் சம்பளம் மாற்ற வேண்டும்"
  │     Time: 200-500ms
  │
  ├─→ Intent Extraction
  │     Input: Original + Tamil script
  │     Process: LLM prompt → Parse JSON
  │     Output: {
  │       field: "salary",
  │       value: null,
  │       intent: "update",
  │       confidence: "high"
  │     }
  │     Time: 300-700ms
  │
  ├─→ State Update
  │     Input: Field name + value
  │     Process: FlowManager.state[field] = value
  │     Output: Updated state
  │     Time: < 1ms
  │
  └─→ Response Formatting
        Input: Intent data + current value
        Process: Template substitution
        Output: "நான் சம்பளம் மாற்ற வேண்டும்\n\n
                I understand you want to update your Annual Income..."
        Time: < 1ms

TOTAL TIME: 500-1200ms
```

## Module Dependencies

```
transliteration.py
  ├─→ Depends on:
  │     ├─→ agent.llm (get_llm function)
  │     ├─→ agent.flow_manager (FlowManager class)
  │     ├─→ re (standard library)
  │     ├─→ typing (standard library)
  │     └─→ json (standard library)
  │
  └─→ Used by:
        └─→ api/routes.py
              ├─→ ask() endpoint
              └─→ ask_stream() endpoint
```

## Pattern Matching Architecture

```
TamilTransliterator.TAMIL_PATTERNS
  │
  ├─→ Pronouns
  │     ├─→ r'\b(?:naa|naan|naanu)\b'      → I/me
  │     └─→ r'\b(?:en|enna|enaku)\b'       → my/mine
  │
  ├─→ Family Terms
  │     ├─→ r'\b(?:kudumbam|kudiiruppu)\b' → family
  │     └─→ r'\b(?:thaayin|thaay|amma)\b'  → mother
  │
  ├─→ Action Words
  │     ├─→ r'\b(?:pannaum|pananum)\b'     → want to do
  │     └─→ r'\b(?:matra|maatra)\b'        → change
  │
  └─→ Field Names
        ├─→ r'\b(?:sambalam|varumanam)\b'  → salary
        ├─→ r'\b(?:peyar)\b'               → name
        ├─→ r'\b(?:mukhavari)\b'           → address
        └─→ r'\b(?:emailu|melil)\b'        → email
```

## LLM Integration Architecture

```
TamilTransliterator
  │
  ├─→ transliterate_to_tamil()
  │     │
  │     ├─→ Build prompt:
  │     │     "Convert the following Tamil text..."
  │     │
  │     ├─→ LLM.invoke(prompt)
  │     │     ├─→ Model: Defined in config.py
  │     │     ├─→ Temperature: Default
  │     │     └─→ Max tokens: Default
  │     │
  │     └─→ Parse response:
  │           └─→ Extract Tamil script from response.content
  │
  └─→ extract_field_intent()
        │
        ├─→ Build prompt:
        │     "You are analyzing a user message..."
        │     + Field descriptions
        │     + JSON format specification
        │
        ├─→ LLM.invoke(prompt)
        │     ├─→ Model: Defined in config.py
        │     ├─→ Temperature: Default
        │     └─→ Max tokens: Default
        │
        └─→ Parse response:
              ├─→ Extract JSON from markdown
              ├─→ json.loads()
              └─→ Validate fields
```

## Error Handling Architecture

```
┌─────────────────────────────┐
│  User Input                 │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Pattern Detection          │
│  (No errors possible)       │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  LLM Transliteration        │
│  ┌───────────────────────┐  │
│  │ Try: LLM call         │  │
│  │ Except: Fallback to   │  │
│  │   rule-based          │  │
│  └───────────────────────┘  │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Intent Extraction          │
│  ┌───────────────────────┐  │
│  │ Try: LLM call         │  │
│  │ Except: Fallback to   │  │
│  │   rule-based          │  │
│  └───────────────────────┘  │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Field Update               │
│  ┌───────────────────────┐  │
│  │ Validate field name   │  │
│  │ Check whitelist       │  │
│  │ Update if valid       │  │
│  └───────────────────────┘  │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Response Formatting        │
│  (No errors possible)       │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  User sees response         │
└─────────────────────────────┘
```

## Deployment Architecture

```
Production Environment
  │
  ├─→ Frontend (Vercel/Netlify)
  │     ├─→ Static React build
  │     └─→ Environment: VITE_BACKEND_URL
  │
  ├─→ Backend (Node.js on Cloud)
  │     ├─→ Port: 5000
  │     ├─→ Dependencies: Express, Supabase client
  │     └─→ Environment: RAG_URL, SUPABASE_*
  │
  └─→ RAG Server (Python on Cloud)
        ├─→ Port: 8000
        ├─→ Dependencies: FastAPI, LangChain, httpx
        ├─→ Modules:
        │     ├─→ api/routes.py
        │     ├─→ api/transliteration.py
        │     └─→ agent/*
        └─→ Environment: LLM_MODEL, UPSTASH_*
```

## Scaling Considerations

```
Current: Single Instance
  ├─→ Handles: 10-50 concurrent users
  ├─→ Bottleneck: LLM calls
  └─→ Response time: 500-1200ms

Optimized: Caching Layer
  ├─→ Cache: Common transliterations
  ├─→ Handles: 100-500 concurrent users
  ├─→ Hit rate: 60-70%
  └─→ Response time: 50-1200ms (cached vs fresh)

Production: Load Balanced
  ├─→ Instances: 3-5 RAG servers
  ├─→ Load balancer: Nginx/AWS ALB
  ├─→ Handles: 500-5000 concurrent users
  ├─→ Failover: Automatic
  └─→ Response time: 400-1000ms (distributed load)
```

## Monitoring Architecture

```
Logs
  ├─→ Detection logs
  │     └─→ "[transliteration] Tamil detected: True/False"
  │
  ├─→ Processing logs
  │     ├─→ "[transliteration] Transliterated: X"
  │     └─→ "[transliteration] Intent: {field, value}"
  │
  ├─→ Error logs
  │     ├─→ "[transliteration] LLM failed: reason"
  │     └─→ "[transliteration] Fallback to rule-based"
  │
  └─→ Performance logs
        └─→ "[ask-stream] Transliteration: XYZms"

Metrics
  ├─→ Detection rate: % of messages with Tamil
  ├─→ Transliteration success: % of LLM success
  ├─→ Intent accuracy: % correct field detection
  └─→ Response time: p50, p95, p99 latency
```

---

**Last Updated:** June 6, 2026  
**Architecture Version:** 1.0.0  
**Status:** ✅ Production Ready
