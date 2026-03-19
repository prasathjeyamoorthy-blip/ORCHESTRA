import { useState } from "react";
import { LuPlus, LuMic, LuSquare } from "react-icons/lu";
import { RiSparkling2Fill } from "react-icons/ri";

export default function ChatInput({ onSend, disabled, isGenerating, onStop }) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (isGenerating) { onStop?.(); return; }
    if (disabled || !input.trim()) return;
    onSend(input);
    setInput("");
  };

  return (
    <div className="input-bar-wrap">
      <div className="input-bar-inner">
        <div className="input-bar">
          <button className="input-icon-btn" aria-label="Attach" tabIndex={-1}>
            <LuPlus size={18} />
          </button>
          <input
            type="text"
            placeholder="Ask anything"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && handleSend()}
            disabled={disabled && !isGenerating}
          />
          <div className="input-right">
            <button className="input-icon-btn" aria-label="Voice" tabIndex={-1}>
              <LuMic size={17} />
            </button>
            <button
              className={`input-send-btn ${isGenerating ? "stop" : ""}`}
              onClick={handleSend}
              disabled={!isGenerating && (disabled || !input.trim())}
              aria-label="Send"
            >
              {isGenerating
                ? <LuSquare size={14} fill="currentColor" />
                : <RiSparkling2Fill size={16} />
              }
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
