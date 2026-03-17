import { useState } from "react";
import { LuFileText } from "react-icons/lu";

export default function DocumentNumberModal({ isOpen, onSubmit }) {
  const [documentNumber, setDocumentNumber] = useState("");

  if (!isOpen) return null;

  const handleSubmit = () => {
    if (!documentNumber.trim()) {
      alert("Please enter the document number!");
      return;
    }
    onSubmit(documentNumber.trim());
  };

  return (
    <div className="overlay">
      <div className="modal-card">
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: "2rem", height: "2rem", borderRadius: "0.5rem", backgroundColor: "hsl(var(--primary)/0.1)", color: "hsl(var(--primary))" }}>
            <LuFileText size={20} />
          </div>
          <h2 style={{ fontSize: "1.125rem", fontWeight: 700, margin: 0 }}>Document Number Required</h2>
        </div>
        
        <p style={{ fontSize: "0.875rem", color: "hsl(var(--muted-foreground))", marginBottom: "1.5rem" }}>
          Please enter the Document Number for your Current Address Proof (e.g., Aadhaar number):
        </p>

        <input
          type="text"
          value={documentNumber}
          onChange={(e) => setDocumentNumber(e.target.value)}
          placeholder="Enter document number"
          maxLength={20}
          style={{ width: "100%", padding: "0.75rem", borderRadius: "0.75rem", border: "1px solid hsl(var(--border))", backgroundColor: "transparent", fontSize: "0.875rem", color: "hsl(var(--foreground))", outline: "none", boxSizing: "border-box", marginBottom: "1.5rem" }}
          onKeyPress={(e) => {
            if (e.key === 'Enter') {
              handleSubmit();
            }
          }}
          autoFocus
        />

        <button onClick={handleSubmit} className="btn-primary" style={{ width: "100%" }}>
          Submit
        </button>
      </div>
    </div>
  );
}
