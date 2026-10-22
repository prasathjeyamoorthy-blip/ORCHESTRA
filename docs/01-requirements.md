# Level 1: System Requirements Specification (SRS)

## 1. Executive Summary & Vision

The **TNeGA Residence Certificate AI Assistant & Autonomous Agent** is an end-to-end intelligent platform built to streamline and automate the issuance of Residence Certificates (*குடியிருப்புச் சான்றிதழ்*) on the Tamil Nadu e-Governance Agency (TNeGA) Citizen Portal.

Traditionally, citizens face complex hurdles:
- Navigating confusing portal menus and identifying required documentation.
- Manual data entry errors across extensive multi-stage forms.
- Stringent portal file-size and format validation rules leading to frequent upload failures.
- Captcha hurdles, OTP prompts, and payment gateway navigation.

This platform bridges the gap by pairing a **conversational RAG AI assistant** with an **autonomous headless Playwright agent**, **zero-knowledge document encryption**, and a **tri-transport real-time event pipeline**.

---

## 2. Problem Statement & Objectives

### Core Problems Solved
1. **Friction in Public Service Delivery**: Citizens often spend hours navigating e-Sevai forms, leading to abandoned applications.
2. **Data Privacy in Public Clouds**: Sensitive citizen documents (Aadhaar, Ration Card, Driving License, Photo) must not be stored in plaintext on third-party servers.
3. **Fragile Web Automation**: Real-time communication between headless automation workers and user browsers often breaks due to browser privacy shields, ad-blockers, dynamic DNS restrictions, and corporate proxies.

### System Objectives
- **Zero-Friction Guidance**: Answer citizen questions in Tamil and English with authoritative references using Retrieval-Augmented Generation (RAG).
- **Zero-Knowledge Privacy**: Ensure all citizen identity documents are encrypted directly in the client browser using AES-256-GCM before transmission.
- **Autonomous Execution**: Automatically log into the portal, fill application forms, upload verified documents, and generate instant BillDesk payment QR codes.
- **Fault-Tolerant Real-Time Streaming**: Deliver uninterrupted status updates, captchas, and payment prompts regardless of network restrictions or browser ad-blockers.

---

## 3. Stakeholder Personas

| Persona | Role | Needs & Expectations |
| :--- | :--- | :--- |
| **Citizen Applicant** | End-User | Simple UI, guided document upload, instant eligibility answers in Tamil/English, seamless payment. |
| **Portal Operator / Kiosk** | E-Sevai Operator | Fast bulk document ingestion, automatic OCR extraction, error-free automated submission. |
| **System Administrator** | DevOps / Platform Owner | High availability, Dockerized microservices, zero plaintext credential leakage, production observability. |

---

## 4. Functional Requirements (FR)

### FR-1: Multilingual Conversational AI & Guidance
- **FR-1.1**: The system shall provide an interactive chat interface supporting both English and Tamil (*தமிழ்*).
- **FR-1.2**: The assistant shall use Retrieval-Augmented Generation (RAG) against official TNeGA service rules, CAN guidelines, and legal requirements.
- **FR-1.3**: The assistant shall automatically recognize applicant intent (e.g., eligibility, required documents, fee structure, tracking) and trigger appropriate UI actions (e.g., launching the application checklist).

### FR-2: Zero-Knowledge Client-Side Document Encryption
- **FR-2.1**: All documents (Aadhaar, Ration Card, Driving License, Photo) shall be encrypted on the citizen's device prior to upload.
- **FR-2.2**: The encryption key shall be derived deterministically using **PBKDF2** (100,000 iterations) with SHA-256 from the user's PIN and normalized phone number.
- **FR-2.3**: Neither the PIN nor the derived AES-256-GCM key shall ever be transmitted to backend microservices or cloud databases.

### FR-3: Automated Document Ingestion & Verification
- **FR-3.1**: The platform shall accept PDF, JPEG, and PNG formats up to 20MB.
- **FR-3.2**: The `DocumentUploadAgent` shall perform OCR and schema extraction using Vision-Language Models (VLM).
- **FR-3.3**: The system shall extract applicant name, date of birth, address, father/spouse name, and document numbers.
- **FR-3.4**: An integrated face validator shall verify the presence of a clear human face in uploaded photograph files using OpenCV.

### FR-4: Form Data Mapping & Application Synthesis
- **FR-4.1**: The frontend shall guide citizens through a 3-step preparation wizard:
  1. Portal Credentials & CAN Verification.
  2. Residency Period (From Date / To Date).
  3. Document Checklist & Validation Status.
- **FR-4.2**: The system shall package verified extracted fields into a normalized JSON application payload.

### FR-5: Autonomous TNeGA Portal Playwright Automation
- **FR-5.1**: Upon submission, the backend shall launch a headless Chromium instance to interact with `tnesevai.tn.gov.in`.
- **FR-5.2**: The agent shall navigate to the Citizen Login page and input credentials.
- **FR-5.3**: When a portal captcha is encountered, the agent shall screenshot the captcha and stream it to the frontend.
- **FR-5.4**: The agent shall navigate service menus, select *Revenue Department -> REV-101: Residence Certificate*, populate applicant forms, and select address proofs.

### FR-6: Self-Declaration Form Processing
- **FR-6.1**: The automation agent shall automatically trigger generation and download of the official Self-Declaration PDF.
- **FR-6.2**: The system shall stream the declaration file path to the citizen for review/signing.
- **FR-6.3**: The signed document shall be uploaded back to the portal session before final form submission.

### FR-7: Real-Time Payment Facilitation
- **FR-7.1**: The agent shall navigate the BillDesk payment gateway page.
- **FR-7.2**: The agent shall scrape the dynamic UPI QR code and push the base64 image to the citizen's browser in real time.
- **FR-7.3**: When the citizen taps "I have paid", the agent shall monitor gateway confirmation and capture the transaction receipt screenshot and receipt PDF.

### FR-8: Post-Submission Tracking & Certificate Fetching
- **FR-8.1**: The citizen shall be able to track application status using their Application Number.
- **FR-8.2**: The `4thAgent` shall check approval status on the portal and fetch the digitally signed Residence Certificate once approved.

---

## 5. Non-Functional Requirements (NFR)

### NFR-1: Security & Confidentiality
- **End-to-End Encryption**: Encrypted binary storage in Supabase buckets (`documents`).
- **Secret Isolation**: All API tokens (OpenRouter, Groq, Qdrant, Supabase, MessageCentral) must be injected via environment variables; none hardcoded.
- **Ephemeral Automation Data**: Local screenshots and temporary files must be cleaned up post-execution.
- **Credential Hygiene**: Citizen portal passwords must never be logged or persisted in plaintext.

### NFR-2: Real-Time Communication Resilience (Tri-Transport)
- **Primary Transport**: WebSocket (`wss://`) for full-duplex instantaneous communication.
- **Secondary Transport (Shield-Proof)**: Server-Sent Events (SSE) via `text/event-stream` on port 443. Must be 100% immune to ad-blockers, tracker shields (Vivaldi, Brave), and corporate proxies.
- **Tertiary Transport**: HTTP Long-Polling (`/ws/events`) fallback active every 1000ms.
- **Zero-Block Delivery**: Dual-path interactive responses (WebSocket + REST `POST /ws/action`).

### NFR-3: Performance & Latency
- **Assistant Response Time**: Streaming AI responses shall begin rendering within 800ms of user query.
- **OCR Extraction**: Document processing shall complete within 3.5s per document.
- **Automation Execution**: End-to-end portal navigation (up to payment gateway) shall complete within 90 seconds under normal portal latency.
- **Real-Time Push Latency**: SSE event push from automation thread to frontend shall take `< 10ms`.

### NFR-4: Availability & Fault Tolerance
- **Self-Healing Automation**: If a portal session stalls, cleaner utilities (`TNeSevaiSavedAppCleaner`) must purge draft applications to prevent duplicate-application lockouts.
- **Connection Recovery**: The frontend must auto-reconnect within 2 seconds if a network disruption occurs.
- **Service Isolation**: Main backend and Document Upload services run in separate Docker containers to prevent heavy OCR workloads from starving RAG or automation threads.

### NFR-5: Browser & Client Compatibility
- Modern desktop and mobile browsers: Chrome, Firefox, Safari, Edge, Brave, and Vivaldi.
- Responsive dark-mode UI with high-contrast elements for accessibility.

---

## 6. External System Dependencies

```
┌────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL INTEGRATIONS                           │
├───────────────────────┬────────────────────────────────────────────────┤
│ Service               │ Purpose                                        │
├───────────────────────┼────────────────────────────────────────────────┤
│ TNeGA Citizen Portal  │ Target portal (tnesevai.tn.gov.in)             │
│ BillDesk Gateway      │ Payment gateway for ₹60 service fee            │
│ Supabase Cloud        │ PostgreSQL DB + ZK Encrypted Blob Storage      │
│ Qdrant Vector Cloud   │ Multilingual semantic search & RAG embeddings  │
│ OpenRouter / Groq     │ LLM inference (Meta-Llama-3.1-8B-Instruct)     │
│ Message Central       │ SMS OTP dispatch and validation                │
│ AWS EC2 (Ubuntu 24.04)│ Production container host & Nginx gateway       │
│ AWS Amplify           │ Global CDN hosting for React SPA frontend      │
└───────────────────────┴────────────────────────────────────────────────┘
```
