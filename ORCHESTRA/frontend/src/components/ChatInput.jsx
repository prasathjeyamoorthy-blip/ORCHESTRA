import { useState } from "react";
import DocumentUpload from "./DocumentUpload";

export default function ChatInput({ onSend, disabled, isGenerating, onStop }) {
  const [input, setInput] = useState("");
  const [fileName, setFileName] = useState(null);

  const handleSend = () => {
    // ⏸ If generating → stop
    if (isGenerating) {
      if (onStop) {
        onStop();
      }
      return;
    }

    if (disabled) return;

    // ▶ Normal send
    if (!input.trim()) return;

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

        <input
          type="text"
          placeholder="Ask about residence certificate..."
          value={input}
          disabled={disabled}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
        />

        <button onClick={handleSend} disabled={disabled && !isGenerating}>
          {isGenerating ? "⏸" : "Send"}
        </button>
      </div>

      {fileName && <div className="file-preview">📄 {fileName}</div>}
    </div>
  );
}
