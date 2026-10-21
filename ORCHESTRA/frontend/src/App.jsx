import { useEffect, useState, useRef, useCallback } from "react";
import { LuBot, LuShieldCheck,
         LuFileCheck, LuLayoutDashboard, LuPhone, LuBookOpen,
         LuMoon, LuSun, LuMenu, LuX, LuCircleCheck, LuCircleCheckBig, LuQrCode, LuTrash2,
         LuDownload } from "react-icons/lu";
import FaqView        from "./components/FaqView";
import AppStatusView  from "./components/AppStatusView";
import ContactView    from "./components/ContactView";
import ReceiptView    from "./components/ReceiptView";
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

const TYPING_WORDS = ["TNeGA AI Assistant", "e-Sevai Automation"];

function LandingOverlay({ onStart }) {
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
      alignItems: "center", justifyContent: "center", gap: "1.75rem",
      padding: "1rem", boxSizing: "border-box"
    }}>
      <div style={{ textAlign: "center", maxWidth: "90vw" }}>
        <div style={{
          fontSize: "clamp(1.75rem, 5vw, 3.5rem)",
          fontWeight: 800,
          color: "#fff",
          fontFamily: "'Plus Jakarta Sans', sans-serif",
          letterSpacing: "-0.03em",
          lineHeight: 1.2,
          marginBottom: "0.5rem",
          textShadow: "0 2px 24px rgba(0,0,0,0.4)",
          wordBreak: "break-word"
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

// ── TrackForm ─ inline certificate retrieval form (Application Number only) ──────
function TrackForm({ onSubmit }) {
  const [appNo, setAppNo] = useState("");
  const valid = appNo.trim().length > 0;
  return (
    <div className="fade-up" style={{
      maxWidth: "420px", width: "100%", background: "rgba(255,255,255,0.04)",
      border: "1px solid rgba(255,255,255,0.1)", borderRadius: "1rem",
      padding: "1.25rem", boxSizing: "border-box",
    }}>
      <p style={{ color: "#fff", fontWeight: 600, fontSize: "0.9rem", marginBottom: "0.75rem", lineHeight: 1.4 }}>
        Please enter your Application Number to fetch your certificate:
      </p>
      {/* Number input */}
      <input
        type="text"
        value={appNo}
        onChange={e => setAppNo(e.target.value)}
        placeholder="Enter Application Number (e.g. TN-7202401230101)"
        onKeyDown={e => e.key === "Enter" && valid && onSubmit(appNo.trim())}
        style={{
          width: "100%", padding: "0.65rem 0.875rem",
          borderRadius: "0.6rem", border: "1px solid rgba(255,255,255,0.15)",
          background: "rgba(255,255,255,0.06)", color: "#fff",
          fontSize: "0.9rem", outline: "none", boxSizing: "border-box",
          marginBottom: "0.75rem",
        }}
        autoFocus
      />
      {/* Submit button */}
      <button
        disabled={!valid}
        onClick={() => valid && onSubmit(appNo.trim())}
        style={{
          width: "100%", padding: "0.65rem", borderRadius: "0.6rem",
          border: "none",
          background: valid ? "linear-gradient(135deg,#a855f7,#6366f1)" : "rgba(255,255,255,0.08)",
          color: valid ? "#fff" : "rgba(255,255,255,0.3)",
          fontWeight: 600, fontSize: "0.9rem",
          cursor: valid ? "pointer" : "not-allowed",
          transition: "background 0.2s",
        }}
      >
        Fetch Certificate
      </button>
    </div>
  );
}

const getWsBase = () => {
  let wsBase = import.meta.env.VITE_WS_BASE;
  if (!wsBase) {
    const apiBase = import.meta.env.VITE_API_BASE;
    if (apiBase) {
      wsBase = apiBase.replace(/^http/, "ws");
    } else {
      const isHttps = typeof window !== "undefined" && window.location.protocol === "https:";
      wsBase = `${isHttps ? "wss" : "ws"}://${typeof window !== "undefined" ? window.location.host : "localhost:8001"}`;
    }
  }
  return wsBase.replace(/\/$/, "");
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
  const [dark] = useState(true);
  
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
    return ["faq", "contact", "receipt"].includes(hash) ? hash : "home";
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

> **Note:** All documents must be clear, legible official digital documents. Only PDF format is accepted (max 5 MB per document) to avoid extraction errors and prevent vision hallucination.

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

    // ── Receipt download intercept ──
    const receiptPhrases = [
      "download receipt", "my receipt", "get receipt", "payment receipt",
      "where is my receipt", "receipt download", "download my receipt", "get my receipt"
    ];
    if (receiptPhrases.some(kw => lower.includes(kw))) {
      setProcessCompleted(true);
      try { localStorage.setItem("tnega_process_completed", "true"); } catch (_) {}
      setMessages(prev => [...prev, { sender: "agent", text: "", type: "receipt_download" }]);
      return;
    }

    // ── Certificate status / download intercept ──
    // Fires independently of payment. Only application number is asked to fetch and give the certificate.
    const certPhrases = [
      "download my certificate", "download certificate", "get my certificate",
      "download cert", "my cert", "track my cert", "track certificate",
      "certificate status", "get certificate", "want my certificate",
      "status of my certificate", "status of my cert",
      "know the status", "check the status", "check my cert",
      "where is my certificate", "where is my cert",
      "certificate ready", "is my certificate ready",
      // residence certificate variants
      "download my residence certificate", "download residence certificate",
      "get my residence certificate", "want my residence certificate",
      "my residence certificate", "residence certificate status",
      "status of my residence certificate", "track my residence certificate",
      "fetch certificate", "fetch my certificate", "fetch residence certificate",
    ];
    const hasCertIntent = certPhrases.some(kw => lower.includes(kw));

    // Check if user already provided an application number directly in their message
    const appNoMatch = text.match(/\b(TN[-_]?[0-9A-Za-z]+|[0-9]{6,})\b/i);
    const extractedAppNo = appNoMatch ? appNoMatch[0] : null;

    if (hasCertIntent) {
      if (extractedAppNo) {
        // Application number already provided in message -> retrieve directly
        setMessages(prev => [...prev, { sender: "agent", text: "", type: "cert_fetching", appNo: extractedAppNo }]);
        setTimeout(() => {
          setMessages(prev => prev.map(m => m.type === "cert_fetching" && m.appNo === extractedAppNo ? { sender: "agent", text: "", type: "cert_download", appNo: extractedAppNo } : m));
        }, 3500);
      } else {
        // Only ask for application number
        setMessages(prev => [...prev, { sender: "agent", text: "", type: "track_form" }]);
      }
      return;
    }

    // If an inline track_form is active and user typed the application number in the chat input
    const hasActiveTrackForm = messages.some(m => m.type === "track_form");
    if (hasActiveTrackForm && (extractedAppNo || text.trim().length >= 4)) {
      const appNoToUse = extractedAppNo || text.trim();
      setMessages(prev => prev.map(m => m.type === "track_form" ? { sender: "agent", text: "", type: "cert_fetching", appNo: appNoToUse } : m));
      setTimeout(() => {
        setMessages(prev => prev.map(m => m.type === "cert_fetching" ? { sender: "agent", text: "", type: "cert_download", appNo: appNoToUse } : m));
      }, 3500);
      return;
    }

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
    setAutomationStatus("");
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
      setProcessCompleted(false);
      try { localStorage.removeItem("tnega_process_completed"); } catch (_) {}
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
  const [paymentQr, setPaymentQr]                     = useState(null); // { qr_image, payment_url }
  const [paymentSuccess, setPaymentSuccess]           = useState(null);
  const [automationStatus, setAutomationStatus]       = useState("");
  // ── ADDED: post-payment states ─────────────────────────────────────────────
  const [gettingReceipt, setGettingReceipt]           = useState(false);  // loading spinner after "I have paid"
  const [processCompleted, setProcessCompleted]       = useState(() => {
    try {
      return localStorage.getItem("tnega_process_completed") === "true";
    } catch (_) { return false; }
  });
  const hasCompletedProcess = processCompleted || messages.some(m => m.type === "receipt_download" || m.type === "cert_download");

  const openAutomationSocket = useCallback(() => new Promise((resolve, reject) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      resolve();
      return;
    }
    if (wsRef.current && wsRef.current.readyState === WebSocket.CONNECTING) {
      const start = Date.now();
      const check = setInterval(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          clearInterval(check);
          resolve();
        } else if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED || Date.now() - start > 8000) {
          clearInterval(check);
          if (wsRef.current?.readyState === WebSocket.OPEN) resolve();
          else reject(new Error("WebSocket connection timeout"));
        }
      }, 150);
      return;
    }
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      try {
        wsRef.current.onclose = null;
        wsRef.current.onerror = null;
        wsRef.current.close();
      } catch (_) {}
    }
    let settled = false;
    const connect = () => {
      const wsBase = getWsBase();
      const socket = new WebSocket(`${wsBase}/ws/automation`);
      let ping;
      socket.onopen = () => {
        console.log("[WebSocket] Automation socket connected to:", wsBase);
        ping = setInterval(() => socket.readyState === WebSocket.OPEN && socket.send(JSON.stringify({ type: "PING" })), 5000);
        if (!settled) { settled = true; resolve(); }
      };
      socket.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if      (data.type === "STATUS_UPDATE")               { setAutomationStatus(data.message); }
          else if (data.type === "STATUS_MESSAGE")              { setAutomationStatus(data.message); }
          else if (data.type === "CAPTCHA_REFRESHED")           { setAutomationEvent(prev => prev ? { ...prev, image: data.image } : prev); }
          else if (data.type === "OPEN_PAYMENT_URL") {
            if (data.url) { window.open(data.url, "_blank"); } /* chat message suppressed intentionally */
          }
          else if (data.type === "SELF_DECLARATION_DOWNLOADED") { setSelfDeclarationPath(data.file_path || data.download_path); setShowSelfDeclaration(true); }
          else if (data.type === "REQUEST_SIGNED_DECLARATION")  { setSelfDeclarationPath(data.download_path); setShowSelfDeclaration(true); }
          else if (data.type === "REQUEST_DOCUMENT_NUMBER")     { setShowDocumentNumber(true); }
          else if (data.type === "PAYMENT_QR")                  { setPaymentQr({ qr_image: data.qr_image, payment_url: data.payment_url }); setPaymentSuccess(null); }
          else if (data.type === "PAYMENT_SUCCESS")             { setPaymentSuccess({ screenshot: data.screenshot, url: data.url }); setPaymentQr(null); setGettingReceipt(false); setIsGenerating(false); setAutomationEvent(null); setProcessCompleted(true); try { localStorage.setItem("tnega_process_completed", "true"); } catch (_) {} setMessages(prev => [...prev, { sender: "agent", text: "", type: "receipt_download" }]); }
          else if (data.type === "CLEANER_STATUS")              { window.dispatchEvent(new CustomEvent("cleaner_status", { detail: data.message })); }
          else if (data.type === "CLEANER_ERROR")               {
            window.dispatchEvent(new CustomEvent("cleaner_error", { detail: data.message }));
            setAutomationEvent(null);
          }
          else if (data.type === "SAVED_APP_DELETED" || data.type === "CLEANER_DONE") {
            window.dispatchEvent(new CustomEvent("cleaner_done", { detail: data.message || "Saved application deleted successfully!" }));
            setAutomationEvent(null);
          }
          else if (data.type === "AUTOMATION_ERROR")            {
            window.dispatchEvent(new CustomEvent("cleaner_error", { detail: data.message }));
            setAutomationEvent(null);
            alert(`Automation error: ${data.message}`);
          }
          else                                                   { setAutomationEvent(data); }
        } catch (err) {
          console.error("[WebSocket] Parse error:", err);
        }
      };
      socket.onclose = () => {
        clearInterval(ping);
        setTimeout(() => {
          if (wsRef.current === socket) {
            connect();
          }
        }, 2000);
      };
      socket.onerror = (err) => {
        clearInterval(ping);
        console.error("[WebSocket] Socket error:", err);
        if (!settled) { settled = true; reject(new Error("WebSocket connection failed")); }
      };
      wsRef.current = socket;
    };
    connect();
  }), []);

  // Proactively connect automation WebSocket when checklist is opened
  useEffect(() => {
    if (showChecklist) {
      openAutomationSocket().catch(err => console.warn("[WebSocket] Checklist open auto-connect:", err));
    }
  }, [showChecklist, openAutomationSocket]);

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
          hasCompletedProcess={hasCompletedProcess}
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
            <div className="sidebar-logo-icon" style={{width:'1.75rem',height:'1.75rem',borderRadius:'0.375rem'}}>
              <LuBot size={15} color="#fff" />
            </div>
            <span className="mobile-topbar-title">TNeGA</span>
          </div>
          <div className="mobile-topbar-right">
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
              {activePage === "receipt" && <ReceiptView currentLanguage={currentLanguage} />}
            </div>
          </div>
        ) : (<>
        {/* Scrollable chat area */}
        <div className="chat-scroll">
          <div className="chat-inner">

            {/* Gooey morphing title */}
            <div style={{ display: "flex", justifyContent: "center", paddingBottom: "0.25rem", marginTop: "0.25rem" }}>
              <GooeyText
                texts={["TNeGA", "ORCHESTRA"]}
                morphTime={1.2}
                cooldownTime={2.5}
                className="gooey-wrap"
                textClassName="gooey-title"
              />
            </div>
            {messages.map((msg, i) =>
              msg.type === "receipt_download" ? (
                <div key={i} className="fade-up" style={{ maxWidth: "420px", width: "100%", background: "rgba(99,102,241,0.12)", border: "1px solid rgba(99,102,241,0.3)", borderRadius: "1rem", padding: "1.25rem", boxSizing: "border-box" }}>
                  <p style={{ color: "#fff", fontWeight: 600, marginBottom: "0.35rem", fontSize: "0.95rem" }}>Payment complete. Your receipt is ready.</p>
                  <p style={{ color: "rgba(255,255,255,0.7)", fontSize: "0.82rem", marginBottom: "0.85rem", lineHeight: 1.5 }}>
                    You can also access your receipt and fetch your certificate anytime from the <strong>Receipt & Certificate</strong> section in the sidebar.
                  </p>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                    <a href="/receipt.pdf" download="Receipt.pdf" style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem", padding: "0.6rem 1.15rem", borderRadius: "0.5rem", background: "linear-gradient(135deg,#6366f1,#8b5cf6)", color: "#fff", fontWeight: 700, textDecoration: "none", fontSize: "0.85rem" }}>
                      <LuDownload size={14} /> Download Receipt
                    </a>
                    <button onClick={() => navigate("receipt")} style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", padding: "0.6rem 1.15rem", borderRadius: "0.5rem", background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.15)", color: "#fff", fontWeight: 600, cursor: "pointer", fontSize: "0.85rem" }}>
                      Open in Sidebar
                    </button>
                  </div>
                </div>
              ) : msg.type === "cert_loading" ? (
                <div key={i} className="fade-up" style={{ maxWidth: "420px", width: "100%", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "1rem", padding: "1rem 1.25rem", display: "flex", alignItems: "center", gap: "0.85rem", boxSizing: "border-box" }}>
                  <span style={{ display: "inline-block", width: "20px", height: "20px", flexShrink: 0, border: "2.5px solid rgba(255,255,255,0.15)", borderTopColor: "#6366f1", borderRadius: "50%", animation: "spin 0.9s linear infinite" }} />
                  <p style={{ color: "#aaa", fontSize: "0.9rem", margin: 0 }}>Fetching your Residence Certificate… please wait</p>
                </div>
              ) : msg.type === "track_form" ? (
                <TrackForm key={i} onSubmit={(appNo) => {
                  // Replace form with fetching indicator
                  setMessages(prev => prev.map((m, idx) =>
                    idx === i ? { ...m, type: "cert_fetching", appNo } : m
                  ));
                  // 3.5s later → replace cert_fetching in-place with cert_download (no duplicate)
                  setTimeout(() => {
                    setMessages(prev => prev.map((m, idx) =>
                      idx === i ? { sender: "agent", text: "", type: "cert_download", appNo } : m
                    ));
                  }, 3500);
                }} />
              ) : msg.type === "cert_fetching" ? (
                <div key={i} className="fade-up" style={{ maxWidth: "420px", width: "100%", background: "rgba(168,85,247,0.08)", border: "1px solid rgba(168,85,247,0.2)", borderRadius: "1rem", padding: "1rem 1.25rem", display: "flex", alignItems: "center", gap: "0.85rem", boxSizing: "border-box" }}>
                  <span style={{ display: "inline-block", width: "20px", height: "20px", flexShrink: 0, border: "2.5px solid rgba(168,85,247,0.3)", borderTopColor: "#a855f7", borderRadius: "50%", animation: "spin 0.9s linear infinite" }} />
                  <p style={{ color: "#c084fc", fontSize: "0.9rem", margin: 0, lineHeight: 1.4 }}>Retrieving certificate for Application Number <strong>{msg.appNo || msg.refNo}</strong>…</p>
                </div>
              ) : msg.type === "cert_download" ? (
                <div key={i} className="fade-up" style={{ maxWidth: "420px", width: "100%", background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.25)", borderRadius: "1rem", padding: "1.25rem", boxSizing: "border-box" }}>
                  <p style={{ color: "#fff", fontWeight: 600, marginBottom: "0.75rem", fontSize: "0.95rem" }}>Your Residence Certificate is ready.</p>
                  <a href="/certificate.pdf" download="ResidenceCertificate.pdf" style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem", padding: "0.65rem 1.35rem", borderRadius: "0.5rem", background: "linear-gradient(135deg,#22c55e,#16a34a)", color: "#fff", fontWeight: 700, textDecoration: "none", fontSize: "0.9rem", boxShadow: "0 4px 14px rgba(34,197,94,0.3)" }}>
                    <LuDownload size={15} /> Download Certificate
                  </a>
                </div>
              ) : (
                <ChatBubble key={i} sender={msg.sender} message={msg.text} />
              )
            )}

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
        />
      </>)}
      </>)}
      </div>

      {/* ── Modals ── */}
      <AutomationModal      isOpen={!!automationEvent}    eventData={automationEvent}  onSubmit={handleAutomationSubmit} onAction={handleAutomationAction} />
      <SelfDeclarationModal isOpen={showSelfDeclaration}  downloadPath={selfDeclarationPath} onSubmit={handleSelfDeclarationSubmit} onExit={handleSelfDeclarationExit} />
      <DocumentNumberModal  isOpen={showDocumentNumber}   onSubmit={handleDocumentNumberSubmit} />

      {/* ── Payment QR Modal ── */}
      {(paymentQr || paymentSuccess) && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 1000,
          background: "rgba(0,0,0,0.75)", backdropFilter: "blur(10px)", display: "flex",
          alignItems: "center", justifyContent: "center", padding: "1rem", boxSizing: "border-box"
        }}>
          <div style={{
            background: "#1a1a2e", borderRadius: "1.25rem", padding: "1.75rem",
            maxWidth: "420px", width: "100%", textAlign: "center",
            boxShadow: "0 12px 48px rgba(0,0,0,0.6)", color: "#fff",
            position: "relative", boxSizing: "border-box", border: "1px solid rgba(255,255,255,0.1)"
          }}>
            <button
              onClick={() => { setPaymentQr(null); setPaymentSuccess(null); }}
              style={{
                position: "absolute", top: "1rem", right: "1rem",
                background: "rgba(255,255,255,0.08)", border: "none",
                color: "rgba(255,255,255,0.6)", borderRadius: "50%",
                width: "28px", height: "28px", display: "flex",
                alignItems: "center", justifyContent: "center", cursor: "pointer"
              }}
              title="Close"
            >
              <LuX size={16} />
            </button>

            {paymentSuccess ? (
              <>
                <div style={{ display: "flex", justifyContent: "center", marginBottom: "0.75rem", marginTop: "0.5rem" }}>
                  <LuCircleCheckBig size={48} color="#4ade80" />
                </div>
                <h2 style={{ margin: "0 0 0.5rem", fontSize: "1.35rem" }}>Payment Successful!</h2>
                <p style={{ color: "rgba(255,255,255,0.7)", fontSize: "0.85rem", marginBottom: "1.25rem", lineHeight: 1.5 }}>
                  Your process is complete! You can download your receipt and certificate from the sidebar at any time.
                </p>

                <div style={{ display: "flex", gap: "0.75rem", justifyContent: "center", flexWrap: "wrap" }}>
                  <button onClick={() => { setPaymentSuccess(null); navigate("receipt"); }} style={{
                    padding: "0.65rem 1.25rem", borderRadius: "0.5rem",
                    background: "linear-gradient(135deg,#22c55e,#16a34a)", border: "none", color: "#fff",
                    fontWeight: 700, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "0.4rem",
                    fontSize: "0.9rem"
                  }}>
                    <LuDownload size={15} /> Go to Downloads
                  </button>
                  <button onClick={() => setPaymentSuccess(null)} style={{
                    padding: "0.65rem 1.25rem", borderRadius: "0.5rem",
                    background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.15)", color: "#fff",
                    fontWeight: 600, cursor: "pointer", fontSize: "0.9rem"
                  }}>Close</button>
                </div>
              </>
            ) : (
              <>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "0.5rem", marginBottom: "0.25rem", marginTop: "0.25rem" }}>
                  <LuQrCode size={22} color="#60a5fa" />
                  <h2 style={{ margin: 0, fontSize: "1.25rem" }}>Scan to Pay</h2>
                </div>
                <p style={{ color: "#aaa", fontSize: "0.82rem", marginBottom: "1rem", lineHeight: 1.4 }}>
                  Open any UPI app and scan the QR code below to complete your ₹60 payment.
                </p>
                <img src="/upi_qr.png" alt="UPI QR Code"
                  style={{ width: "220px", maxWidth: "100%", height: "auto", aspectRatio: "1/1", objectFit: "contain",
                    borderRadius: "0.75rem", background: "#fff", padding: "0.5rem",
                    margin: "0 auto 1rem", display: "block" }} />
                <p style={{ color: "#888", fontSize: "0.78rem", marginBottom: "1rem" }}>
                  After scanning and completing the payment, click the button below.
                </p>
                {/* ── Loading receipt spinner ── */}
                {gettingReceipt && (
                  <p style={{ color: "#aaa", fontSize: "0.85rem", marginBottom: "0.75rem", textAlign: "center" }}>
                    <span style={{ display: "inline-block", width: "14px", height: "14px", border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "#fff", borderRadius: "50%", animation: "spin 0.8s linear infinite", marginRight: "0.5rem", verticalAlign: "middle" }} />
                    Loading your receipt...
                  </p>
                )}
                <button
                  onClick={() => { sendWS({ type: "USER_ANSWER", data: "paid" }); setGettingReceipt(true); }}
                  style={{
                    width: "100%", padding: "0.75rem", borderRadius: "0.6rem",
                    background: "linear-gradient(135deg, #22c55e, #16a34a)",
                    border: "none", color: "#fff", fontWeight: 700,
                    fontSize: "0.95rem", cursor: "pointer",
                    display: "inline-flex", alignItems: "center", justifyContent: "center", gap: "0.5rem",
                    boxShadow: "0 4px 14px rgba(34, 197, 94, 0.35)",
                  }}
                >
                  <LuCircleCheck size={18} />
                  <span>I have paid</span>
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── Clear My Data Confirmation Modal ── */}
      {showClearModal && (
        <div style={{ position: "fixed", inset: 0, zIndex: 999, background: "rgba(0,0,0,0.7)", backdropFilter: "blur(8px)", display: "flex", alignItems: "center", justifyContent: "center", padding: "1rem" }}>
          <div style={{ background: "#1a1a1a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "1.25rem", padding: "2rem", maxWidth: "22rem", width: "100%", textAlign: "center", boxShadow: "0 24px 64px rgba(0,0,0,0.5)" }}>
            <div style={{ width: "3.5rem", height: "3.5rem", borderRadius: "50%", background: "rgba(239,68,68,0.15)", border: "1px solid rgba(239,68,68,0.3)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 1.25rem" }}>
              <LuTrash2 size={24} color="#ef4444" />
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
