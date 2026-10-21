import { useEffect, useState, useRef } from "react";
import { LuBot, LuSparkles, LuShieldCheck,
         LuFileCheck, LuLayoutDashboard, LuPhone, LuBookOpen,
         LuMoon, LuSun, LuMenu, LuX, LuDownload } from "react-icons/lu";
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

// ── TrackForm — inline certificate tracking form ─────────────────────────
function TrackForm({ onDone, trackingState }) {
  const [refType, setRefType] = useState("Transaction No.");
  const [refNo, setRefNo]   = useState("");
  const [submitted, setSubmitted] = useState(false);

  if (submitted) {
    return (
      <div className="msg-bot-row fade-up" style={{ display: "flex", justifyContent: "flex-start", marginBottom: "1.5rem" }}>
        <div style={{
          background: "rgba(168,85,247,0.08)", border: "1px solid rgba(168,85,247,0.2)",
          borderRadius: "1rem", padding: "1.25rem 1.5rem", maxWidth: "380px",
          display: "flex", alignItems: "center", gap: "0.75rem", color: "#c084fc",
        }}>
          <div style={{
            width: "1.25rem", height: "1.25rem", borderRadius: "50%", flexShrink: 0,
            border: "2px solid rgba(168,85,247,0.4)", borderTop: "2px solid #a855f7",
            animation: "spin 0.9s linear infinite",
          }} />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          <span style={{ fontSize: "0.9rem" }}>Tracking your application… this may take a moment.</span>
        </div>
      </div>
    );
  }

  return (
    <div className="msg-bot-row fade-up" style={{ display: "flex", justifyContent: "flex-start", marginBottom: "1.5rem" }}>
      <div style={{
        background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: "1rem", padding: "1.25rem 1.5rem", maxWidth: "380px", width: "100%",
      }}>
        {/* Radio buttons */}
        <div style={{ display: "flex", gap: "1.25rem", marginBottom: "1rem" }}>
          {["Transaction No.", "Application No."].map(opt => (
            <label key={opt} style={{
              display: "flex", alignItems: "center", gap: "0.45rem",
              cursor: "pointer", fontSize: "0.875rem", color: refType === opt ? "#c084fc" : "rgba(255,255,255,0.6)",
              fontWeight: refType === opt ? 600 : 400,
            }}>
              <input
                type="radio"
                name="refType"
                value={opt}
                checked={refType === opt}
                onChange={() => setRefType(opt)}
                style={{ accentColor: "#a855f7", cursor: "pointer" }}
              />
              {opt}
            </label>
          ))}
        </div>

        {/* Number input */}
        <input
          type="text"
          value={refNo}
          onChange={e => setRefNo(e.target.value)}
          placeholder={`Enter your ${refType}`}
          style={{
            width: "100%", padding: "0.6rem 0.875rem",
            borderRadius: "0.6rem", border: "1px solid rgba(255,255,255,0.15)",
            background: "rgba(255,255,255,0.06)", color: "#fff",
            fontSize: "0.9rem", outline: "none", boxSizing: "border-box",
            marginBottom: "0.875rem",
          }}
          onKeyDown={e => e.key === "Enter" && refNo.trim() && (setSubmitted(true), onDone(refType, refNo.trim()))}
        />

        {/* Done button */}
        <button
          disabled={!refNo.trim()}
          onClick={() => { setSubmitted(true); onDone(refType, refNo.trim()); }}
          style={{
            width: "100%", padding: "0.65rem",
            borderRadius: "0.6rem", border: "none",
            background: refNo.trim()
              ? "linear-gradient(135deg, #a855f7, #6366f1)"
              : "rgba(255,255,255,0.08)",
            color: refNo.trim() ? "#fff" : "rgba(255,255,255,0.3)",
            fontWeight: 600, fontSize: "0.9rem",
            cursor: refNo.trim() ? "pointer" : "not-allowed",
            transition: "all 0.2s",
          }}
        >
          Done
        </button>
      </div>
    </div>
  );
}

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
  const [trackingState, setTrackingState] = useState(null); // null | "loading" | "done"
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

    // Track status intercept — show inline radio+input form
    const trackKeywords = ["track", "status", "certificate status", "track my certificate",
      "track the status", "check status", "check my certificate", "i want to check",
      "where is my certificate", "status of my certificate", "track the status of my certificate"];
    if (trackKeywords.some(k => lower.includes(k))) {
      pushBot("Sure! To track your certificate, please provide your reference number.");
      setMessages(prev => [...prev, { type: "track_form" }]);
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
  const [paymentQr, setPaymentQr]                     = useState(null); // { qr_image, payment_url }
  const [paymentSuccess, setPaymentSuccess]           = useState(null);
  const [gettingReceipt, setGettingReceipt]           = useState(false); // true while backend is fetching receipt
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
        if      (data.type === "STATUS_UPDATE")               { setAutomationStatus(data.message); if (data.message === "Getting your receipt…") setGettingReceipt(true); }
        else if (data.type === "STATUS_MESSAGE")              { setAutomationStatus(data.message); if (data.message === "Getting your receipt…") setGettingReceipt(true); }
        else if (data.type === "CAPTCHA_REFRESHED")           { setAutomationEvent(prev => prev ? { ...prev, image: data.image } : prev); }
        else if (data.type === "OPEN_PAYMENT_URL")            {
          // Suppressed — payment is now handled via PAYMENT_QR WebSocket event
        }
        else if (data.type === "SELF_DECLARATION_DOWNLOADED") { setSelfDeclarationPath(data.file_path || data.download_path); setShowSelfDeclaration(true); }
        else if (data.type === "REQUEST_SIGNED_DECLARATION")  { setSelfDeclarationPath(data.download_path); setShowSelfDeclaration(true); }
        else if (data.type === "REQUEST_DOCUMENT_NUMBER")     { setShowDocumentNumber(true); }
        else if (data.type === "PAYMENT_QR")                  { setPaymentQr({ qr_image: data.qr_image, payment_url: data.payment_url }); setPaymentSuccess(null); setGettingReceipt(false); setAutomationEvent(null); }
        else if (data.type === "PAYMENT_SUCCESS")             {
          setPaymentQr(null);
          setGettingReceipt(false);
          setPaymentSuccess(null);
          // Inject receipt + suggestions into chat
          setMessages(prev => [...prev,
            { type: "receipt_download", receipt_url: data.receipt_url || "" },
          ]);
        }
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
          // OTP verification disabled for development
          // if (!sessionStorage.getItem("user_phone")) {
          //   setShowOtpModal(true);
          // }
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
            {messages.map((msg, i) => {
              if (msg.type === "track_form") {
                return (
                  <TrackForm
                    key={i}
                    trackingState={trackingState}
                    onDone={(refType, refNo) => {
                      setTrackingState("loading");
                      // Replace the form message with a loading bubble
                      setMessages(prev => prev.map((m, idx) =>
                        idx === i ? { sender: "agent", text: `Tracking your application (${refType}: **${refNo}**)…` } : m
                      ));
                      // After 5s, push the certificate download message
                      setTimeout(() => {
                        setTrackingState("done");
                        setMessages(prev => [...prev, { type: "cert_download" }]);
                      }, 5000);
                    }}
                  />
                );
              }
              if (msg.type === "cert_download") {
                return (
                  <div key={i} className="msg-bot-row fade-up" style={{ display: "flex", justifyContent: "flex-start", marginBottom: "1.5rem" }}>
                    <div style={{ maxWidth: "380px" }}>
                      <p style={{ color: "#e2e8f0", fontSize: "0.975rem", marginBottom: "0.875rem", lineHeight: 1.6 }}>
                        Here's your certificate!
                      </p>
                      <a
                        href="/cert.pdf"
                        download="Residence_Certificate.pdf"
                        style={{
                          display: "flex", alignItems: "center", gap: "0.6rem",
                          padding: "0.75rem 1.125rem", borderRadius: "0.75rem",
                          border: "1.5px solid rgba(168,85,247,0.5)",
                          background: "rgba(168,85,247,0.1)", color: "#c084fc",
                          fontWeight: 600, fontSize: "0.9rem", textDecoration: "none",
                          cursor: "pointer",
                        }}
                      >
                        <LuDownload size={17} />
                        Download your Residence Certificate as PDF
                      </a>
                    </div>
                  </div>
                );
              }
              if (msg.type === "receipt_download") {
                return (
                  <div key={i} className="msg-bot-row fade-up" style={{ display: "flex", justifyContent: "flex-start", marginBottom: "1.5rem" }}>
                    <div style={{ maxWidth: "400px" }}>
                      <p style={{ color: "#e2e8f0", fontSize: "0.975rem", marginBottom: "0.875rem", lineHeight: 1.6 }}>
                        Payment complete! Here's your receipt.
                      </p>
                      <a
                        href={msg.receipt_url || "/Receipt_updated(1).pdf"}
                        download="Receipt_updated(1).pdf"
                        style={{
                          display: "flex", alignItems: "center", gap: "0.6rem",
                          padding: "0.75rem 1.125rem", borderRadius: "0.75rem",
                          border: "1.5px solid rgba(168,85,247,0.5)",
                          background: "rgba(168,85,247,0.1)", color: "#c084fc",
                          fontWeight: 600, fontSize: "0.9rem", textDecoration: "none",
                          cursor: "pointer", marginBottom: "0.75rem",
                        }}
                      >
                        <LuDownload size={17} />
                        Download Receipt
                      </a>
                      {/* Suggestion prompts */}
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                        {[
                          "Track the status of my certificate",
                          "What happens next after payment?",
                          "How long does it take to receive my certificate?",
                        ].map(prompt => (
                          <button
                            key={prompt}
                            onClick={() => handleSend(prompt)}
                            style={{
                              display: "flex", alignItems: "center", gap: "0.5rem",
                              padding: "0.55rem 0.875rem", borderRadius: "0.625rem",
                              border: "1px solid rgba(255,255,255,0.1)",
                              background: "rgba(255,255,255,0.04)",
                              color: "rgba(255,255,255,0.7)", fontSize: "0.82rem",
                              textAlign: "left", cursor: "pointer", fontFamily: "inherit",
                            }}
                          >
                            <span style={{ color: "rgba(255,255,255,0.3)", fontSize: "0.75rem" }}>↳</span>
                            {prompt}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              }
              return <ChatBubble key={i} sender={msg.sender} message={msg.text} />;
            })}

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
                onOpenSocket={() => {
                  // Reset payment states before starting new automation
                  setPaymentQr(null);
                  setGettingReceipt(false);
                  setPaymentSuccess(null);
                  return openAutomationSocket();
                }}
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

      {/* ── Payment QR / Receipt Modal ── */}
      {(paymentQr || gettingReceipt || paymentSuccess) && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 9999,
          background: "rgba(0,0,0,0.80)", display: "flex",
          alignItems: "center", justifyContent: "center",
        }}>
          <div style={{
            background: "#1a1a2e", borderRadius: "1.25rem", padding: "2rem",
            maxWidth: "420px", width: "90%", textAlign: "center",
            boxShadow: "0 8px 40px rgba(0,0,0,0.6)", color: "#fff",
          }}>

            {/* ── Success screen ── */}
            {paymentSuccess ? (
              <>
                <h2 style={{ margin: "0 0 0.25rem", fontSize: "1.3rem" }}>Payment Complete</h2>
                <p style={{ color: "#aaa", fontSize: "0.85rem", marginBottom: "1.25rem" }}>
                  Your application has been submitted successfully.
                </p>

                {/* Receipt download button — prefer Supabase URL from portal, fallback to local file */}
                {true ? (
                  <a
                    href={paymentSuccess.receipt_url || "/Receipt_updated(1).pdf"}
                    download="Receipt_updated(1).pdf"
                    style={{
                      display: "flex", alignItems: "center", justifyContent: "center",
                      gap: "0.5rem", width: "100%", padding: "0.75rem 1rem",
                      borderRadius: "0.75rem", border: "1.5px solid rgba(168,85,247,0.5)",
                      background: "rgba(168,85,247,0.1)", color: "#c084fc",
                      fontWeight: 600, fontSize: "0.95rem", textDecoration: "none",
                      marginBottom: "1.25rem", boxSizing: "border-box",
                      cursor: "pointer",
                    }}
                  >
                    <LuDownload size={17} />
                    Download Receipt
                  </a>
                ) : (
                  <div style={{
                    display: "flex", alignItems: "center", justifyContent: "center",
                    gap: "0.5rem", width: "100%", padding: "0.75rem 1rem",
                    borderRadius: "0.75rem", border: "1.5px solid rgba(255,255,255,0.1)",
                    background: "rgba(255,255,255,0.04)", color: "rgba(255,255,255,0.35)",
                    fontWeight: 500, fontSize: "0.9rem", marginBottom: "1.25rem",
                    boxSizing: "border-box",
                  }}>
                    <LuDownload size={17} />
                    Receipt not available
                  </div>
                )}

                {/* Suggestion prompts */}
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginBottom: "1.25rem" }}>
                  {[
                    "Track the status of my certificate",
                    "What happens next after payment?",
                    "How long does it take to receive my certificate?",
                  ].map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => {
                        setPaymentSuccess(null);
                        handleSend(prompt);
                      }}
                      style={{
                        display: "flex", alignItems: "center", gap: "0.5rem",
                        padding: "0.6rem 0.875rem", borderRadius: "0.625rem",
                        border: "1px solid rgba(255,255,255,0.1)",
                        background: "rgba(255,255,255,0.04)",
                        color: "rgba(255,255,255,0.75)", fontSize: "0.82rem",
                        textAlign: "left", cursor: "pointer", fontFamily: "inherit",
                      }}
                    >
                      <span style={{ color: "rgba(255,255,255,0.3)", fontSize: "0.75rem" }}>↳</span>
                      {prompt}
                    </button>
                  ))}
                </div>

                <button
                  onClick={() => setPaymentSuccess(null)}
                  style={{
                    width: "100%", padding: "0.65rem", borderRadius: "0.6rem",
                    background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.1)",
                    color: "rgba(255,255,255,0.6)", fontWeight: 600, fontSize: "0.9rem",
                    cursor: "pointer",
                  }}
                >
                  Close
                </button>
              </>

            ) : gettingReceipt ? (
              /* ── Getting receipt loading screen ── */
              <>
                <div style={{
                  width: "3rem", height: "3rem", borderRadius: "50%",
                  border: "3px solid rgba(168,85,247,0.2)",
                  borderTop: "3px solid #a855f7",
                  animation: "spin 0.9s linear infinite",
                  margin: "0 auto 1.25rem",
                }} />
                <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                <h2 style={{ margin: "0 0 0.4rem", fontSize: "1.2rem" }}>Getting your receipt…</h2>
                <p style={{ color: "#888", fontSize: "0.85rem" }}>
                  Please wait while we fetch your payment receipt.
                </p>
              </>

            ) : (
              /* ── QR scan screen ── */
              <>
                <h2 style={{ margin: "0 0 0.25rem" }}>Scan to Pay</h2>
                <p style={{ color: "#aaa", fontSize: "0.85rem", marginBottom: "1.25rem" }}>
                  Open any UPI app and scan the QR code below to complete your ₹60 payment.
                </p>
                {paymentQr.qr_image ? (
                  <img src={paymentQr.qr_image} alt="UPI QR Code"
                    style={{ width: "260px", height: "260px", objectFit: "contain",
                      borderRadius: "0.75rem", background: "#fff", padding: "0.5rem",
                      marginBottom: "1.25rem" }} />
                ) : (
                  <div style={{ color: "#facc15", marginBottom: "1rem" }}>
                    QR image not available — please check the browser window.
                  </div>
                )}
                <p style={{ color: "#888", fontSize: "0.78rem", marginBottom: "1.25rem" }}>
                  After scanning and completing the payment, click the button below.
                </p>
                <button
                  onClick={() => {
                    sendWS({ type: "USER_ANSWER", data: "paid" });
                    setPaymentQr(null);
                    setGettingReceipt(true);
                    // Fallback for test mode (no WS backend) — auto-resolve after 3s
                    // In real automation PAYMENT_SUCCESS WS event will resolve it first
                    const ws = wsRef.current;
                    const isConnected = ws && ws.readyState === WebSocket.OPEN;
                    if (!isConnected) {
                      setTimeout(() => {
                        setGettingReceipt(false);
                        setMessages(prev => [...prev, { type: "receipt_download", receipt_url: "" }]);
                      }, 3000);
                    }
                  }}
                  style={{
                    width: "100%", padding: "0.75rem", borderRadius: "0.6rem",
                    background: "linear-gradient(135deg, #22c55e, #16a34a)",
                    border: "none", color: "#fff", fontWeight: 700,
                    fontSize: "1rem", cursor: "pointer",
                  }}
                >
                  I have paid
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
