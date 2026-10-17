import { useState, useRef, useCallback } from "react";
import { LuSquare, LuSendHorizontal, LuSparkles, LuFileText, LuCircleHelp, LuSearch, LuCircleCheck } from "react-icons/lu";

function useAutoResize(minH = 48, maxH = 140) {
  const ref = useRef(null);
  const adjust = useCallback((reset) => {
    const el = ref.current;
    if (!el) return;
    el.style.height = `${minH}px`;
    if (!reset) el.style.height = `${Math.min(el.scrollHeight, maxH)}px`;
  }, [minH, maxH]);
  return { ref, adjust };
}

const QUICK_ACTIONS = [
  { label: "Required Documents", send: "What documents are required for residence certificate?", icon: LuFileText },
  { label: "Step-by-Step Guide", send: "What is the complete process to apply for residence certificate?", icon: LuCircleHelp },
  { label: "Check Eligibility",  send: "Who is eligible to apply for a Tamil Nadu Residence Certificate?", icon: LuCircleCheck },
  { label: "Track Application",  send: "How can I track my residence certificate status?", icon: LuSearch },
];

export default function ChatInput({ onSend, disabled, isGenerating, onStop, showChips = true, currentLanguage = "en" }) {
  const [input, setInput] = useState("");
  const { ref, adjust } = useAutoResize(48, 140);

  const handleSend = () => {
    if (isGenerating) { onStop?.(); return; }
    if (disabled || !input.trim()) return;
    onSend(input);
    setInput("");
    adjust(true);
  };

  const handleQuickAction = (text) => {
    if (disabled || isGenerating) return;
    onSend(text);
  };

  return (
    <div className="input-bar-wrap" style={{ paddingBottom: "1.25rem", width: "100%", maxWidth: "48rem", margin: "0 auto" }}>
      <div className="input-bar-inner" style={{ display: "flex", flexDirection: "column", gap: "0.625rem" }}>

        {/* Quick Action Pills */}
        {showChips && !isGenerating && (
          <div style={{
            display: "flex",
            gap: "0.5rem",
            overflowX: "auto",
            padding: "0.25rem 0.25rem 0.25rem",
            scrollbarWidth: "none",
            WebkitOverflowScrolling: "touch",
          }}>
            {QUICK_ACTIONS.map(({ label, send, icon: Icon }) => (
              <button
                key={label}
                onClick={() => handleQuickAction(send)}
                disabled={disabled}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.4rem",
                  whiteSpace: "nowrap",
                  padding: "0.4rem 0.85rem",
                  borderRadius: "9999px",
                  background: "rgba(255,255,255,0.05)",
                  backdropFilter: "blur(12px)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  color: "rgba(255,255,255,0.85)",
                  fontSize: "0.78125rem",
                  fontWeight: 600,
                  cursor: disabled ? "not-allowed" : "pointer",
                  transition: "all 0.18s ease",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
                }}
                onMouseEnter={e => {
                  if (!disabled) {
                    e.currentTarget.style.background = "rgba(255,255,255,0.12)";
                    e.currentTarget.style.borderColor = "rgba(255,255,255,0.3)";
                    e.currentTarget.style.color = "#ffffff";
                    e.currentTarget.style.transform = "translateY(-1px)";
                  }
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = "rgba(255,255,255,0.05)";
                  e.currentTarget.style.borderColor = "rgba(255,255,255,0.12)";
                  e.currentTarget.style.color = "rgba(255,255,255,0.85)";
                  e.currentTarget.style.transform = "translateY(0)";
                }}
              >
                <Icon size={13} style={{ color: "#38bdf8", flexShrink: 0 }} />
                <span>{label}</span>
              </button>
            ))}
          </div>
        )}

        {/* Input Box Glass Container */}
        <div style={{
          background: "linear-gradient(180deg, rgba(20,22,28,0.85) 0%, rgba(12,14,18,0.92) 100%)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          border: "1px solid rgba(255,255,255,0.14)",
          borderRadius: "1rem",
          boxShadow: "0 8px 32px rgba(0,0,0,0.45), 0 0 0 1px rgba(255,255,255,0.05)",
          overflow: "hidden",
          transition: "border-color 0.2s, box-shadow 0.2s",
        }}>
          {/* Subtle Top Metadata Bar */}
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0.45rem 1rem 0.25rem",
            borderBottom: "1px solid rgba(255,255,255,0.06)",
            fontSize: "0.6875rem",
            color: "rgba(255,255,255,0.45)",
            fontWeight: 500
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
              <span style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                background: "#10b981",
                boxShadow: "0 0 8px #10b981",
                display: "inline-block"
              }} />
              <span>TNeGA e-Sevai Digital Desk</span>
            </div>
            <div style={{ display: "none", sm: { display: "block" } }}>
              <span>Enter ↵ to send</span>
            </div>
          </div>

          <textarea
            ref={ref}
            value={input}
            placeholder={currentLanguage === "ta" ? "இருப்பிடச் சான்றிதழ் குறித்து எதுவாயினும் கேளுங்கள்..." : "Ask about Residence Certificate requirements, eligibility, or type 'Apply'..."}
            rows={1}
            onChange={e => { setInput(e.target.value); adjust(); }}
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), handleSend())}
            disabled={disabled && !isGenerating}
            style={{
              width: "100%",
              resize: "none",
              border: "none",
              outline: "none",
              background: "transparent",
              color: "#ffffff",
              fontSize: "0.9375rem",
              fontFamily: "'Geist', sans-serif",
              lineHeight: 1.6,
              padding: "0.65rem 1rem 0.25rem",
              minHeight: "48px",
              maxHeight: "140px",
              overflow: "hidden",
              boxSizing: "border-box",
            }}
          />

          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0.4rem 0.75rem 0.55rem",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "rgba(255,255,255,0.4)", fontSize: "0.75rem" }}>
              <LuSparkles size={13} style={{ color: "#38bdf8" }} />
              <span>Official Citizen Assistance</span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <button
                onClick={handleSend}
                disabled={!isGenerating && (disabled || !input.trim())}
                aria-label={isGenerating ? "Stop generation" : "Send message"}
                style={{
                  height: "2.125rem",
                  padding: "0 0.85rem",
                  borderRadius: "0.5rem",
                  border: "none",
                  background: isGenerating
                    ? "#ef4444"
                    : (!disabled && input.trim())
                      ? "linear-gradient(135deg, #ffffff 0%, #e2e8f0 100%)"
                      : "rgba(255,255,255,0.08)",
                  color: isGenerating
                    ? "#ffffff"
                    : (!disabled && input.trim())
                      ? "#0a0a0a"
                      : "rgba(255,255,255,0.3)",
                  cursor: (disabled && !isGenerating) ? "not-allowed" : "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "0.4rem",
                  fontSize: "0.8125rem",
                  fontWeight: 700,
                  transition: "all 0.15s ease",
                  boxShadow: (!disabled && input.trim()) ? "0 2px 10px rgba(255,255,255,0.2)" : "none",
                }}
              >
                {isGenerating ? (
                  <>
                    <LuSquare size={11} fill="currentColor" />
                    <span>Stop</span>
                  </>
                ) : (
                  <>
                    <span>Send</span>
                    <LuSendHorizontal size={14} />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
