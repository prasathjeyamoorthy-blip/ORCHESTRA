import { useEffect, useState } from "react";
import AgentStatus from "./components/AgentStatus";
import ChatBubble from "./components/ChatBubble";
import ChatInput from "./components/ChatInput";
import DocumentChecklist from "./components/DocumentChecklist";
import { sendMessage } from "./api/chatApi";
import "./index.css";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());

  const [showChecklist, setShowChecklist] = useState(false);
  const [waitingForDocumentResponse, setWaitingForDocumentResponse] =
    useState(false);
  const [isChecklistProceeding, setIsChecklistProceeding] = useState(false);

  useEffect(() => {
    window.scrollTo(0, 0);

    setMessages([
      {
        sender: "agent",
        text: "Welcome to the Official TNeGA e-Sevai Assistant. I can guide you step-by-step to obtain a Residence Certificate. How may I help you?",
      },
    ]);
  }, []);

  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.sender === "agent") {
        const text = lastMessage.text.toLowerCase();
        // Specifically check if the text ends with the exact question
        // added in the backend agent.py.
        if (text.includes("are you ready to submit the documents")) {
          setWaitingForDocumentResponse(true);
        } else {
          setWaitingForDocumentResponse(false);
        }
      } else {
        setWaitingForDocumentResponse(false);
      }
    }
  }, [messages]);

  const handleQuickReply = async (reply) => {
    setWaitingForDocumentResponse(false);
    setMessages((prev) => [...prev, { sender: "user", text: reply }]);

    if (reply === "Yes") {
      setShowChecklist(true);
      return; // Stop here, don't generate bot response while checklist is open
    } else {
      setShowChecklist(false);
    }

    setIsGenerating(true);
    try {
      const response = await sendMessage(sessionId, reply);
      setMessages((prev) => [
        ...prev,
        {
          sender: "agent",
          text: response.answer || "Please provide more details.",
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "agent",
          text: "The service is temporarily unavailable. Please try again later.",
        },
      ]);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleChecklistProceed = async () => {
    setIsChecklistProceeding(true);

    // Simulate slight loading delay for processing
    await new Promise((resolve) => setTimeout(resolve, 1500));

    setIsChecklistProceeding(false);
    setShowChecklist(false);

    // After checklist concludes, push bot confirmation:
    setMessages((prev) => [
      ...prev,
      {
        sender: "agent",
        text: "Thank you for submitting the documents.",
      },
    ]);
  };

  const handleChecklistExit = () => {
    setShowChecklist(false);
  };

  const handleSend = async (text) => {
    if (!text.trim()) return;

    const lowerText = text.toLowerCase();

    // Check if user explicitly wants to submit/view submitted documents
    // Broadening the match: if "submit" and "document" appear anywhere in the logic.
    const wantsToSubmit =
      lowerText.includes("submit") && lowerText.includes("document");

    // Add user message
    setMessages((prev) => [...prev, { sender: "user", text }]);

    if (wantsToSubmit) {
      setShowChecklist(true);
      setWaitingForDocumentResponse(false);
      return; // Stop here, don't generate bot response while checklist is open
    }

    setShowChecklist(false); // Reset checklist state on new normal manual message
    setWaitingForDocumentResponse(false);

    setIsGenerating(true);

    try {
      const response = await sendMessage(sessionId, text);

      setMessages((prev) => [
        ...prev,
        {
          sender: "agent",
          text: response.answer || "Please provide more details.",
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "agent",
          text: "The service is temporarily unavailable. Please try again later.",
        },
      ]);
    } finally {
      setIsGenerating(false); // 🔥 This controls pause button correctly
    }
  };

  const handleStop = () => {
    if (window.stopAgent) {
      window.stopAgent();
    }
    setIsGenerating(false);
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
          <ChatBubble key={idx} sender={msg.sender} message={msg.text} />
        ))}

        {waitingForDocumentResponse && (
          <div className="quick-replies">
            <button
              className="quick-reply-btn"
              onClick={() => handleQuickReply("Yes")}
            >
              Yes
            </button>
            <button
              className="quick-reply-btn"
              onClick={() => handleQuickReply("No")}
            >
              No
            </button>
          </div>
        )}

        {showChecklist && (
          <DocumentChecklist
            onProceed={handleChecklistProceed}
            onExit={handleChecklistExit}
            isProceeding={isChecklistProceeding}
          />
        )}

        {isGenerating && (
          <div className="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        )}
      </main>

      <ChatInput
        onSend={handleSend}
        disabled={isGenerating || showChecklist}
        isGenerating={isGenerating}
        onStop={handleStop}
      />
    </div>
  );
}
