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
import { HeroGeometric } from "./components/ui/shape-landing-hero";
import AnimatedShaderBackground from "./components/ui/animated-shader-background";
import { HoverButton } from "./components/ui/hover-button";
import { AppSidebar } from "./components/AppSidebar";
import { GooeyText } from "./components/ui/gooey-text-morphing";
import { sendMessage, sendMessageStream } from "./api/chatApi";
import "./index.css";

const TYPING_WORDS = ["TNeGA AI Assistant", "e-Sevai Automation"];

function LandingOverlay({ onStart }) {
  const [displayed, setDisplayed] = useState("");
  const [wordIdx, setWordIdx] = useState(0);
  const [charIdx, setCharIdx] = useState(0);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const word = TYPING_WORDS[wordIdx];
    let timeout;
    if (!deleting && charIdx < word.length) {
      timeout = setTimeout(() => setCharIdx(i => i + 1), 80);
    } else if (!deleting && charIdx === word.length) {
      timeout = setTimeout(() => setDeleting(true), 1600);
    } else if (deleting && charIdx > 0) {
      timeout = setTimeout(() => setCharIdx(i => i - 1), 45);
    } else if (deleting && charIdx === 0) {
      setDeleting(false);
      setWordIdx(i => (i + 1) % TYPING_WORDS.length);
    }
    setDisplayed(word.slice(0, charIdx));
    return () => clearTimeout(timeout);
  }, [charIdx, deleting, wordIdx]);

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 10,
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center", gap: "1.75rem",
    }}>
      <div style={{ textAlign: "center" }}>
        <div style={{
          fontSize: "clamp(2rem, 4.5vw, 3.5rem)",
          fontWeight: 800,
          color: "#fff",
          fontFamily: "'Plus Jakarta Sans', sans-serif",
          letterSpacing: "-0.03em",
          lineHeight: 1.2,
          marginBottom: "0.5rem",
          textShadow: "0 2px 24px rgba(0,0,0,0.4)",
        }}>
          {displayed}
          <span style={{
            display: "inline-block",
            width: "3px", height: "1em",
            background: "#ffffff",
            marginLeft: "4px",
            verticalAlign: "middle",
            borderRadius: "2px",
            animation: "blink-cursor 0.75s step-end infinite",
          }} />
        </div>
        <div style={{
          fontSize: "clamp(0.8rem, 1.5vw, 1rem)",
          color: "rgba(255,255,255,0.45)",
          fontWeight: 500,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
        }}>
          Powered by ORCHESTRA
        </div>
      </div>
      <HoverButton onClick={onStart}>Get Started</HoverButton>
    </div>
  );
}

const DEFAULT_WELCOME_MSG = {
  sender: "agent",
  text: "Welcome to the Official TNeGA e-Sevai Assistant. I can guide you step-by-step to obtain a Residence Certificate. How may I help you?",
};

export default function App() {
  const [showLanding, setShowLanding] = useState(true);
  const [messages, setMessages]   = useState([DEFAULT_WELCOME_MSG]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const [chatSessions, setChatSessions] = useState(() => {
    try {
      const saved = localStorage.getItem("tnega_chat_sessions");
      return saved ? JSON.parse(saved) : [];
    } catch (_) { return []; }
  });
  const [showChecklist, setShowChecklist] = useState(false);
  const [waitingForDocReply, setWaitingForDocReply] = useState(false);
  const [isChecklistProceeding, setIsChecklistProceeding] = useState(false);
  const chatEndRef = useRef(null);

  // ── Dark mode — always dark ───────────────────────────────────────────────
  const [dark, setDark] = useState(true);
  
  useEffect(() => {
    document.documentElement.classList.add("dark");
    localStorage.setItem("theme", "dark");
  }, []);
  const [activePage, setActivePage] = useState(() => {
    const hash = window.location.hash.replace("#", "");
    return ["faq", "status", "contact"].includes(hash) ? hash : "home";
  });
  const [pageHistory, setPageHistory] = useState(["home"]);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const navigate = (page) => {
    window.history.pushState({ page }, "", `#${page}`);
    setPageHistory(h => [...h, page]);
    setActivePage(page);
    setDrawerOpen(false);
  };

  const navigateBack = () => {
    window.history.back();
  };

  // Listen to browser back/forward
  useEffect(() => {
    const onPop = (e) => {
      const page = e.state?.page || "home";
      setActivePage(page);
      setPageHistory(h => h.length > 1 ? h.slice(0, -1) : h);
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  // ── Sync current session to chat history in localStorage ──────────────────
  useEffect(() => {
    if (!messages || messages.length <= 1) return;
    const userFirstMsg = messages.find(m => m.sender === "user")?.text;
    const title = userFirstMsg ? (userFirstMsg.length > 25 ? userFirstMsg.slice(0, 25) + "..." : userFirstMsg) : "New Chat";

    setChatSessions(prev => {
      const existingIdx = prev.findIndex(s => s.id === sessionId);
      let updated;
      if (existingIdx >= 0) {
        updated = [...prev];
        updated[existingIdx] = { ...updated[existingIdx], title: updated[existingIdx].title && updated[existingIdx].title !== "New Chat" ? updated[existingIdx].title : title, messages };
      } else {
        updated = [{ id: sessionId, title, messages }, ...prev];
      }
      try { localStorage.setItem("tnega_chat_sessions", JSON.stringify(updated)); } catch (_) {}
      return updated;
    });
  }, [messages, sessionId]);

  const handleNewChat = () => {
    const newId = crypto.randomUUID();
    setSessionId(newId);
    setMessages([DEFAULT_WELCOME_MSG]);
    setShowChecklist(false);
    setActivePage("home");
  };

  const handleSelectChat = (id) => {
    const target = chatSessions.find(s => s.id === id);
    if (target) {
      setSessionId(target.id);
      setMessages(target.messages || [DEFAULT_WELCOME_MSG]);
      setActivePage("home");
    }
  };

  const handleDeleteChat = (id) => {
    const updated = chatSessions.filter(s => s.id !== id);
    setChatSessions(updated);
    try { localStorage.setItem("tnega_chat_sessions", JSON.stringify(updated)); } catch (_) {}
    if (id === sessionId) {
      handleNewChat();
    }
  };

  // ── Init ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    window.history.replaceState({ page: "home" }, "", "#home");
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
    } catch (err) {
      pushBot(`Error: ${err.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSend = async (text) => {
    if (!text.trim()) return;
    pushUser(text);
    const lower = text.toLowerCase().trim();

    // Quick-action intercept — exact keyword matches only
    const quickKey = Object.keys(QUICK_RESPONSES).find(k => lower === k);
    if (quickKey) { pushBot(QUICK_RESPONSES[quickKey]); return; }

    setShowChecklist(false);
    setWaitingForDocReply(false);
    setIsGenerating(true);

    const botMsgId = Date.now().toString();
    setMessages(prev => [...prev, { id: botMsgId, sender: "bot", text: "" }]);

    try {
      const res = await sendMessageStream(
        sessionId,
        text,
        userPhone,
        currentLanguage,
        (token, fullText) => {
          setMessages(prev =>
            prev.map(msg => msg.id === botMsgId ? { ...msg, text: fullText } : msg)
          );
        }
      );

      setMessages(prev =>
        prev.map(msg => msg.id === botMsgId ? { ...msg, text: res.answer || "Please provide more details." } : msg)
      );

      if (res.stage === "SHOW_DOCUMENTS") setShowChecklist(true);
    } catch (err) {
      try {
        const res = await sendMessage(sessionId, text);
        setMessages(prev =>
          prev.map(msg => msg.id === botMsgId ? { ...msg, text: res.answer || "Please provide more details." } : msg)
        );
        if (res.stage === "SHOW_DOCUMENTS") setShowChecklist(true);
      } catch (fallbackErr) {
        setMessages(prev =>
          prev.map(msg => msg.id === botMsgId ? { ...msg, text: `Error: ${fallbackErr.message}` } : msg)
        );
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const handleQuickReply = async (reply) => {
    setWaitingForDocReply(false);
    pushUser(reply);
    setIsGenerating(true);

    const botMsgId = Date.now().toString();
    setMessages(prev => [...prev, { id: botMsgId, sender: "bot", text: "" }]);

    try {
      const res = await sendMessageStream(
        sessionId,
        reply,
        userPhone,
        currentLanguage,
        (token, fullText) => {
          setMessages(prev =>
            prev.map(msg => msg.id === botMsgId ? { ...msg, text: fullText } : msg)
          );
        }
      );

      setMessages(prev =>
        prev.map(msg => msg.id === botMsgId ? { ...msg, text: res.answer || "Please provide more details." } : msg)
      );

      if (res.stage === "SHOW_DOCUMENTS") {
        setShowChecklist(true);
      } else {
        setShowChecklist(false);
      }
    } catch (err) {
      try {
        const res = await sendMessage(sessionId, reply);
        setMessages(prev =>
          prev.map(msg => msg.id === botMsgId ? { ...msg, text: res.answer || "Please provide more details." } : msg)
        );
        if (res.stage === "SHOW_DOCUMENTS") setShowChecklist(true);
      } catch (fallbackErr) {
        setMessages(prev =>
          prev.map(msg => msg.id === botMsgId ? { ...msg, text: `Error: ${fallbackErr.message}` } : msg)
        );
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const handleChecklistExit = () => {
    sendWS({ type: "USER_CLOSE" });
    setShowChecklist(false);
    setFinalPageImage("");
  };

  // ── WebSocket ─────────────────────────────────────────────────────────────
  const wsRef = useRef(null);
  const [automationEvent, setAutomationEvent]       = useState(null);
  const [showSelfDeclaration, setShowSelfDeclaration] = useState(false);
  const [selfDeclarationPath, setSelfDeclarationPath] = useState("");
  const [showDocumentNumber, setShowDocumentNumber]   = useState(false);
  const [automationStatus, setAutomationStatus]       = useState("");
  const [finalPageImage, setFinalPageImage]           = useState("");

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
        if      (data.type === "STATUS_UPDATE")               { setAutomationStatus(data.message); }
        else if (data.type === "STATUS_MESSAGE")              { setAutomationStatus(data.message); }
        else if (data.type === "CAPTCHA_REFRESHED")           { setAutomationEvent(prev => prev ? { ...prev, image: data.image } : prev); }
        else if (data.type === "FINAL_PAGE_SCREENSHOT")       { /* no-op */ }
        else if (data.type === "OPEN_PAYMENT_URL")            { if (data.url) window.open(data.url, "_blank"); }
        else if (data.type === "SELF_DECLARATION_DOWNLOADED") { setSelfDeclarationPath(data.file_path || data.download_path); setShowSelfDeclaration(true); }
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
  const handleAutomationAction      = (v) => { sendWS(v); };
  const handleSelfDeclarationSubmit = (p) => { sendWS({ type: "USER_ANSWER", data: p }); setShowSelfDeclaration(false); };
  const handleSelfDeclarationExit   = ()  => { sendWS({ type: "USER_ANSWER", data: "exit" }); setShowSelfDeclaration(false); };
  const handleDocumentNumberSubmit  = (n) => { sendWS({ type: "USER_ANSWER", data: n }); setShowDocumentNumber(false); };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="app-root">

      {/* ── Sidebar ── */}
      {!showLanding && (
        <AppSidebar
          activePage={activePage}
          onNavigate={navigate}
          drawerOpen={drawerOpen}
          onDrawerClose={() => setDrawerOpen(false)}
          chatSessions={chatSessions}
          currentSessionId={sessionId}
          onNewChat={handleNewChat}
          onSelectChat={handleSelectChat}
          onDeleteChat={handleDeleteChat}
        />
      )}

      {/* ── Main ── */}
      <div className="main-col">
        {/* Animated background — shader on landing, geometric on chat */}
        {showLanding ? <AnimatedShaderBackground /> : <HeroGeometric />}

        {/* ── Landing overlay ── */}
        {showLanding && <LandingOverlay onStart={() => setShowLanding(false)} />}

        {/* ── Mobile Topbar ── */}
        {!showLanding && (<>
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

            {/* Gooey morphing title */}
            <div style={{ display: "flex", justifyContent: "center", paddingBottom: "0.5rem", marginTop: "2rem" }}>
              <GooeyText
                texts={["TNeGA", "ORCHESTRA"]}
                morphTime={1.2}
                cooldownTime={2.5}
                className="gooey-wrap"
                textClassName="gooey-title"
              />
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
                onProceed={() => {}}
                onExit={handleChecklistExit}
                isProceeding={isChecklistProceeding}
                onOpenSocket={openAutomationSocket}
                automationStatus={automationStatus}
              />
            )}

            {/* Typing indicator (only if no active empty bot message) */}
            {isGenerating && !messages.some(m => (m.sender === "bot" || m.sender === "agent" || m.sender === "assistant") && !m.text) && (
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
          showChips={messages.length <= 1 && !showChecklist}
        />
      </>)}
      </>)}
      </div>

      {/* ── Modals ── */}
      <AutomationModal      isOpen={!!automationEvent}    eventData={automationEvent}  onSubmit={handleAutomationSubmit} onAction={handleAutomationAction} />
      <SelfDeclarationModal isOpen={showSelfDeclaration}  downloadPath={selfDeclarationPath} onSubmit={handleSelfDeclarationSubmit} onExit={handleSelfDeclarationExit} />
      <DocumentNumberModal  isOpen={showDocumentNumber}   onSubmit={handleDocumentNumberSubmit} />
    </div>
  );
}
