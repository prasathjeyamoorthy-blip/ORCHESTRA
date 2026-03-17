import { useRef, useState } from "react";

export default function AgentStatus({ onChunk }) {
  const abortRef = useRef(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const startAgent = async (message) => {
    abortRef.current = new AbortController();
    setIsGenerating(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
        signal: abortRef.current.signal
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        onChunk(decoder.decode(value));
      }
    } catch (err) {
      if (err.name !== "AbortError") {
        console.error(err);
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const stopAgent = () => {
    abortRef.current?.abort();
    setIsGenerating(false);
  };

  return (
    <div className="agent-status">
      <span className={`status-dot ${isGenerating ? "active" : ""}`}></span>
      <span className="status-text">
        {isGenerating ? "AI Generating…" : "AI Agent Online"}
      </span>

      {/* expose functions */}
      {typeof window !== "undefined" && (
        (window.startAgent = startAgent),
        (window.stopAgent = stopAgent)
      )}
    </div>
  );
}
