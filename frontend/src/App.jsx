import { useEffect, useState } from "react";
import AgentStatus from "./components/AgentStatus";
import ChatBubble from "./components/ChatBubble";
import ChatInput from "./components/ChatInput";
import { sendMessage } from "./api/chatApi";
import "./index.css";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());

  useEffect(() => {
  window.scrollTo(0, 0);

  setMessages([
    {
      sender: "agent",
      text:
        "Welcome to the Official TNeGA e-Sevai Assistant. I can guide you step-by-step to obtain a Residence Certificate. How may I help you?",
    },
  ]);
}, []);


  const handleSend = async (text) => {
    setMessages((prev) => [...prev, { sender: "user", text }]);
    setLoading(true);

    try {
      const response = await sendMessage(sessionId, text);

      setMessages((prev) => [
        ...prev,
        {
          sender: "agent",
          text: response.answer || "Please provide more details.",
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          sender: "agent",
          text:
            "The service is temporarily unavailable. Please try again later.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>ORCHESTRA – TNeGA AI</h1>
        <p>Official e-Sevai Residence Certificate Assistant</p>
        <AgentStatus />
      </header>

      <main className="chat-container">
        {messages.map((msg, idx) => (
          <ChatBubble
            key={idx}
            sender={msg.sender}
            message={msg.text}
          />
        ))}

        {loading && (
          <div className="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        )}
      </main>

      <ChatInput onSend={handleSend} disabled={loading} />
    </div>
  );
}
