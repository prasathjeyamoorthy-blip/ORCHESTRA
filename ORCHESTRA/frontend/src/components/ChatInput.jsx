import { useState } from "react";
import DocumentUpload from "./DocumentUpload";

export default function ChatInput({ onSend, disabled }) {
  const [input, setInput] = useState("");
  const [fileName, setFileName] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const handleSend = () => {
    // ⏸ Stop while generating
    if (isGenerating) {
      if (window.stopAgent) {
        window.stopAgent();
      }
      setIsGenerating(false);
      return;
    }

    // ▶ Normal send
    if (!input.trim() || disabled) return;

    setIsGenerating(true);
    onSend(input);
    setInput("");
  };

  const handleFileSelect = (file) => {
    setFileName(file.name);
    console.log("Selected file:", file);
  };

  return (
    <div className="chat-input-wrapper">
      <div className="chat-input-container">
        <DocumentUpload onFileSelect={handleFileSelect} />

        {/* Disable INPUT while generating */}
        <input
          type="text"
          placeholder="Ask about residence certificate..."
          value={input}
          disabled={disabled || isGenerating}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
        />

        {/* ❗ Button MUST stay clickable */}
        <button onClick={handleSend}>
          {isGenerating ? "⏸" : "Send"}
        </button>
      </div>

      {fileName && (
        <div className="file-preview">
          📄 {fileName}
        </div>
      )}
    </div>
  );
}
