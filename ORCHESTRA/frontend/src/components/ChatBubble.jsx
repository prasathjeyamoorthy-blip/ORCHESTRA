import ReactMarkdown from "react-markdown";

export default function ChatBubble({ sender, message }) {
  const isBot = sender === "agent";

  if (isBot) {
    return (
      <div className="msg-bot fade-up">
        <ReactMarkdown
          components={{
            p:          ({ children }) => <p className="msg-p">{children}</p>,
            strong:     ({ children }) => <strong className="msg-strong">{children}</strong>,
            em:         ({ children }) => <em className="msg-em">{children}</em>,
            h1:         ({ children }) => <h2 className="msg-h2">{children}</h2>,
            h2:         ({ children }) => <h2 className="msg-h2">{children}</h2>,
            h3:         ({ children }) => <h3 className="msg-h3">{children}</h3>,
            ul:         ({ children }) => <ul className="msg-ul">{children}</ul>,
            ol:         ({ children }) => <ol className="msg-ol">{children}</ol>,
            li:         ({ children }) => <li className="msg-li">{children}</li>,
            hr:         () => <hr className="msg-hr" />,
            code:       ({ children }) => <code className="msg-code">{children}</code>,
            blockquote: ({ children }) => <blockquote className="msg-blockquote">{children}</blockquote>,
          }}
        >
          {message}
        </ReactMarkdown>
      </div>
    );
  }

  return (
    <div className="msg-user-row fade-up">
      <div className="msg-user">{message}</div>
    </div>
  );
}
