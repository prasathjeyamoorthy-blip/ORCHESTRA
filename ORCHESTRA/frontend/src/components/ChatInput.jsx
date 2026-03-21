import { useState, useRef, useCallback } from "react";
import { LuPlus, LuMic, LuSquare, LuSendHorizontal } from "react-icons/lu";

function useAutoResize(minH = 48, maxH = 150) {
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
  { label: "Required Documents",  send: "required documents" },
  { label: "Step-by-Step Guide",  send: "step-by-step guide" },
  { label: "Track Application",   send: "track application" },
  { label: "Submit Documents",    send: "submit documents" },
  { label: "General Help",        send: "general help" },
];

export default function ChatInput({ onSend, disabled, isGenerating, onStop, showChips }) {
  const [input, setInput] = useState("");
  const { ref, adjust } = useAutoResize(48, 150);

  const handleSend = () => {
    if (isGenerating) { onStop?.(); return; }
    if (disabled || !input.trim()) return;
    onSend(input);
    setInput("");
    adjust(true);
  };

  return (
    <div className="input-bar-wrap" style={{ paddingBottom: "1.25rem" }}>
      <div className="input-bar-inner">



        {/* Input box */}
        <div style={{
          background: "rgba(0,0,0,0.55)",
          backdropFilter: "blur(14px)",
          border: "1px solid rgba(255,255,255,0.12)",
          borderRadius: "0.875rem",
          overflow: "hidden",
        }}>
          <textarea
            ref={ref}
            value={input}
            placeholder="Ask anything"
            rows={1}
            onChange={e => { setInput(e.target.value); adjust(); }}
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), handleSend())}
            disabled={disabled && !isGenerating}
            style={{
              width: "100%", resize: "none", border: "none", outline: "none",
              background: "transparent",
              color: "#fff", fontSize: "0.9375rem",
              fontFamily: "inherit", lineHeight: 1.6,
              padding: "0.75rem 1rem 0",
              minHeight: "48px", maxHeight: "150px",
              overflow: "hidden",
              boxSizing: "border-box",
            }}
          />
          <div style={{
            display: "flex", alignItems: "center",
            justifyContent: "space-between",
            padding: "0.375rem 0.625rem 0.5rem",
          }}>
            <button
              aria-label="Attach"
              style={{
                width: "2rem", height: "2rem", borderRadius: "9999px",
                border: "none", background: "transparent",
                color: "rgba(255,255,255,0.45)", cursor: "pointer",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}
            >
              <LuPlus size={17} />
            </button>
            <div style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
              <button
                aria-label="Voice"
                style={{
                  width: "2rem", height: "2rem", borderRadius: "9999px",
                  border: "none", background: "transparent",
                  color: "rgba(255,255,255,0.45)", cursor: "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}
              >
                <LuMic size={16} />
              </button>
              <button
                onClick={handleSend}
                disabled={!isGenerating && (disabled || !input.trim())}
                aria-label="Send"
                style={{
                  width: "2rem", height: "2rem", borderRadius: "9999px",
                  border: "none",
                  background: isGenerating ? "#dc2626" : (disabled || !input.trim()) ? "rgba(255,255,255,0.08)" : "#ffffff",
                  color: isGenerating ? "#fff" : (disabled || !input.trim()) ? "rgba(255,255,255,0.3)" : "#000",
                  cursor: (disabled && !isGenerating) ? "not-allowed" : "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  transition: "background 0.15s",
                  opacity: (!isGenerating && (disabled || !input.trim())) ? 0.5 : 1,
                }}
              >
                {isGenerating
                  ? <LuSquare size={12} fill="currentColor" />
                  : <LuSendHorizontal size={15} />
                }
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
