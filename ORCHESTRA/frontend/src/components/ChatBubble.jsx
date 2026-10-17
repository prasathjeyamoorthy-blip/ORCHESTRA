import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { LuCopy, LuCheck, LuShieldCheck, LuUser } from "react-icons/lu";

export default function ChatBubble({ sender, message }) {
  const isBot = sender === "agent" || sender === "bot" || sender === "assistant";
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!message) return;
    navigator.clipboard.writeText(message);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isBot) {
    const isEmpty = !message || !message.trim();

    return (
      <div className="msg-bot-row fade-up" style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", marginBottom: "1.75rem", width: "100%" }}>
        {/* Official Civic Assistant Header */}
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          width: "100%",
          maxWidth: "94%",
          padding: "0 0.25rem 0.5rem",
          gap: "0.75rem",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <div style={{
              width: "1.625rem",
              height: "1.625rem",
              borderRadius: "0.375rem",
              background: "rgba(255,255,255,0.08)",
              border: "1px solid rgba(255,255,255,0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              overflow: "hidden",
              boxShadow: "0 2px 6px rgba(0,0,0,0.3)"
            }}>
              <img
                src="/tnega-logo.png"
                alt="TNeGA Seal"
                style={{ width: "100%", height: "100%", objectFit: "contain" }}
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                }}
              />
            </div>
            <span style={{
              fontSize: "0.8125rem",
              fontWeight: 700,
              letterSpacing: "-0.01em",
              color: "#ffffff",
              fontFamily: "'Geist', sans-serif"
            }}>
              TNeGA e-Sevai Guide
            </span>
            <span style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.25rem",
              fontSize: "0.6875rem",
              fontWeight: 600,
              padding: "0.15rem 0.5rem",
              borderRadius: "9999px",
              background: "rgba(16,185,129,0.12)",
              color: "#34d399",
              border: "1px solid rgba(16,185,129,0.25)",
              letterSpacing: "0.02em"
            }}>
              <LuShieldCheck size={11} /> Verified Desk
            </span>
          </div>

          {!isEmpty && (
            <button
              onClick={handleCopy}
              title="Copy response"
              aria-label="Copy response"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.3rem",
                padding: "0.25rem 0.5rem",
                borderRadius: "0.375rem",
                border: "1px solid rgba(255,255,255,0.08)",
                background: "rgba(255,255,255,0.04)",
                color: copied ? "#34d399" : "rgba(255,255,255,0.5)",
                fontSize: "0.6875rem",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = "rgba(255,255,255,0.08)";
                e.currentTarget.style.color = "#ffffff";
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = "rgba(255,255,255,0.04)";
                e.currentTarget.style.color = copied ? "#34d399" : "rgba(255,255,255,0.5)";
              }}
            >
              {copied ? <><LuCheck size={12} /> Copied</> : <><LuCopy size={12} /> Copy</>}
            </button>
          )}
        </div>

        {/* Message Content Container */}
        <div className="msg-bot" style={{
          background: "linear-gradient(180deg, rgba(22,24,29,0.75) 0%, rgba(14,16,20,0.85) 100%)",
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          border: "1px solid rgba(255,255,255,0.09)",
          borderRadius: "0.875rem",
          boxShadow: "0 8px 32px rgba(0,0,0,0.35)",
          padding: "1.125rem 1.35rem",
          maxWidth: "94%",
          width: "100%",
          color: "#e2e8f0",
          fontSize: "0.95rem",
          lineHeight: 1.75,
          position: "relative",
          boxSizing: "border-box"
        }}>
          {isEmpty ? (
            <div className="typing-row" style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", padding: "0.35rem 0" }}>
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
            </div>
          ) : (
            <ReactMarkdown
              components={{
                p:          ({ children }) => <p className="msg-p" style={{ margin: "0 0 0.85rem 0", lineHeight: 1.75, color: "#e2e8f0" }}>{children}</p>,
                strong:     ({ children }) => <strong className="msg-strong" style={{ color: "#ffffff", fontWeight: 700 }}>{children}</strong>,
                em:         ({ children }) => <em className="msg-em" style={{ color: "#cbd5e1" }}>{children}</em>,
                h1:         ({ children }) => <h2 className="msg-h2" style={{ color: "#ffffff", fontSize: "1.2rem", margin: "1rem 0 0.5rem", fontWeight: 700, borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: "0.4rem" }}>{children}</h2>,
                h2:         ({ children }) => <h2 className="msg-h2" style={{ color: "#ffffff", fontSize: "1.125rem", margin: "1rem 0 0.5rem", fontWeight: 700 }}>{children}</h2>,
                h3:         ({ children }) => <h3 className="msg-h3" style={{ color: "#f8fafc", fontSize: "1.025rem", margin: "0.85rem 0 0.35rem", fontWeight: 600 }}>{children}</h3>,
                ul:         ({ children }) => <ul className="msg-ul" style={{ margin: "0.5rem 0 0.95rem", paddingLeft: "1.35rem", display: "flex", flexDirection: "column", gap: "0.4rem" }}>{children}</ul>,
                ol:         ({ children }) => <ol className="msg-ol" style={{ margin: "0.5rem 0 0.95rem", paddingLeft: "1.35rem", display: "flex", flexDirection: "column", gap: "0.4rem" }}>{children}</ol>,
                li:         ({ children }) => <li className="msg-li" style={{ marginBottom: "0.25rem", lineHeight: 1.7, color: "#cbd5e1" }}>{children}</li>,
                hr:         () => <hr className="msg-hr" style={{ border: "none", borderTop: "1px solid rgba(255,255,255,0.1)", margin: "1rem 0" }} />,
                code:       ({ children }) => <code className="msg-code" style={{ background: "rgba(255,255,255,0.09)", border: "1px solid rgba(255,255,255,0.1)", padding: "0.15rem 0.45rem", borderRadius: "0.3rem", fontSize: "0.85em", color: "#f8fafc", fontFamily: "'Geist Mono', monospace" }}>{children}</code>,
                blockquote: ({ children }) => <blockquote className="msg-blockquote" style={{ borderLeft: "3px solid #38bdf8", background: "rgba(56,189,248,0.05)", borderRadius: "0 0.5rem 0.5rem 0", margin: "0.85rem 0", padding: "0.5rem 0.85rem", fontStyle: "normal", color: "#e2e8f0" }}>{children}</blockquote>,
                a:          ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: "#38bdf8", textDecoration: "underline", textUnderlineOffset: "3px", fontWeight: 600, wordBreak: "break-all" }}>{children}</a>,
              }}
            >
              {message}
            </ReactMarkdown>
          )}
        </div>
      </div>
    );
  }

  // User Message
  return (
    <div className="msg-user-row fade-up" style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", marginBottom: "1.5rem", width: "100%" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.35rem", padding: "0 0.25rem 0.35rem", color: "rgba(255,255,255,0.45)", fontSize: "0.6875rem", fontWeight: 600 }}>
        <span>Citizen</span>
        <LuUser size={11} />
      </div>
      <div className="msg-user" style={{
        background: "linear-gradient(135deg, rgba(45,49,58,0.9) 0%, rgba(30,33,40,0.95) 100%)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        border: "1px solid rgba(255, 255, 255, 0.16)",
        borderRadius: "1rem 1rem 0.25rem 1rem",
        padding: "0.85rem 1.25rem",
        maxWidth: "80%",
        color: "#ffffff",
        fontSize: "0.95rem",
        lineHeight: 1.6,
        wordBreak: "break-word",
        boxShadow: "0 4px 16px rgba(0,0,0,0.35)",
        letterSpacing: "-0.01em"
      }}>
        {message}
      </div>
    </div>
  );
}
