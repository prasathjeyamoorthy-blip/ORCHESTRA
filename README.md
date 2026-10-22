# TNeGA Residence Certificate AI Assistant & Automation Agent

An end-to-end AI assistant and autonomous agent designed for the Tamil Nadu e-Governance Agency (TNeGA) portal to streamline citizen residence certificate issuance.

---

## 🌟 Key Features

- **Conversational AI Agent**: Multilingual RAG chatbot powered by Llama 3 on OpenRouter/Groq with Qdrant vector store.
- **Automated Document Extraction**: Zero-knowledge encrypted document extraction supporting Aadhaar Card, Ration Card, Driving License, and Applicant Photo with face validation.
- **Playwright Automation Engine**: Headless browser automation for citizen portal login, CAN lookup/registration, dynamic form population, self-declaration handling, and BillDesk payment gateway integration.
- **Tri-Transport Real-Time Communication**:
  - **WebSocket (`/ws/automation`)**: Instant full-duplex communication.
  - **Server-Sent Events (`/ws/events/stream`)**: 0ms streaming immune to ad-blockers, tracker shields, and corporate proxies.
  - **HTTP Long-Polling (`/ws/events`)**: Fallback for high-security or restricted network environments.
  - **REST Actions (`/ws/action`)**: Deterministic delivery of interactive prompts (captchas, OTPs, signatures).

---

## 🏗️ Architecture

```
                                  ┌───────────────────────────┐
                                  │      React Frontend       │
                                  │    (Vite / AWS Amplify)   │
                                  └─────────────┬─────────────┘
                                                │ HTTPS / WSS / SSE
                                                ▼
                                  ┌───────────────────────────┐
                                  │       Nginx Reverse       │
                                  │           Proxy           │
                                  └──────┬─────────────┬──────┘
                                         │             │
                    Port 8001 (/ /ws)    │             │ Port 8000 (/extract /upload)
                                         ▼             ▼
                           ┌──────────────────┐   ┌───────────────────────────┐
                           │ ORCHESTRA Main   │   │ Document Upload Agent     │
                           │  - FastAPI       │   │  - OCR & Schema Extraction│
                           │  - RAG Agent     │   │  - Face Validator         │
                           │  - Playwright    │   │  - Supabase ZK Storage    │
                           └──────────────────┘   └───────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Backend Services (Docker Compose)

```bash
cd ORCHESTRA
docker compose up -d --build
```

### 2. Frontend (Local Development)

```bash
cd ORCHESTRA/frontend
npm install
npm run dev
```

---

## 🔒 Security & Privacy

- **Zero-Knowledge Encryption**: User documents are encrypted in the browser before storage in Supabase.
- **Privacy Shields & Adblock Compatibility**: Native Server-Sent Events (SSE) ensure that browser tracker blockers (Vivaldi, Brave, uBlock) never interfere with real-time automation.
- **Ephemeral Automation Data**: Local browser runs and downloads are cleaned up dynamically after execution.
