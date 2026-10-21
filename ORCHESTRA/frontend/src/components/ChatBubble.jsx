import ReactMarkdown from "react-markdown";

export default function ChatBubble({ sender, message }) {
  const isBot = sender === "agent" || sender === "bot" || sender === "assistant";

  if (isBot) {
    const isEmpty = !message || !message.trim();

    return (
      <div className="msg-bot-row fade-up" style={{ display: "flex", justifyContent: "flex-start", width: "100%" }}>
        <div className="msg-bot" style={{
          background: "transparent",
          border: "none",
          boxShadow: "none",
          padding: "0.15rem 0",
          maxWidth: "100%",
          color: "#ececec",
          fontSize: "0.95rem",
          lineHeight: 1.65,
        }}>
          {isEmpty ? (
            <div className="typing-row" style={{ display: "inline-flex", alignItems: "center", gap: "0.35rem", padding: "0.25rem 0" }}>
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
            </div>
          ) : (
            <ReactMarkdown
              components={{
                p:          ({ children }) => <p className="msg-p" style={{ margin: "0 0 0.5rem 0", lineHeight: 1.65, color: "#e2e8f0" }}>{children}</p>,
                strong:     ({ children }) => <strong className="msg-strong" style={{ color: "#ffffff", fontWeight: 600 }}>{children}</strong>,
                em:         ({ children }) => <em className="msg-em" style={{ color: "#cbd5e1" }}>{children}</em>,
                h1:         ({ children }) => <h2 className="msg-h2" style={{ color: "#ffffff", fontSize: "1.15rem", margin: "0.75rem 0 0.35rem", fontWeight: 700 }}>{children}</h2>,
                h2:         ({ children }) => <h2 className="msg-h2" style={{ color: "#ffffff", fontSize: "1.1rem", margin: "0.75rem 0 0.35rem", fontWeight: 700 }}>{children}</h2>,
                h3:         ({ children }) => <h3 className="msg-h3" style={{ color: "#ffffff", fontSize: "1rem", margin: "0.6rem 0 0.25rem", fontWeight: 600 }}>{children}</h3>,
                ul:         ({ children }) => <ul className="msg-ul" style={{ margin: "0.35rem 0 0.6rem", paddingLeft: "1.25rem", display: "flex", flexDirection: "column", gap: "0.25rem" }}>{children}</ul>,
                ol:         ({ children }) => <ol className="msg-ol" style={{ margin: "0.35rem 0 0.6rem", paddingLeft: "1.25rem", display: "flex", flexDirection: "column", gap: "0.25rem" }}>{children}</ol>,
                li:         ({ children }) => <li className="msg-li" style={{ marginBottom: "0.15rem", lineHeight: 1.6, color: "#e2e8f0" }}>{children}</li>,
                hr:         () => <hr className="msg-hr" style={{ border: "none", borderTop: "1px solid rgba(255,255,255,0.12)", margin: "0.75rem 0" }} />,
                code:       ({ children }) => <code className="msg-code" style={{ background: "rgba(255,255,255,0.08)", padding: "0.15rem 0.4rem", borderRadius: "0.25rem", fontSize: "0.875em", color: "#f1f5f9" }}>{children}</code>,
                pre:        ({ children }) => <pre style={{ overflowX: "auto", maxWidth: "100%", background: "rgba(255,255,255,0.05)", padding: "0.75rem", borderRadius: "0.5rem", border: "1px solid rgba(255,255,255,0.1)", margin: "0.5rem 0", boxSizing: "border-box" }}>{children}</pre>,
                blockquote: ({ children }) => <blockquote className="msg-blockquote" style={{ borderLeft: "3px solid #a855f7", margin: "0.6rem 0", paddingLeft: "0.875rem", fontStyle: "italic", color: "#cbd5e1" }}>{children}</blockquote>,
                a:          ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: "#38bdf8", textDecoration: "underline", fontWeight: 600, wordBreak: "break-all" }}>{children}</a>,
                table:      ({ children }) => <div style={{ overflowX: "auto", margin: "0.6rem 0 0.85rem", borderRadius: "0.5rem", border: "1px solid rgba(255,255,255,0.12)" }}><table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem", textAlign: "left" }}>{children}</table></div>,
                thead:      ({ children }) => <thead style={{ background: "rgba(255,255,255,0.06)", borderBottom: "1px solid rgba(255,255,255,0.14)" }}>{children}</thead>,
                tbody:      ({ children }) => <tbody>{children}</tbody>,
                tr:         ({ children }) => <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>{children}</tr>,
                th:         ({ children }) => <th style={{ padding: "0.55rem 0.75rem", fontWeight: 600, color: "#ffffff" }}>{children}</th>,
                td:         ({ children }) => <td style={{ padding: "0.5rem 0.75rem", color: "#e2e8f0" }}>{children}</td>,
              }}
            >
              {message}
            </ReactMarkdown>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="msg-user-row fade-up" style={{ display: "flex", justifyContent: "flex-end", width: "100%" }}>
      <div className="msg-user" style={{
        background: "#2a2a2a",
        border: "1px solid rgba(255, 255, 255, 0.12)",
        borderRadius: "1.125rem",
        borderBottomRightRadius: "0.35rem",
        padding: "0.65rem 1rem",
        maxWidth: "80%",
        color: "#ffffff",
        fontSize: "0.9375rem",
        lineHeight: 1.5,
        wordBreak: "break-word",
        boxShadow: "0 2px 8px rgba(0,0,0,0.2)"
      }}>
        {message}
      </div>
    </div>
  );
}
