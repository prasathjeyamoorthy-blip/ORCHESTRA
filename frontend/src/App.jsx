import { useEffect, useState, useRef } from "react";
import { LuBot, LuSparkles, LuShieldCheck,
         LuFileCheck, LuLayoutDashboard, LuPhone, LuBookOpen,
         LuMoon, LuSun, LuMenu, LuX } from "react-icons/lu";
import FaqView        from "./components/FaqView";
import AppStatusView  from "./components/AppStatusView";
import ContactView    from "./components/ContactView";
import ChatBubble      from "./components/ChatBubble";
import ChatInput       from "./components/ChatInput";
import DocumentChecklist    from "./components/DocumentChecklist";
import AutomationModal      from "./components/AutomationModal";
import SelfDeclarationModal from "./components/SelfDeclarationModal";
import DocumentNumberModal  from "./components/DocumentNumberModal";
import { sendMessage } from "./api/chatApi";
import "./index.css";

export default function App() {
  const [messages, setMessages]   = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());
  const [showChecklist, setShowChecklist] = useState(false);
  const [waitingForDocReply, setWaitingForDocReply] = useState(false);
  const [isChecklistProceeding, setIsChecklistProceeding] = useState(false);
  const chatEndRef = useRef(null);

  // ── Dark mode ─────────────────────────────────────────────────────────────
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem("theme");
    if (saved) return saved === "dark";
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });
  const [activePage, setActivePage] = useState("home"); // home | faq | status | contact
  const [drawerOpen, setDrawerOpen] = useState(false);

  const navigate = (page) => { setActivePage(page); setDrawerOpen(false); };

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  // ── Init ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    setMessages([{
      sender: "agent",
      text: "Welcome to the Official TNeGA e-Sevai Assistant. I can guide you step-by-step to obtain a Residence Certificate. How may I help you?",
    }]);
  }, []);

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isGenerating, showChecklist]);

  // Detect "ready to submit" prompt
  useEffect(() => {
    if (!messages.length) return;
    const last = messages[messages.length - 1];
    if (last.sender === "agent" && last.text.toLowerCase().includes("are you ready to submit the documents")) {
      setWaitingForDocReply(true);
    } else {
      setWaitingForDocReply(false);
    }
  }, [messages]);

  // ── Handlers ──────────────────────────────────────────────────────────────
  const pushBot = (text) => setMessages(p => [...p, { sender: "agent", text }]);
  const pushUser = (text) => setMessages(p => [...p, { sender: "user", text }]);

  // ── Hardcoded quick-action responses ──────────────────────────────────────
  const QUICK_RESPONSES = {
    "required documents": `## Documents Required for Residence Certificate

To apply for a Residence Certificate through the TNeGA e-Sevai portal, you must submit the following:

### Identity Proof (any one)
- Aadhaar Card
- Voter ID Card
- Passport
- PAN Card

### Address Proof (any one)
- Aadhaar Card (if address matches)
- Ration Card
- Electricity / Water / Gas Bill (not older than 3 months)
- Bank Passbook with address
- Rental Agreement (notarised)

### Additional Documents
- Recent passport-size photograph
- Self-Declaration Form (downloaded and signed from the portal)
- Applicant's mobile number linked to Aadhaar

---

> **Note:** All documents must be clear, legible scans or photos. PDFs and JPEG/PNG formats are accepted. Maximum file size per document is 2 MB.

Once you have these ready, type **"submit documents"** and I will guide you through the upload process.`,

    "step-by-step guide": `## How to Apply for a Residence Certificate

Follow these steps to complete your application on the TNeGA e-Sevai portal:

### Step 1 — Create / Login to Your Account
Log in using your registered mobile number or Aadhaar-linked credentials on the e-Sevai portal.

### Step 2 — Select the Service
Navigate to **Revenue Department → Certificates → Residence Certificate**.

### Step 3 — Fill the Application Form
Enter your personal details — full name, date of birth, current residential address, and duration of residence in Tamil Nadu.

### Step 4 — Upload Documents
Upload the required identity proof, address proof, and your photograph. Ensure each file is under 2 MB.

### Step 5 — Submit Self-Declaration
Download the self-declaration form, sign it, and re-upload it in the designated field.

### Step 6 — Pay the Fee
A nominal service fee applies. Payment can be made via UPI, Net Banking, or Debit/Credit Card.

### Step 7 — Track Your Application
After submission, note your **Application Reference Number**. Use it to track status under **My Applications**.

### Step 8 — Receive Certificate
Once approved by the Revenue Officer, the certificate will be available for download from your dashboard.

---

> Processing typically takes **3–7 working days**. You will receive an SMS notification on approval.`,

    "track application": `## Track Your Application Status

You can check the current status of your Residence Certificate application in two ways:

### Option 1 — Via This Assistant
Tell me your **Application Reference Number** (e.g., *TN-RC-2025-XXXXXXX*) and I will fetch the latest status for you.

### Option 2 — Via e-Sevai Portal
1. Log in to the e-Sevai portal
2. Click **My Applications** in your dashboard
3. Find your Residence Certificate application in the list

### Application Status Stages

| Status | Meaning |
|---|---|
| **Submitted** | Application received, pending review |
| **Under Scrutiny** | Revenue Officer is verifying documents |
| **Pending Clarification** | Additional info or documents required |
| **Approved** | Certificate is ready for download |
| **Rejected** | Application rejected — reason will be stated |

---

> If your application has been **Pending Clarification** for more than 2 working days, contact your local Taluk Office or call the helpline at **1800-425-1234**.`,

    "general help": `## How Can I Help You?

I am the official ORCHESTRA assistant for the TNeGA e-Sevai Residence Certificate service. Here is what I can do for you:

### Services I Provide
- **Document Guidance** — Tell you exactly which documents to prepare
- **Step-by-Step Application** — Walk you through the entire application process
- **Application Tracking** — Check your application status by reference number
- **Document Upload** — Help you upload and verify your documents directly
- **Form Filling** — Auto-fill your application form using your Aadhaar data

### Common Questions
- *"What documents do I need?"* — Type **"required documents"**
- *"How do I apply?"* — Type **"step-by-step guide"**
- *"Where is my application?"* — Type **"track application"**
- *"I want to upload my documents"* — Type **"submit documents"**

### Need Human Support?
- **Helpline:** 1800-425-1234 (Toll-free, Mon–Sat 9 AM–6 PM)
- **Email:** support@esevai.tn.gov.in

---

Just type your question in plain language and I will assist you right away.`,
  };

  const callBackend = async (text) => {
    setIsGenerating(true);
    try {
      const res = await sendMessage(sessionId, text);
      pushBot(res.answer || "Please provide more details.");
    } catch {
      pushBot("The service is temporarily unavailable. Please try again later.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSend = async (text) => {
    if (!text.trim()) return;
    pushUser(text);
    const lower = text.toLowerCase().trim();

    // Quick-action intercept — no backend call needed
    const quickKey = Object.keys(QUICK_RESPONSES).find(k => lower === k || lower.startsWith(k));
    if (quickKey) { pushBot(QUICK_RESPONSES[quickKey]); return; }

    // Document submission intent — show checklist directly
    const wantsForm = (
      lower.includes("submit") || lower.includes("upload") || lower.includes("attach") ||
      lower.includes("application form") || lower.includes("fill form") || lower.includes("start application") ||
      lower.includes("apply now") || lower.includes("begin") || lower.includes("proceed") ||
      lower.includes("login") || lower.includes("credentials") || lower.includes("start")
    ) && (
      lower.includes("document") || lower.includes("certificate") || lower.includes("file") ||
      lower.includes("form") || lower.includes("application") || lower.includes("apply")
    );

    if (wantsForm) {
      pushBot("Sure! Please fill in your portal credentials and upload your documents below.");
      setShowChecklist(true);
      return;
    }

    setShowChecklist(false);
    setWaitingForDocReply(false);
    setIsGenerating(true);
    try {
      const res = await sendMessage(sessionId, text);
      pushBot(res.answer || "Please provide more details.");
      if (res.stage === "SHOW_DOCUMENTS") setShowChecklist(true);
    } catch {
      pushBot("The service is temporarily unavailable. Please try again later.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleQuickReply = async (reply) => {
    setWaitingForDocReply(false);
    pushUser(reply);
    setIsGenerating(true);
    try {
      const res = await sendMessage(sessionId, reply);
      pushBot(res.answer || "Please provide more details.");
      if (res.stage === "SHOW_DOCUMENTS") {
        setShowChecklist(true);
      } else {
        setShowChecklist(false);
      }
    } catch {
      pushBot("The service is temporarily unavailable. Please try again later.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleChecklistProceed = async () => {
    setIsChecklistProceeding(true);
    await new Promise(r => setTimeout(r, 1200));
    setIsChecklistProceeding(false);
    setShowChecklist(false);
    pushBot("Thank you for submitting the documents.");
  };

  // ── WebSocket ─────────────────────────────────────────────────────────────
  const wsRef = useRef(null);
  const [automationEvent, setAutomationEvent]       = useState(null);
  const [showSelfDeclaration, setShowSelfDeclaration] = useState(false);
  const [selfDeclarationPath, setSelfDeclarationPath] = useState("");
  const [showDocumentNumber, setShowDocumentNumber]   = useState(false);

  const openAutomationSocket = () => new Promise((resolve) => {
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      wsRef.current.close();
    }
    let resolved = false;
    const connect = () => {
      const socket = new WebSocket(`${import.meta.env.VITE_WS_BASE}/ws/automation`);
      let ping;
      socket.onopen = () => {
        ping = setInterval(() => socket.readyState === WebSocket.OPEN && socket.send(JSON.stringify({ type: "PING" })), 5000);
        if (!resolved) { resolved = true; resolve(); }
      };
      socket.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if      (data.type === "SELF_DECLARATION_DOWNLOADED") { setSelfDeclarationPath(data.file_path || data.download_path); setShowSelfDeclaration(true); }
        else if (data.type === "REQUEST_SIGNED_DECLARATION")  { setSelfDeclarationPath(data.download_path); setShowSelfDeclaration(true); }
        else if (data.type === "REQUEST_DOCUMENT_NUMBER")     { setShowDocumentNumber(true); }
        else if (data.type === "AUTOMATION_ERROR")            { setAutomationEvent(null); alert(`Automation error: ${data.message}`); }
        else                                                   { setAutomationEvent(data); }
      };
      socket.onclose = () => { clearInterval(ping); setTimeout(() => wsRef.current === socket && connect(), 1000); };
      socket.onerror = () => { clearInterval(ping); if (!resolved) { resolved = true; resolve(); } };
      wsRef.current = socket;
    };
    connect();
  });

  const sendWS = (payload) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(payload));
  };

  const handleAutomationSubmit      = (v) => { sendWS({ type: "USER_ANSWER", data: v }); setAutomationEvent(null); };
  const handleSelfDeclarationSubmit = (p) => { sendWS({ type: "USER_ANSWER", data: p }); setShowSelfDeclaration(false); };
  const handleSelfDeclarationExit   = ()  => { sendWS({ type: "USER_ANSWER", data: "exit" }); setShowSelfDeclaration(false); };
  const handleDocumentNumberSubmit  = (n) => { sendWS({ type: "USER_ANSWER", data: n }); setShowDocumentNumber(false); };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="app-root">

      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">
            <LuBot size={18} color="#fff" />
          </div>
          <div className="sidebar-logo-text">
            <span className="sidebar-logo-title">TNeGA</span>
            <span className="sidebar-logo-sub">e-Sevai Portal</span>
          </div>
          <button className="theme-toggle" aria-label="Toggle theme" onClick={() => setDark(d => !d)}>
            {dark ? <LuSun size={14} /> : <LuMoon size={14} />}
          </button>
        </div>

        <nav className="sidebar-nav">
          <div className="sidebar-label">Navigation</div>
          <button className={`nav-item${activePage==="home"?" active":""}`}    onClick={() => navigate("home")}><LuLayoutDashboard size={15} /> Home</button>
          <button className={`nav-item${activePage==="faq"?" active":""}`}     onClick={() => navigate("faq")}><LuBookOpen size={15} /> FAQ</button>
          <button className={`nav-item${activePage==="status"?" active":""}`}  onClick={() => navigate("status")}><LuFileCheck size={15} /> Application Status</button>
          <button className={`nav-item${activePage==="contact"?" active":""}`} onClick={() => navigate("contact")}><LuPhone size={15} /> Contact</button>


        </nav>

        <div className="sidebar-footer" />
      </aside>

      {/* ── Mobile Topbar ── */}
      <div className="mobile-topbar">
        <div className="mobile-topbar-left">
          <div className="sidebar-logo-icon" style={{width:'1.75rem',height:'1.75rem',borderRadius:'0.375rem'}}>
            <LuBot size={15} color="#fff" />
          </div>
          <span className="mobile-topbar-title">TNeGA</span>
        </div>
        <div className="mobile-topbar-right">
          <button className="hamburger-btn theme-toggle" aria-label="Toggle theme" onClick={() => setDark(d => !d)}>
            {dark ? <LuSun size={14} /> : <LuMoon size={14} />}
          </button>
          <button className="hamburger-btn" aria-label="Menu" onClick={() => setDrawerOpen(true)}>
            <LuMenu size={16} />
          </button>
        </div>
      </div>

      {/* ── Mobile Drawer ── */}
      <div className={`drawer-overlay${drawerOpen?" open":""}`} onClick={() => setDrawerOpen(false)} />
      <div className={`drawer${drawerOpen?" open":""}`}>
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon"><LuBot size={18} color="#fff" /></div>
          <div className="sidebar-logo-text">
            <span className="sidebar-logo-title">TNeGA</span>
            <span className="sidebar-logo-sub">e-Sevai Portal</span>
          </div>
          <button className="hamburger-btn" aria-label="Close" onClick={() => setDrawerOpen(false)}>
            <LuX size={15} />
          </button>
        </div>
        <nav className="sidebar-nav">
          <div className="sidebar-label">Navigation</div>
          <button className={`nav-item${activePage==="home"?" active":""}`}    onClick={() => navigate("home")}><LuLayoutDashboard size={15} /> Home</button>
          <button className={`nav-item${activePage==="faq"?" active":""}`}     onClick={() => navigate("faq")}><LuBookOpen size={15} /> FAQ</button>
          <button className={`nav-item${activePage==="status"?" active":""}`}  onClick={() => navigate("status")}><LuFileCheck size={15} /> Application Status</button>
          <button className={`nav-item${activePage==="contact"?" active":""}`} onClick={() => navigate("contact")}><LuPhone size={15} /> Contact</button>
        </nav>
      </div>

      {/* ── Main ── */}
      <div className="main-col">

        {activePage !== "home" ? (
          <div className="chat-scroll">
            <div className="chat-inner">
              {activePage === "faq"     && <FaqView />}
              {activePage === "status"  && <AppStatusView />}
              {activePage === "contact" && <ContactView />}
            </div>
          </div>
        ) : (<>
        {/* Scrollable chat area */}
        <div className="chat-scroll">
          <div className="chat-inner">

            {/* Hero card */}
            <div className="hero-card-wrap">
              <div className="hero-card">
                <div className="hero-dot" />
                <div className="hero-card-inner">
                  <div className="hero-avatar">
                    <LuBot size={20} color="#fff" />
                  </div>
                  <div className="hero-info">
                    <div className="hero-title">ORCHESTRA <span>/ TNeGA</span></div>
                    <div className="hero-sub">Residence Certificate · e-Sevai Automation Assistant</div>
                  </div>
                  <div className="hero-meta">
                    <span className="hero-tag"><LuShieldCheck size={11} /> Gov Verified</span>
                    <span className="hero-tag accent"><LuSparkles size={11} /> AI</span>
                  </div>
                </div>
              </div>
            </div>
            {messages.map((msg, i) => (
              <ChatBubble key={i} sender={msg.sender} message={msg.text} />
            ))}

            {/* Quick replies */}
            {waitingForDocReply && (
              <div className="quick-replies fade-up">
                <button className="quick-reply-btn" onClick={() => handleQuickReply("Yes")}>Yes, proceed</button>
                <button className="quick-reply-btn" onClick={() => handleQuickReply("No")}>Not right now</button>
              </div>
            )}

            {/* Document checklist */}
            {showChecklist && (
              <DocumentChecklist
                onProceed={handleChecklistProceed}
                onExit={() => setShowChecklist(false)}
                isProceeding={isChecklistProceeding}
                onOpenSocket={openAutomationSocket}
              />
            )}

            {/* Typing indicator */}
            {isGenerating && (
              <div className="typing-row fade-up">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </div>
            )}

            <div ref={chatEndRef} />
          </div>
        </div>

        {/* Input bar */}
        <ChatInput
          onSend={handleSend}
          disabled={isGenerating || showChecklist}
          isGenerating={isGenerating}
          onStop={() => setIsGenerating(false)}
        />
      </>)}
      </div>

      {/* ── Modals ── */}
      <AutomationModal      isOpen={!!automationEvent}    eventData={automationEvent}  onSubmit={handleAutomationSubmit} />
      <SelfDeclarationModal isOpen={showSelfDeclaration}  downloadPath={selfDeclarationPath} onSubmit={handleSelfDeclarationSubmit} onExit={handleSelfDeclarationExit} />
      <DocumentNumberModal  isOpen={showDocumentNumber}   onSubmit={handleDocumentNumberSubmit} />
    </div>
  );
}
