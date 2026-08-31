import ReactMarkdown from "react-markdown";

export default function ChatBubble({ sender, message }) {
  const isBot = sender === "agent" || sender === "bot" || sender === "assistant";

  if (isBot) {
    const isEmpty = !message || !message.trim();

    return (
      <div className="msg-bot-row fade-up" style={{ display: "flex", justifyContent: "flex-start", marginBottom: "1.5rem" }}>
        <div className="msg-bot" style={{
          background: "transparent",
          border: "none",
          boxShadow: "none",
          padding: "0.25rem 0",
          maxWidth: "92%",
          color: "#ececec",
          fontSize: "0.975rem",
          lineHeight: 1.7,
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
                p:          ({ children }) => <p className="msg-p" style={{ margin: "0 0 0.75rem 0", lineHeight: 1.7, color: "#e2e8f0" }}>{children}</p>,
                strong:     ({ children }) => <strong className="msg-strong" style={{ color: "#ffffff", fontWeight: 600 }}>{children}</strong>,
                em:         ({ children }) => <em className="msg-em" style={{ color: "#cbd5e1" }}>{children}</em>,
                h1:         ({ children }) => <h2 className="msg-h2" style={{ color: "#ffffff", fontSize: "1.15rem", margin: "1rem 0 0.5rem", fontWeight: 700 }}>{children}</h2>,
                h2:         ({ children }) => <h2 className="msg-h2" style={{ color: "#ffffff", fontSize: "1.1rem", margin: "1rem 0 0.5rem", fontWeight: 700 }}>{children}</h2>,
                h3:         ({ children }) => <h3 className="msg-h3" style={{ color: "#ffffff", fontSize: "1rem", margin: "0.75rem 0 0.375rem", fontWeight: 600 }}>{children}</h3>,
                ul:         ({ children }) => <ul className="msg-ul" style={{ margin: "0.5rem 0 0.875rem", paddingLeft: "1.25rem", display: "flex", flexDirection: "column", gap: "0.35rem" }}>{children}</ul>,
                ol:         ({ children }) => <ol className="msg-ol" style={{ margin: "0.5rem 0 0.875rem", paddingLeft: "1.25rem", display: "flex", flexDirection: "column", gap: "0.35rem" }}>{children}</ol>,
                li:         ({ children }) => <li className="msg-li" style={{ marginBottom: "0.2rem", lineHeight: 1.65, color: "#e2e8f0" }}>{children}</li>,
                hr:         () => <hr className="msg-hr" style={{ border: "none", borderTop: "1px solid rgba(255,255,255,0.12)", margin: "1rem 0" }} />,
                code:       ({ children }) => <code className="msg-code" style={{ background: "rgba(255,255,255,0.08)", padding: "0.15rem 0.4rem", borderRadius: "0.25rem", fontSize: "0.875em", color: "#f1f5f9" }}>{children}</code>,
                blockquote: ({ children }) => <blockquote className="msg-blockquote" style={{ borderLeft: "3px solid #a855f7", margin: "0.75rem 0", paddingLeft: "0.875rem", fontStyle: "italic", color: "#cbd5e1" }}>{children}</blockquote>,
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
    <div className="msg-user-row fade-up" style={{ display: "flex", justifyContent: "flex-end", marginBottom: "1.5rem" }}>
      <div className="msg-user" style={{
        background: "#2f2f2f",
        border: "1px solid rgba(255, 255, 255, 0.12)",
        borderRadius: "1.25rem",
        padding: "0.75rem 1.125rem",
        maxWidth: "75%",
        color: "#ffffff",
        fontSize: "0.95rem",
        lineHeight: 1.5,
        wordBreak: "break-word",
        boxShadow: "0 2px 8px rgba(0,0,0,0.2)"
      }}>
        {message}
      </div>
    </div>
  );
}
