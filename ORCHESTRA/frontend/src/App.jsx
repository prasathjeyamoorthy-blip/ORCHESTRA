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
import OtpModal             from "./components/OtpModal";
import { HeroGeometric } from "./components/ui/shape-landing-hero";
import AnimatedShaderBackground from "./components/ui/animated-shader-background";
import { HoverButton } from "./components/ui/hover-button";
import { AppSidebar } from "./components/AppSidebar";
import { GooeyText } from "./components/ui/gooey-text-morphing";
import { sendMessage, sendMessageStream } from "./api/chatApi";
import "./index.css";

const TYPING_WORDS = [
  "Residence Certificate Portal",
  "e-Sevai Digital Desk",
  "இருப்பிடச் சான்றிதழ் இணையச் சேவை",
  "Automated Citizen Verification",
];

function LandingOverlay({ onStart }) {
  const [wordIdx, setWordIdx] = useState(0);
  const [charIdx, setCharIdx] = useState(0);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const word = TYPING_WORDS[wordIdx];
    let timeout;
    if (!deleting && charIdx < word.length) {
      timeout = setTimeout(() => setCharIdx(i => i + 1), 70);
    } else if (!deleting && charIdx === word.length) {
      timeout = setTimeout(() => setDeleting(true), 1800);
    } else if (deleting && charIdx > 0) {
      timeout = setTimeout(() => setCharIdx(i => i - 1), 40);
    } else if (deleting && charIdx === 0) {
      timeout = setTimeout(() => {
        setDeleting(false);
        setWordIdx(i => (i + 1) % TYPING_WORDS.length);
      }, 200);
    }
    return () => clearTimeout(timeout);
  }, [charIdx, deleting, wordIdx]);

  const displayed = TYPING_WORDS[wordIdx].slice(0, charIdx);

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 10,
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center", gap: "2rem",
      padding: "1.5rem",
      pointerEvents: "auto",
    }}>
      {/* Tamil Nadu Govt Seal & Civic Header Badge */}
      <div style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.75rem",
        padding: "0.5rem 1.15rem",
        borderRadius: "9999px",
        background: "rgba(255,255,255,0.08)",
        backdropFilter: "blur(16px)",
        border: "1px solid rgba(255,255,255,0.18)",
        boxShadow: "0 4px 20px rgba(0,0,0,0.3)",
      }}>
        <div style={{
          width: "1.75rem",
          height: "1.75rem",
          borderRadius: "0.375rem",
          overflow: "hidden",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}>
          <img
            src="/tnega-logo.png"
            alt="Tamil Nadu Government Seal"
            style={{ width: "100%", height: "100%", objectFit: "contain" }}
            onError={(e) => { e.currentTarget.style.display = "none"; }}
          />
        </div>
        <div style={{ display: "flex", flexDirection: "column", textAlign: "left" }}>
          <span style={{ fontSize: "0.75rem", fontWeight: 800, color: "#ffffff", letterSpacing: "0.04em", textTransform: "uppercase" }}>
            தமிழ்நாடு அரசு • Government of Tamil Nadu
          </span>
          <span style={{ fontSize: "0.625rem", color: "rgba(255,255,255,0.6)", fontWeight: 500 }}>
            Tamil Nadu e-Governance Agency (TNeGA) • Revenue Department
          </span>
        </div>
      </div>

      {/* Main Title & Typewriter */}
      <div style={{ textAlign: "center", maxWidth: "48rem" }}>
        <h1 style={{
          fontSize: "clamp(2rem, 5vw, 3.75rem)",
          fontWeight: 800,
          color: "#fff",
          fontFamily: "'Plus Jakarta Sans', sans-serif",
          letterSpacing: "-0.03em",
          lineHeight: 1.15,
          marginBottom: "1rem",
          textShadow: "0 4px 32px rgba(0,0,0,0.6)",
        }}>
          {displayed}
          <span style={{
            display: "inline-block",
            width: "3px", height: "0.95em",
            background: "#38bdf8",
            marginLeft: "6px",
            verticalAlign: "middle",
            borderRadius: "2px",
            animation: "blink-cursor 0.75s step-end infinite",
          }} />
        </h1>
        <p style={{
          fontSize: "clamp(0.9rem, 1.8vw, 1.125rem)",
          color: "rgba(255,255,255,0.7)",
          fontWeight: 400,
          lineHeight: 1.6,
          maxWidth: "38rem",
          margin: "0 auto",
          textShadow: "0 2px 12px rgba(0,0,0,0.5)",
        }}>
          Official digital citizen assistance for applying, validating, and obtaining your
          official <strong>Residence Certificate (இருப்பிடச் சான்றிதழ்)</strong> through automated e-Sevai processing.
        </p>
      </div>

      {/* Trust Feature Badges */}
      <div style={{
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        gap: "0.75rem",
        maxWidth: "42rem",
      }}>
        <div style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.4rem",
          padding: "0.35rem 0.85rem",
          borderRadius: "9999px",
          background: "rgba(0,0,0,0.4)",
          backdropFilter: "blur(12px)",
          border: "1px solid rgba(255,255,255,0.12)",
          fontSize: "0.78125rem",
          color: "rgba(255,255,255,0.85)",
          fontWeight: 500,
        }}>
          <span style={{ color: "#34d399" }}>✓</span> Instant OCR Document Extraction
        </div>
        <div style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.4rem",
          padding: "0.35rem 0.85rem",
          borderRadius: "9999px",
          background: "rgba(0,0,0,0.4)",
          backdropFilter: "blur(12px)",
          border: "1px solid rgba(255,255,255,0.12)",
          fontSize: "0.78125rem",
          color: "rgba(255,255,255,0.85)",
          fontWeight: 500,
        }}>
          <span style={{ color: "#38bdf8" }}>🔒</span> Zero-Knowledge Client Encryption
        </div>
        <div style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.4rem",
          padding: "0.35rem 0.85rem",
          borderRadius: "9999px",
          background: "rgba(0,0,0,0.4)",
          backdropFilter: "blur(12px)",
          border: "1px solid rgba(255,255,255,0.12)",
          fontSize: "0.78125rem",
          color: "rgba(255,255,255,0.85)",
          fontWeight: 500,
        }}>
          <span style={{ color: "#fbbf24" }}>🏛️</span> Revenue Department Standards
        </div>
      </div>

      {/* Button using HoverButton */}
      <HoverButton onClick={onStart}>
        Enter Citizen Portal →
      </HoverButton>
    </div>
  );
}

const DEFAULT_WELCOME_MSG = {
  sender: "agent",
  text: `### Vanakkam! Welcome to the Official TNeGA e-Sevai Digital Desk

I am your citizen assistance guide for obtaining a **Residence Certificate (இருப்பிடச் சான்றிதழ்)** issued by the **Revenue & Disaster Management Department, Government of Tamil Nadu**.

**How I can assist you today:**
- 📋 **Check Required Documents** (Aadhaar, Ration Card, Address Proof, Photo)
- 📝 **Verify Eligibility & Application Requirements**
- ⚡ **Auto-Extract & Validate Documents** with Instant OCR
- 🚀 **Step-by-Step Guidance** through the e-Sevai Portal submission

*Select a quick action below or type your query to begin.*`,
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
  const [showOtpModal, setShowOtpModal]   = useState(false);
  const [userPhone, setUserPhone]         = useState(() => sessionStorage.getItem("user_phone") || "");
  const [currentLanguage, _setCurrentLanguage] = useState("en");
  const [waitingForDocReply, setWaitingForDocReply] = useState(false);
  const [isChecklistProceeding, _setIsChecklistProceeding] = useState(false);
  const [showClearModal, setShowClearModal] = useState(false);
  const [isClearingData, setIsClearingData] = useState(false);
  const chatEndRef = useRef(null);

  // ── Dark mode — always dark ───────────────────────────────────────────────
  const [dark, setDark] = useState(true);
  
  useEffect(() => {
    if (dark) {
      document.documentElement.classList.add("dark");
      document.documentElement.classList.remove("light");
    } else {
      document.documentElement.classList.remove("dark");
      document.documentElement.classList.add("light");
    }
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);
  const [activePage, setActivePage] = useState(() => {
    const hash = window.location.hash.replace("#", "");
    return ["faq", "status", "contact"].includes(hash) ? hash : "home";
  });
  const [_pageHistory, setPageHistory] = useState(["home"]);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const navigate = (page) => {
    window.history.pushState({ page }, "", `#${page}`);
    setPageHistory(h => [...h, page]);
    setActivePage(page);
    setDrawerOpen(false);
  };

  const _navigateBack = () => {
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

  const checkShouldShowChecklist = (res, userText, botAnswer) => {
    if (res?.stage === "SHOW_DOCUMENTS") return true;

    const u = (userText || "").toLowerCase().trim();
    const b = (botAnswer || "").toLowerCase().trim();

    const userPhrases = [
      "yeah we can go", "we can go", "let's go", "lets go", "go ahead", "ready", "ready to apply",
      "submit documents", "upload documents", "apply now", "start application", "yes proceed", "proceed",
      "submit application", "start process", "begin application", "i want to apply", "yes", "yeah"
    ];
    if (userPhrases.some(p => u.includes(p))) return true;

    const botPhrases = [
      "provide the required documents", "proceed with submitting", "submit your residence certificate",
      "upload your documents", "ready to begin", "upload the required documents", "document upload checklist"
    ];
    if (botPhrases.some(p => b.includes(p))) return true;

    return false;
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

      const finalAnswer = res.answer || "";
      setMessages(prev =>
        prev.map(msg => msg.id === botMsgId ? { ...msg, text: finalAnswer || "Please provide more details." } : msg)
      );

      if (checkShouldShowChecklist(res, text, finalAnswer)) setShowChecklist(true);
    } catch (_err) {
      try {
        const res = await sendMessage(sessionId, text);
        const finalAnswer = res.answer || "";
        setMessages(prev =>
          prev.map(msg => msg.id === botMsgId ? { ...msg, text: finalAnswer || "Please provide more details." } : msg)
        );
        if (checkShouldShowChecklist(res, text, finalAnswer)) setShowChecklist(true);
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

      const finalAnswer = res.answer || "";
      setMessages(prev =>
        prev.map(msg => msg.id === botMsgId ? { ...msg, text: finalAnswer || "Please provide more details." } : msg)
      );

      if (checkShouldShowChecklist(res, reply, finalAnswer)) {
        setShowChecklist(true);
      }
    } catch (_err) {
      try {
        const res = await sendMessage(sessionId, reply);
        const finalAnswer = res.answer || "";
        setMessages(prev =>
          prev.map(msg => msg.id === botMsgId ? { ...msg, text: finalAnswer || "Please provide more details." } : msg)
        );
        if (checkShouldShowChecklist(res, reply, finalAnswer)) setShowChecklist(true);
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
  };

  // ── Apply Now — open checklist directly ──────────────────────────────────
  const handleApplyNow = () => {
    navigate("home");
    setShowChecklist(true);
  };

  // ── Clear My Data — delete all user data from backend + local state ───────
  const handleClearDataConfirm = async () => {
    setIsClearingData(true);
    try {
      const phone = userPhone || sessionStorage.getItem("user_phone") || "";
      const apiBase = import.meta.env.VITE_API_BASE;
      const docBase = import.meta.env.VITE_DOC_API_BASE;

      const requests = [
        fetch(`${docBase}/clear-cache`, { method: "POST" }).catch(() => {}),
      ];
      if (phone) {
        requests.push(
          fetch(`${apiBase}/api/chat-history?phone_number=${encodeURIComponent(phone)}`, { method: "DELETE" }).catch(() => {})
        );
      }
      await Promise.all(requests);

      // Clear local state
      setChatSessions([]);
      localStorage.removeItem("tnega_chat_sessions");
      setMessages([DEFAULT_WELCOME_MSG]);
      setShowChecklist(false);
      setShowClearModal(false);
    } catch (err) {
      alert("Error clearing data: " + (err.message || "Unknown error"));
    } finally {
      setIsClearingData(false);
    }
  };

  // ── WebSocket ─────────────────────────────────────────────────────────────
  const wsRef = useRef(null);
  const [automationEvent, setAutomationEvent]       = useState(null);
  const [showSelfDeclaration, setShowSelfDeclaration] = useState(false);
  const [selfDeclarationPath, setSelfDeclarationPath] = useState("");
  const [showDocumentNumber, setShowDocumentNumber]   = useState(false);
  const [automationStatus, setAutomationStatus]       = useState("");

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
        else if (data.type === "OPEN_PAYMENT_URL")            {
          if (data.url) {
            window.open(data.url, "_blank");
            setMessages(prev => [
              ...prev,
              {
                sender: "agent",
                text: `💳 **Payment Gateway is Ready!**\n\nIf the payment tab did not open automatically, please click below:\n\n👉 [**Proceed to Payment Gateway**](${data.url})`
              }
            ]);
          }
        }
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
          onOpenOtpModal={() => setShowOtpModal(true)}
          userPhone={userPhone}
          onApplyNow={handleApplyNow}
          onClearData={() => setShowClearModal(true)}
        />
      )}

      {/* ── Main ── */}
      <div className="main-col">
        {/* Animated background — shader on landing, geometric on chat */}
        {showLanding ? <AnimatedShaderBackground /> : <HeroGeometric />}

        {/* ── Landing overlay ── */}
        {showLanding && <LandingOverlay onStart={() => {
          setShowLanding(false);
          if (!sessionStorage.getItem("user_phone")) {
            setShowOtpModal(true);
          }
        }} />}

        {/* ── Mobile Topbar ── */}
        {!showLanding && (<>
        <div className="mobile-topbar">
          <div className="mobile-topbar-left">
            <div className="sidebar-logo-icon" style={{ width: '1.875rem', height: '1.875rem', borderRadius: '0.4rem', overflow: 'hidden', background: 'rgba(255,255,255,0.08)', padding: '0.15rem' }}>
              <img src="/tnega-logo.png" alt="TNeGA Seal" style={{ width: '100%', height: '100%', objectFit: 'contain' }} onError={(e) => { e.currentTarget.style.display = "none"; }} />
            </div>
            <span className="mobile-topbar-title" style={{ fontSize: '0.9375rem', fontWeight: 700 }}>TNeGA e-Sevai</span>
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

            {/* Official Civic Service Header */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.6rem", marginTop: "1.75rem", marginBottom: "1.25rem", textAlign: "center" }}>
              <div style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.35rem 0.95rem",
                borderRadius: "9999px",
                background: "rgba(255,255,255,0.06)",
                border: "1px solid rgba(255,255,255,0.12)",
                backdropFilter: "blur(14px)",
                fontSize: "0.75rem",
                fontWeight: 600,
                color: "#e2e8f0",
                boxShadow: "0 2px 8px rgba(0,0,0,0.25)"
              }}>
                <img src="/tnega-logo.png" alt="TNeGA Seal" style={{ width: "16px", height: "16px", objectFit: "contain" }} onError={(e) => { e.currentTarget.style.display = "none"; }} />
                <span>தமிழ்நாடு அரசு • Revenue & Disaster Management Dept</span>
                <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#10b981", boxShadow: "0 0 6px #10b981", display: "inline-block" }} />
              </div>

              <GooeyText
                texts={["e-Sevai Portal", "Residence Certificate", "இருப்பிடச் சான்றிதழ்", "Citizen Desk"]}
                morphTime={1.2}
                cooldownTime={2.5}
                className="gooey-wrap"
                textClassName="gooey-title"
              />

              <div style={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)", fontWeight: 500, letterSpacing: "0.02em" }}>
                Official Automated Verification & Application Processing
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
                onProceed={() => {}}
                onExit={handleChecklistExit}
                isProceeding={isChecklistProceeding}
                onOpenSocket={openAutomationSocket}
                automationStatus={automationStatus}
                onResetAutomationStatus={() => setAutomationStatus("")}
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

      {/* ── Clear My Data Confirmation Modal ── */}
      {showClearModal && (
        <div style={{ position: "fixed", inset: 0, zIndex: 999, background: "rgba(0,0,0,0.7)", backdropFilter: "blur(8px)", display: "flex", alignItems: "center", justifyContent: "center", padding: "1rem" }}>
          <div style={{ background: "#1a1a1a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "1.25rem", padding: "2rem", maxWidth: "22rem", width: "100%", textAlign: "center", boxShadow: "0 24px 64px rgba(0,0,0,0.5)" }}>
            <div style={{ width: "3.5rem", height: "3.5rem", borderRadius: "50%", background: "rgba(239,68,68,0.15)", border: "1px solid rgba(239,68,68,0.3)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 1.25rem" }}>
              <span style={{ fontSize: "1.5rem" }}>🗑</span>
            </div>
            <h3 style={{ color: "#fff", fontWeight: 700, fontSize: "1.1rem", marginBottom: "0.5rem" }}>Clear All My Data?</h3>
            <p style={{ color: "rgba(255,255,255,0.5)", fontSize: "0.875rem", lineHeight: 1.6, marginBottom: "1.5rem" }}>
              This permanently deletes your chat history, uploaded documents, and saved application data. Your account stays active.
            </p>
            <div style={{ display: "flex", gap: "0.75rem" }}>
              <button
                onClick={() => setShowClearModal(false)}
                disabled={isClearingData}
                style={{ flex: 1, padding: "0.7rem", borderRadius: "9999px", background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.12)", color: "rgba(255,255,255,0.7)", fontWeight: 600, fontSize: "0.875rem", cursor: "pointer" }}
              >
                Cancel
              </button>
              <button
                onClick={handleClearDataConfirm}
                disabled={isClearingData}
                style={{ flex: 1, padding: "0.7rem", borderRadius: "9999px", background: isClearingData ? "rgba(239,68,68,0.4)" : "linear-gradient(135deg,#ef4444,#dc2626)", border: "none", color: "#fff", fontWeight: 700, fontSize: "0.875rem", cursor: isClearingData ? "not-allowed" : "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "0.5rem" }}
              >
                {isClearingData ? <><span style={{ width: "14px", height: "14px", border: "2px solid rgba(255,255,255,0.4)", borderTopColor: "#fff", borderRadius: "50%", display: "inline-block", animation: "spin 0.8s linear infinite" }} /> Deleting…</> : "Yes, Delete"}
              </button>
            </div>
          </div>
        </div>
      )}

      <OtpModal
        isOpen={showOtpModal}
        onClose={() => setShowOtpModal(false)}
        onSuccess={(phone) => {
          setShowOtpModal(false);
          setUserPhone(phone);
          sessionStorage.setItem("user_phone", phone);
        }}
      />
    </div>
  );
}
