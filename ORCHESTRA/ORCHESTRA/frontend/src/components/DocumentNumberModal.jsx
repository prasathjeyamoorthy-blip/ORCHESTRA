import { useState } from "react";

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
    <div style={{
      position: "fixed",
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: "rgba(0, 0, 0, 0.7)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 9999,
    }}>
      <div style={{
        backgroundColor: "#fff",
        borderRadius: "12px",
        padding: "30px",
        maxWidth: "450px",
        width: "90%",
        boxShadow: "0 10px 40px rgba(0,0,0,0.3)",
      }}>
        <h2 style={{ marginTop: 0, color: "#b8860b", fontSize: "22px" }}>
          📋 Document Number Required
        </h2>
        
        <p style={{ color: "#555", lineHeight: "1.6", marginBottom: "20px" }}>
          Please enter the Document Number for your Current Address Proof (e.g., Aadhaar number):
        </p>

        <input
          type="text"
          value={documentNumber}
          onChange={(e) => setDocumentNumber(e.target.value)}
          placeholder="Enter document number"
          maxLength={20}
          style={{
            width: "100%",
            padding: "12px",
            fontSize: "16px",
            border: "2px solid #ddd",
            borderRadius: "8px",
            marginBottom: "20px",
            boxSizing: "border-box",
          }}
          onKeyPress={(e) => {
            if (e.key === 'Enter') {
              handleSubmit();
            }
          }}
        />

        <button
          onClick={handleSubmit}
          style={{
            width: "100%",
            padding: "12px",
            backgroundColor: "#b8860b",
            color: "white",
            border: "none",
            borderRadius: "8px",
            fontSize: "16px",
            fontWeight: "600",
            cursor: "pointer",
          }}
        >
          Submit
        </button>
      </div>
    </div>
  );
}
