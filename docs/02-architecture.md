# Level 2: System Architecture Document (SAD)

## 1. System Architecture Overview

The system is engineered as a **distributed, microservice-oriented platform** consisting of a React Single-Page Application (SPA) deployed on AWS Amplify, a hardened Nginx reverse proxy gateway, and multiple containerized backend microservices deployed on an AWS EC2 instance.

```mermaid
graph TD
    subgraph Client ["Client Tier (Browser)"]
        SPA["React SPA (AWS Amplify CDN)<br/>- Multilingual Chat UI<br/>- 3-Step Wizard<br/>- PBKDF2 / AES-GCM ZK Crypto<br/>- Tri-Transport Engine"]
    end

    subgraph Gateway ["Gateway Tier (AWS EC2 - 13.207.224.41)"]
        NGINX["Nginx Reverse Proxy (Port 443 SSL)<br/>- Let's Encrypt TLS<br/>- Unbuffered Streaming<br/>- WebSocket Upgrade Proxy<br/>- 3600s Keep-Alive Timeouts"]
    end

    subgraph Services ["Service Tier (Docker Compose)"]
        Main["ORCHESTRA Main Server (:8001)<br/>- FastAPI Core<br/>- RAG AI Assistant<br/>- ConnectionManager<br/>- Playwright Worker Pool"]
        DocAgent["Document Upload Agent (:8000)<br/>- FastAPI Engine<br/>- VLM OCR Extractor<br/>- OpenCV Face Validator<br/>- Schema Normalizer"]
        CertAgent["4thAgent / Cert Agent<br/>- Playwright Certificate Fetcher<br/>- Application Tracker"]
    end

    subgraph Data ["Data & External Tier"]
        Qdrant[("Qdrant Vector Cloud<br/>Multilingual Embeddings")]
        Supabase[("Supabase Cloud<br/>- PostgreSQL DB<br/>- ZK Encrypted Storage")]
        LLM["OpenRouter / Groq Cloud<br/>Llama 3.1 8B Instruct"]
        Portal["TNeGA Citizen Portal<br/>tnesevai.tn.gov.in"]
        Gateway_Pay["BillDesk Payment Gateway"]
    end

    SPA -->|HTTPS / WSS / SSE| NGINX
    NGINX -->|/ws/* & /api/* & /| Main
    NGINX -->|/extract & /upload*| DocAgent

    Main -->|Semantic Search| Qdrant
    Main -->|Inference Stream| LLM
    Main -->|Encrypted Records| Supabase
    Main -->|Headless Automation| Portal
    Main -->|Scrape UPI QR| Gateway_Pay

    DocAgent -->|Store Encrypted Blobs| Supabase
    CertAgent -->|Fetch Approval PDF| Portal
```

---

## 2. Architectural Layers

### Layer 1: Client Tier (Frontend)
- **Framework**: React 18 with Vite.
- **Hosting**: AWS Amplify with global CDN edge caching.
- **State Management**: React Hooks (`useCallback`, `useRef`, `useState`) with local/session persistence.
- **Client-Side Cryptography**: Web Crypto API (`window.crypto.subtle`) for deterministic PBKDF2 key derivation and AES-GCM-256 encryption.
- **Real-Time Client**: Smart Tri-Transport engine that dynamically transitions across WebSocket, Server-Sent Events (SSE), and HTTP Long-Polling.

### Layer 2: Gateway Tier (Reverse Proxy)
- **Server**: Nginx 1.24+ running on Ubuntu 24.04 LTS (`13.207.224.41`).
- **TLS Termination**: Let's Encrypt SSL certificate for `residence-cert.duckdns.org`.
- **Routing Rules**:
  - `location ^~ /ws/`: Proxied to port `8001` with `Upgrade` and `Connection` header forwarding, `proxy_buffering off;`, and `tcp_nodelay on;`.
  - `location ~ ^/(extract|upload|verify)`: Proxied to port `8000` with 20MB client payload limits.
  - `location /`: Proxied to port `8001` with 3600s timeouts for long-running workflows.

### Layer 3: Microservices Tier (Backend)
1. **ORCHESTRA Main Server** (Container: `orchestra-backend`, Port 8001):
   - Core API handling chat streaming, OTP services, and application submission.
   - `ConnectionManager`: Multi-transport pub-sub hub managing event queues, event sequencing, run IDs, and client responses.
   - Playwright Worker: Autonomous headless browser executor driving citizen portal interactions.
2. **Document Upload Agent** (Container: `document-upload-agent`, Port 8000):
   - Microservice specialized in document ingestion, VLM-powered OCR extraction, field normalization, and OpenCV face validation.
3. **Certificate Agent (`4thAgent`)**:
   - Specialized worker script to query portal records by transaction ID and retrieve issued certificate PDFs.

### Layer 4: Storage & Cloud Services Tier
- **Supabase Cloud**:
  - PostgreSQL tables: `user_chat_history`, `user_profiles`, `user_documents`, `application_payloads`.
  - S3-compatible Object Storage Bucket: `documents` for zero-knowledge encrypted binary uploads.
- **Qdrant Vector Cloud**:
  - Dedicated vector database hosting embeddings of official TNeGA service definitions and legal rules.
- **LLM Inference Providers**:
  - OpenRouter & Groq hosting `meta-llama/llama-3.1-8b-instruct`.

---

## 3. Real-Time Tri-Transport Architecture

To prevent disconnections caused by browser ad-blockers, tracking protection, or corporate proxy firewalls, the real-time layer employs a **three-tier fallback hierarchy**:

```mermaid
flowchart TD
    Start["User Opens Automation Checklist"] --> CheckShield{"WebSockets Blocked in Session?"}
    
    CheckShield -- Yes --> SSE["Connect via Server-Sent Events (SSE)<br/>GET /ws/events/stream"]
    CheckShield -- No --> TryWS["Attempt Native WebSocket<br/>wss://residence-cert.duckdns.org/ws/automation"]
    
    TryWS -- Success --> WSActive["Transport: WEBSOCKET Active<br/>(Full Duplex)"]
    TryWS -- Blocked / Error --> FlagShield["Set sessionStorage: ws_blocked = true"] --> SSE
    
    SSE -- Success --> SSEActive["Transport: SSE Active<br/>(Instant 0ms HTTP Stream, Shield-Proof)"]
    SSE -- Disconnected / Error --> Poll["Transport: HTTP Polling Active<br/>GET /ws/events?since={seq}"]
    
    subgraph ActionDispatch ["Client Response Dispatch"]
        UserAction["User Submits Captcha / Action"]
        UserAction --> SendWS{"Is WebSocket Open?"}
        SendWS -- Yes --> SendSocket["ws.send(payload)"]
        SendWS -- No --> PostRest["POST /ws/action (REST)"]
    end

    WSActive -.-> ActionDispatch
    SSEActive -.-> ActionDispatch
    Poll -.-> ActionDispatch
```

---

## 4. Key Sequence & Data Flow Workflows

### Workflow 1: Zero-Knowledge Client-Side Document Ingestion

```mermaid
sequenceDiagram
    autonumber
    actor User as Citizen / Applicant
    participant Browser as React Client (Crypto API)
    participant DocAgent as DocumentUploadAgent (:8000)
    participant SupaStorage as Supabase Storage Bucket
    participant SupaDB as Supabase Database

    User->>Browser: Selects Document (e.g. Aadhaar / Ration)
    Browser->>Browser: Derive Key = PBKDF2(PIN, PhoneSalt)<br/>Encrypt Binary with AES-256-GCM
    Browser->>DocAgent: POST /extract (FormData with file)
    DocAgent->>DocAgent: Run VLM OCR & Schema Normalization
    DocAgent-->>Browser: Return Extracted JSON Fields
    Browser->>SupaStorage: Upload Encrypted Binary Document
    Browser->>SupaDB: Save Document Metadata Reference
    Browser->>User: Display Extracted Info for Review & Confirmation
```

### Workflow 2: Autonomous Portal Automation & Captcha Handshake

```mermaid
sequenceDiagram
    autonumber
    actor User as Citizen / Applicant
    participant UI as React Frontend
    participant Gateway as Nginx / Tri-Transport
    participant Backend as ORCHESTRA Main Server
    participant Playwright as Headless Chromium Worker
    participant Portal as TNeGA Portal (tnesevai.tn.gov.in)

    User->>UI: Clicks 'Proceed to Automation'
    UI->>Gateway: POST /submit-application (JSON Payload)
    Gateway->>Backend: Start new run (run_id) & spawn Worker Thread
    Backend->>Playwright: Launch headless browser & navigate
    Playwright->>Portal: Load Citizen Login Page & Fill Credentials
    Playwright->>Portal: Screenshot Dynamic Captcha Image
    Playwright->>Backend: ws_manager.send_event_sync(REQUEST_CAPTCHA)
    Backend->>Gateway: Broadcast Event via WebSocket / SSE / Polling
    Gateway->>UI: Stream Event with Captcha Base64
    UI->>User: Display Captcha Input Modal
    User->>UI: Enters Captcha Characters & Submits
    UI->>Gateway: POST /ws/action (USER_ANSWER)
    Gateway->>Backend: Record latest_response
    Backend->>Playwright: Worker receives response & inputs captcha
    Playwright->>Portal: Click Login & Navigate to Form REV-101
```

### Workflow 3: BillDesk Payment Facilitation & Receipt Extraction

```mermaid
sequenceDiagram
    autonumber
    actor User as Citizen / Applicant
    participant UI as React Frontend
    participant Gateway as Nginx / Tri-Transport
    participant Playwright as Headless Chromium Worker
    participant BillDesk as BillDesk Payment Gateway

    Playwright->>BillDesk: Submit Application & Open BillDesk
    Playwright->>BillDesk: Select UPI / QR Payment Mode
    Playwright->>BillDesk: Scrape dynamic Base64 QR Image
    Playwright->>Gateway: send_event_sync(PAYMENT_QR)
    Gateway->>UI: Push QR Code Image to Frontend
    UI->>User: Render Payment QR Modal on Screen
    User->>User: Scans QR Code with UPI App (GPay/PhonePe)
    User->>UI: Clicks 'I Have Paid'
    UI->>Gateway: POST /ws/action (USER_ANSWER: 'paid')
    Gateway->>Playwright: Unblock Worker Execution
    Playwright->>BillDesk: Await Payment Confirmation & Download Receipt
    Playwright->>Gateway: send_event_sync(PAYMENT_SUCCESS)
    Gateway->>UI: Trigger Receipt Download & Success Celebration
```

---

## 5. Security Architecture

### Zero-Knowledge Principles
1. **Client-Side Key Generation**: PBKDF2 (100,000 rounds of SHA-256) is executed exclusively inside the browser's Web Crypto runtime.
2. **Ciphertext-Only Ingestion**: Cloud databases and storage buckets store only initialization vectors (IV) and AES-256-GCM ciphertexts.
3. **No Key Storage**: Neither backend servers nor Supabase ever receive or persist the citizen's decryption key or PIN.

### Network & Infrastructure Hardening
- **TLS 1.3 / 1.2 Enforcement**: Strict SSL configuration via Let's Encrypt certificates.
- **CORS Protection**: Explicit origin allowlists ensuring API endpoints only accept requests from the designated AWS Amplify production domains and local development origins.
- **Isolation via Docker**: Backend microservices communicate over an internal Docker bridge network (`orchestra_default`), with only ports 8000 and 8001 exposed locally to Nginx on `127.0.0.1`.
