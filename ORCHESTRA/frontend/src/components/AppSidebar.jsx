import { useState, useRef, useEffect } from "react";
import {
  Menu, LayoutDashboard, BookOpen,
  FileCheck, Phone, Settings, User2, ChevronUp, X,
} from "lucide-react";

const NAV_ITEMS = [
  { title: "Home",               icon: LayoutDashboard, page: "home" },
  { title: "FAQ",                icon: BookOpen,        page: "faq" },
  { title: "Application Status", icon: FileCheck,       page: "status" },
  { title: "Contact",            icon: Phone,           page: "contact" },
];

const ICON_W = "2.25rem";
const FULL_W = "13.5rem";

const bg     = "rgba(0,0,0,0.12)";
const border = "rgba(255,255,255,0.08)";
const col    = "rgba(255,255,255,0.70)";
const colAct = "#ffffff";
const hover  = "rgba(255,255,255,0.08)";
const actBg  = "rgba(255,255,255,0.12)";

function NavContent({ open, activePage, onNavigate, onClose, onToggle, userMenu, setUserMenu, userMenuRef }) {
  const row = {
    display: "flex", alignItems: "center",
    width: "100%", border: "none", background: "transparent",
    cursor: "pointer", fontFamily: "inherit",
    borderRadius: "0.375rem",
    transition: "background 0.12s, color 0.12s",
    color: col, padding: 0,
  };

  return (
    <>
      {/* Nav items */}
      <div style={{ flex: 1, padding: "0.5rem 0.375rem", display: "flex", flexDirection: "column", gap: "0.125rem", overflowY: "auto", overflowX: "hidden" }}>
        {/* Hamburger / close */}
        {onClose ? (
          <button onClick={onClose} style={{ ...row, justifyContent: "flex-start", padding: "0.65rem 0.625rem", gap: "0.75rem", fontSize: "0.9375rem" }}
            onMouseEnter={e => e.currentTarget.style.background = hover}
            onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
            <X size={20} style={{ flexShrink: 0 }} />
            <span style={{ whiteSpace: "nowrap" }}>Close</span>
          </button>
        ) : (
          <button onClick={onToggle} style={{ ...row, justifyContent: open ? "flex-start" : "center", padding: open ? "0.65rem 0.625rem" : "0.65rem", gap: "0.75rem", fontSize: "0.9375rem" }}
            onMouseEnter={e => e.currentTarget.style.background = hover}
            onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
            <Menu size={20} style={{ flexShrink: 0 }} />
          </button>
        )}

        {NAV_ITEMS.map(({ title, icon: Icon, page }) => {
          const isActive = activePage === page;
          return (
            <button key={page} onClick={() => { onNavigate(page); onClose?.(); }}
              title={!open ? title : undefined}
              style={{ ...row, justifyContent: open ? "flex-start" : "center", padding: open ? "0.65rem 0.625rem" : "0.65rem", gap: "0.75rem", fontSize: "0.9375rem", fontWeight: isActive ? 600 : 400, color: isActive ? colAct : col, background: isActive ? actBg : "transparent" }}
              onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = hover; }}
              onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = "transparent"; }}>
              <Icon size={20} style={{ flexShrink: 0 }} />
              {open && <span style={{ whiteSpace: "nowrap" }}>{title}</span>}
            </button>
          );
        })}
      </div>

      {/* Footer */}
      <div style={{ padding: "0.5rem 0.375rem", display: "flex", flexDirection: "column", gap: "0.125rem" }}>
        <button title={!open ? "Settings" : undefined}
          style={{ ...row, justifyContent: open ? "flex-start" : "center", padding: open ? "0.65rem 0.625rem" : "0.65rem", gap: "0.75rem", fontSize: "0.9375rem" }}
          onMouseEnter={e => e.currentTarget.style.background = hover}
          onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
          <Settings size={20} style={{ flexShrink: 0 }} />
          {open && <span style={{ whiteSpace: "nowrap" }}>Settings</span>}
        </button>

        <div ref={userMenuRef} style={{ position: "relative" }}>
          <button onClick={() => setUserMenu(o => !o)} title={!open ? "User" : undefined}
            style={{ ...row, justifyContent: open ? "flex-start" : "center", padding: open ? "0.65rem 0.625rem" : "0.65rem", gap: "0.75rem", fontSize: "0.9375rem", background: userMenu ? actBg : "transparent", color: userMenu ? colAct : col }}
            onMouseEnter={e => { if (!userMenu) e.currentTarget.style.background = hover; }}
            onMouseLeave={e => { if (!userMenu) e.currentTarget.style.background = "transparent"; }}>
            <User2 size={20} style={{ flexShrink: 0 }} />
            {open && <>
              <span style={{ flex: 1, textAlign: "left", whiteSpace: "nowrap" }}>User</span>
              <ChevronUp size={13} style={{ transform: userMenu ? "rotate(0deg)" : "rotate(180deg)", transition: "transform 0.2s" }} />
            </>}
          </button>
          {userMenu && (
            <div style={{ position: "absolute", bottom: "calc(100% + 4px)", left: 0, width: open ? "100%" : "9rem", background: "rgba(10,10,10,0.85)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)", border: `1px solid ${border}`, borderRadius: "0.5rem", boxShadow: "0 4px 20px rgba(0,0,0,0.4)", overflow: "hidden", zIndex: 20 }}>
              {["Account", "Back Up", "Sign out"].map(label => (
                <button key={label} onClick={() => setUserMenu(false)}
                  style={{ ...row, borderRadius: 0, padding: "0.5rem 0.875rem", fontSize: "0.8125rem", justifyContent: "flex-start" }}
                  onMouseEnter={e => e.currentTarget.style.background = hover}
                  onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export function AppSidebar({ activePage, onNavigate, drawerOpen, onDrawerClose }) {
  const [open, setOpen]         = useState(false);
  const [userMenu, setUserMenu] = useState(false);
  const userMenuRef             = useRef(null);

  useEffect(() => {
    const h = (e) => { if (userMenuRef.current && !userMenuRef.current.contains(e.target)) setUserMenu(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  // Close drawer on resize to desktop
  useEffect(() => {
    const onResize = () => { if (window.innerWidth >= 768) onDrawerClose?.(); };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [onDrawerClose]);

  return (
    <>
      {/* ── Desktop sidebar (hidden on mobile) ── */}
      <div className="sidebar-desktop-spacer" style={{ width: open ? FULL_W : ICON_W, minWidth: open ? FULL_W : ICON_W, flexShrink: 0, transition: "width 0.2s ease, min-width 0.2s ease" }}>
        <div style={{ position: "fixed", top: 0, left: 0, bottom: 0, width: open ? FULL_W : ICON_W, background: bg, backdropFilter: "blur(20px) saturate(160%)", WebkitBackdropFilter: "blur(20px) saturate(160%)", borderRight: `1px solid ${border}`, boxShadow: "4px 0 24px rgba(0,0,0,0.20)", display: "flex", flexDirection: "column", overflow: "hidden", transition: "width 0.2s ease", zIndex: 5 }}>
          <NavContent open={open} activePage={activePage} onNavigate={onNavigate} onClose={null} onToggle={() => setOpen(o => !o)} userMenu={userMenu} setUserMenu={setUserMenu} userMenuRef={userMenuRef} />
        </div>
      </div>

      {/* ── Mobile drawer overlay ── */}
      {drawerOpen && (
        <div onClick={onDrawerClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)", zIndex: 200, animation: "fade-in 0.2s ease" }} />
      )}
      {/* Mobile drawer panel */}
      <div style={{ position: "fixed", top: 0, left: 0, bottom: 0, width: "16rem", background: "rgba(10,10,10,0.85)", backdropFilter: "blur(24px)", WebkitBackdropFilter: "blur(24px)", borderRight: `1px solid ${border}`, display: "flex", flexDirection: "column", zIndex: 201, transform: drawerOpen ? "translateX(0)" : "translateX(-100%)", transition: "transform 0.25s cubic-bezier(0.4,0,0.2,1)", overflow: "hidden" }}>
        <NavContent open={true} activePage={activePage} onNavigate={onNavigate} onClose={onDrawerClose} onToggle={null} userMenu={userMenu} setUserMenu={setUserMenu} userMenuRef={userMenuRef} />
      </div>
    </>
  );
}
