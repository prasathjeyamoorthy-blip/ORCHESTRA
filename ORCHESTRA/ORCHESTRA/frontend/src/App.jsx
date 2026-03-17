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
    setShowChecklist(false);
    setWaitingForDocReply(false);
    setIsGenerating(true);
    try {
      const res = await sendMessage(sessionId, text);
      pushBot(res.answer || "Please provide more details.");
      // Only show the document checklist if the backend explicitly returns SHOW_DOCUMENTS stage
      if (res.stage === "SHOW_DOCUMENTS") {
        setShowChecklist(true);
      }
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
      const socket = new WebSocket("ws://localhost:8000/ws/automation");
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
