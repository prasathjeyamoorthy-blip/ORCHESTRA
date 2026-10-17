import { useState, useEffect } from "react";
import {
  Menu, LayoutDashboard, BookOpen,
  FileCheck, Phone, ShieldCheck, Zap,
  Plus, MessageSquare, Trash2, X,
} from "lucide-react";

const NAV_ITEMS = [
  { title: "Home",               icon: LayoutDashboard, page: "home" },
  { title: "FAQ",                icon: BookOpen,        page: "faq" },
  { title: "Application Status", icon: FileCheck,       page: "status" },
  { title: "Contact Desk",       icon: Phone,           page: "contact" },
];

const ICON_W = "2.5rem";
const FULL_W = "16rem";

const bg     = "rgba(12,14,18,0.75)";
const border = "rgba(255,255,255,0.08)";
const col    = "rgba(255,255,255,0.72)";
const colAct = "#ffffff";
const hover  = "rgba(255,255,255,0.08)";
const actBg  = "linear-gradient(135deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.04) 100%)";

function NavContent({
  open, activePage, onNavigate, onClose, onToggle,
  chatSessions = [], currentSessionId, onNewChat, onSelectChat, onDeleteChat,
  onOpenOtpModal, userPhone, onApplyNow, onClearData
}) {
  const row = {
    display: "flex", alignItems: "center",
    width: "100%", border: "none", background: "transparent",
    cursor: "pointer", fontFamily: "inherit",
    borderRadius: "0.5rem",
    transition: "all 0.15s ease",
    color: col, padding: 0,
  };

  return (
    <>
      {/* Brand & Seal Header */}
      <div style={{
        padding: open ? "0.85rem 0.75rem 0.75rem" : "0.75rem 0.25rem",
        display: "flex",
        alignItems: "center",
        justifyContent: open ? "flex-start" : "center",
        gap: "0.625rem",
        borderBottom: `1px solid ${border}`,
        background: "rgba(255,255,255,0.02)"
      }}>
        <div style={{
          width: "2rem",
          height: "2rem",
          borderRadius: "0.375rem",
          background: "rgba(255,255,255,0.08)",
          border: "1px solid rgba(255,255,255,0.15)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          overflow: "hidden",
          flexShrink: 0,
          boxShadow: "0 2px 8px rgba(0,0,0,0.35)"
        }}>
          <img
            src="/tnega-logo.png"
            alt="TNeGA Seal"
            style={{ width: "100%", height: "100%", objectFit: "contain" }}
            onError={(e) => { e.currentTarget.style.display = "none"; }}
          />
        </div>
        {open && (
          <div style={{ display: "flex", flexDirection: "column", minWidth: 0, flex: 1 }}>
            <span style={{ fontSize: "0.8125rem", fontWeight: 800, color: "#ffffff", letterSpacing: "-0.01em", lineHeight: 1.2 }}>
              TNeGA e-Sevai
            </span>
            <span style={{ fontSize: "0.5625rem", fontWeight: 600, color: "rgba(255,255,255,0.45)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Govt of Tamil Nadu
            </span>
          </div>
        )}
      </div>

      {/* Header controls & New Chat */}
      <div style={{ padding: "0.5rem 0.375rem", display: "flex", flexDirection: "column", gap: "0.375rem", borderBottom: `1px solid ${border}` }}>
        {onClose ? (
          <button onClick={onClose} style={{ ...row, justifyContent: "flex-start", padding: "0.6rem 0.625rem", gap: "0.75rem", fontSize: "0.875rem" }}
            onMouseEnter={e => e.currentTarget.style.background = hover}
            onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
            <X size={18} style={{ flexShrink: 0 }} />
            <span style={{ whiteSpace: "nowrap" }}>Close Menu</span>
          </button>
        ) : (
          <button onClick={onToggle} style={{ ...row, justifyContent: open ? "flex-start" : "center", padding: open ? "0.6rem 0.625rem" : "0.6rem", gap: "0.75rem", fontSize: "0.875rem" }}
            onMouseEnter={e => e.currentTarget.style.background = hover}
            onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
            <Menu size={18} style={{ flexShrink: 0 }} />
            {open && <span style={{ whiteSpace: "nowrap", fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>Collapse Menu</span>}
          </button>
        )}

        {/* New Chat Button */}
        {onNewChat && (
          <button onClick={() => { onNewChat(); onClose?.(); }}
            title={!open ? "New Session" : undefined}
            style={{
              ...row,
              justifyContent: open ? "flex-start" : "center",
              padding: open ? "0.6rem 0.75rem" : "0.6rem",
              gap: "0.75rem",
              fontSize: "0.84375rem",
              fontWeight: 600,
              color: "#fff",
              background: "linear-gradient(135deg, rgba(255,255,255,0.14) 0%, rgba(255,255,255,0.05) 100%)",
              border: `1px solid ${border}`,
              boxShadow: "0 2px 8px rgba(0,0,0,0.2)"
            }}
            onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.2)"}
            onMouseLeave={e => e.currentTarget.style.background = "linear-gradient(135deg, rgba(255,255,255,0.14) 0%, rgba(255,255,255,0.05) 100%)"}>
            <Plus size={16} style={{ flexShrink: 0, color: "#fff" }} />
            {open && <span style={{ whiteSpace: "nowrap" }}>New Citizen Session</span>}
          </button>
        )}
      </div>

      {/* Nav items */}
      <div style={{ flex: 1, padding: "0.5rem 0.375rem", display: "flex", flexDirection: "column", gap: "0.2rem", overflowY: "auto", overflowX: "hidden" }}>
        {NAV_ITEMS.map(({ title, icon: Icon, page }) => {
          const isActive = activePage === page;
          return (
            <button key={page} onClick={() => { onNavigate(page); onClose?.(); }}
              title={!open ? title : undefined}
              style={{
                ...row,
                justifyContent: open ? "flex-start" : "center",
                padding: open ? "0.6rem 0.65rem" : "0.6rem",
                gap: "0.75rem",
                fontSize: "0.875rem",
                fontWeight: isActive ? 600 : 400,
                color: isActive ? colAct : col,
                background: isActive ? actBg : "transparent",
                border: isActive ? "1px solid rgba(255,255,255,0.12)" : "1px solid transparent"
              }}
              onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = hover; }}
              onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = "transparent"; }}>
              <Icon size={18} style={{ flexShrink: 0, color: isActive ? "#38bdf8" : "inherit" }} />
              {open && <span style={{ whiteSpace: "nowrap" }}>{title}</span>}
            </button>
          );
        })}

        {/* Recent Chats Section */}
        {open && chatSessions && chatSessions.length > 0 && (
          <div style={{ marginTop: "1rem", paddingTop: "0.75rem", borderTop: `1px solid ${border}` }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.08em", padding: "0 0.625rem 0.5rem" }}>
              Recent Sessions
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
              {chatSessions.map(session => {
                const isActive = session.id === currentSessionId;
                return (
                  <div key={session.id} style={{ display: "flex", alignItems: "center", position: "relative" }}>
                    <button
                      onClick={() => { onSelectChat(session.id); onClose?.(); }}
                      style={{
                        ...row,
                        justifyContent: "flex-start",
                        padding: "0.5rem 0.625rem",
                        paddingRight: "1.75rem",
                        gap: "0.625rem",
                        fontSize: "0.8125rem",
                        fontWeight: isActive ? 600 : 400,
                        color: isActive ? colAct : col,
                        background: isActive ? actBg : "transparent",
                        textAlign: "left"
                      }}
                      onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = hover; }}
                      onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = "transparent"; }}>
                      <MessageSquare size={14} style={{ flexShrink: 0, opacity: 0.7 }} />
                      <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", flex: 1 }}>
                        {session.title || "Citizen Chat"}
                      </span>
                    </button>
                    {onDeleteChat && (
                      <button
                        onClick={(e) => { e.stopPropagation(); onDeleteChat(session.id); }}
                        title="Delete session"
                        style={{
                          position: "absolute", right: "0.375rem", background: "transparent", border: "none",
                          color: "rgba(255,255,255,0.4)", cursor: "pointer", padding: "0.25rem", display: "flex", alignItems: "center"
                        }}
                        onMouseEnter={e => e.currentTarget.style.color = "#ff4d4f"}
                        onMouseLeave={e => e.currentTarget.style.color = "rgba(255,255,255,0.4)"}>
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div style={{ padding: "0.625rem 0.375rem", display: "flex", flexDirection: "column", gap: "0.25rem", borderTop: `1px solid ${border}`, background: "rgba(0,0,0,0.15)" }}>

        {/* Apply Now button */}
        {onApplyNow && (
          <button
            onClick={() => { onApplyNow(); onClose?.(); }}
            title={!open ? "Apply for Residence Certificate" : undefined}
            style={{
              ...row,
              justifyContent: open ? "flex-start" : "center",
              padding: open ? "0.65rem 0.75rem" : "0.65rem",
              gap: "0.75rem",
              fontSize: "0.875rem",
              fontWeight: 700,
              color: "#fff",
              background: "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
              border: "1px solid rgba(255,255,255,0.15)",
              borderRadius: "0.5rem",
              boxShadow: "0 2px 10px rgba(37,99,235,0.35)",
              marginBottom: "0.25rem",
            }}
            onMouseEnter={e => e.currentTarget.style.opacity = "0.9"}
            onMouseLeave={e => e.currentTarget.style.opacity = "1"}
          >
            <Zap size={16} style={{ flexShrink: 0, color: "#fff" }} />
            {open && <span style={{ whiteSpace: "nowrap" }}>Apply for Certificate</span>}
          </button>
        )}

        {/* Clear My Data button */}
        {onClearData && (
          <button
            onClick={() => { onClearData(); onClose?.(); }}
            title={!open ? "Clear My Data" : undefined}
            style={{
              ...row,
              justifyContent: open ? "flex-start" : "center",
              padding: open ? "0.55rem 0.625rem" : "0.55rem",
              gap: "0.75rem",
              fontSize: "0.8125rem",
              color: "#f87171",
            }}
            onMouseEnter={e => e.currentTarget.style.background = "rgba(239,68,68,0.1)"}
            onMouseLeave={e => e.currentTarget.style.background = "transparent"}
          >
            <Trash2 size={16} style={{ flexShrink: 0, color: "#f87171" }} />
            {open && <span style={{ whiteSpace: "nowrap" }}>Clear My Data</span>}
          </button>
        )}

        {onOpenOtpModal && (
          <button
            onClick={() => { onOpenOtpModal(); onClose?.(); }}
            title={!open ? "Security & PIN" : undefined}
            style={{
              ...row,
              justifyContent: open ? "flex-start" : "center",
              padding: open ? "0.55rem 0.625rem" : "0.55rem",
              gap: "0.75rem",
              fontSize: "0.8125rem",
              color: userPhone ? "#34d399" : "#38bdf8"
            }}
            onMouseEnter={e => e.currentTarget.style.background = hover}
            onMouseLeave={e => e.currentTarget.style.background = "transparent"}
          >
            <ShieldCheck size={18} style={{ flexShrink: 0, color: userPhone ? "#34d399" : "#38bdf8" }} />
            {open && <span style={{ whiteSpace: "nowrap", fontWeight: 600 }}>{userPhone ? "PIN Authenticated" : "Verify Mobile & PIN"}</span>}
          </button>
        )}
      </div>
    </>
  );
}

export function AppSidebar({
  activePage, onNavigate, drawerOpen, onDrawerClose,
  chatSessions, currentSessionId, onNewChat, onSelectChat, onDeleteChat,
  onOpenOtpModal, userPhone, onApplyNow, onClearData
}) {
  const [open, setOpen] = useState(false);

  // Close drawer on resize to desktop
  useEffect(() => {
    const onResize = () => { if (window.innerWidth >= 768) onDrawerClose?.(); };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [onDrawerClose]);

  const navProps = {
    open, activePage, onNavigate,
    chatSessions, currentSessionId, onNewChat, onSelectChat, onDeleteChat,
    onOpenOtpModal, userPhone, onApplyNow, onClearData
  };

  return (
    <>
      {/* Desktop sidebar */}
      <div className="sidebar-desktop-spacer" style={{ width: open ? FULL_W : ICON_W, minWidth: open ? FULL_W : ICON_W, flexShrink: 0, transition: "width 0.2s ease, min-width 0.2s ease" }}>
        <div style={{ position: "fixed", top: 0, left: 0, bottom: 0, width: open ? FULL_W : ICON_W, background: bg, backdropFilter: "blur(24px) saturate(180%)", WebkitBackdropFilter: "blur(24px) saturate(180%)", borderRight: `1px solid ${border}`, boxShadow: "4px 0 28px rgba(0,0,0,0.35)", display: "flex", flexDirection: "column", overflow: "hidden", transition: "width 0.2s ease", zIndex: 5 }}>
          <NavContent {...navProps} open={open} onClose={null} onToggle={() => setOpen(o => !o)} />
        </div>
      </div>

      {/* Mobile drawer overlay */}
      {drawerOpen && (
        <div onClick={onDrawerClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.65)", backdropFilter: "blur(6px)", zIndex: 200, animation: "fade-in 0.2s ease" }} />
      )}
      {/* Mobile drawer panel */}
      <div style={{ position: "fixed", top: 0, left: 0, bottom: 0, width: "16.5rem", background: "rgba(12,14,18,0.92)", backdropFilter: "blur(24px)", WebkitBackdropFilter: "blur(24px)", borderRight: `1px solid ${border}`, display: "flex", flexDirection: "column", zIndex: 201, transform: drawerOpen ? "translateX(0)" : "translateX(-100%)", transition: "transform 0.25s cubic-bezier(0.4,0,0.2,1)", overflow: "hidden" }}>
        <NavContent {...navProps} open={true} onClose={onDrawerClose} onToggle={null} />
      </div>
    </>
  );
}
