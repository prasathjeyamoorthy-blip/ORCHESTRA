import React from 'react';
import { LuCreditCard, LuExternalLink, LuX, LuCircleCheck } from "react-icons/lu";

export default function PaymentModal({ isOpen, paymentUrl, onClose }) {
  if (!isOpen || !paymentUrl) return null;

  return (
    <div className="overlay" style={{ zIndex: 9999 }}>
      <div 
        className="modal-card" 
        style={{ 
          maxWidth: "min(950px, 96vw)", 
          width: "95%", 
          height: "85vh", 
          maxHeight: "92vh",
          display: "flex", 
          flexDirection: "column", 
          padding: 0, 
          overflow: "hidden",
          borderRadius: "var(--radius-lg)",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
          background: "var(--surface-1)"
        }}
      >
        {/* Header */}
        <div style={{
          padding: "1rem 1.25rem",
          background: "var(--surface-1)",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "0.75rem"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div className="modal-icon" style={{ background: "rgba(59, 130, 246, 0.12)", color: "#3b82f6" }}>
              <LuCreditCard size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 600, color: "var(--text)" }}>
                TNeSevai Payment Gateway
              </h3>
              <p style={{ margin: 0, fontSize: "0.75rem", color: "var(--text-3)" }}>
                Complete your application fee payment below to finalize submission
              </p>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <a
              href={paymentUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.375rem",
                padding: "0.4rem 0.75rem",
                fontSize: "0.8rem",
                textDecoration: "none",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border)",
                color: "var(--text)"
              }}
            >
              <LuExternalLink size={14} /> Open in New Tab
            </a>
            <button
              onClick={onClose}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--text-3)",
                cursor: "pointer",
                padding: "0.375rem",
                borderRadius: "var(--radius-md)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
              }}
              title="Close Payment Window"
            >
              <LuX size={20} />
            </button>
          </div>
        </div>

        {/* Payment URL Bar */}
        <div style={{
          padding: "0.5rem 1.25rem",
          background: "var(--surface-2)",
          borderBottom: "1px solid var(--border)",
          fontSize: "0.75rem",
          color: "var(--text-2)",
          display: "flex",
          alignItems: "center",
          gap: "0.5rem"
        }}>
          <span style={{ fontWeight: 600, color: "var(--text-3)" }}>Gateway URL:</span>
          <span style={{ 
            fontFamily: "monospace", 
            overflow: "hidden", 
            textOverflow: "ellipsis", 
            whiteSpace: "nowrap",
            color: "var(--accent)"
          }}>
            {paymentUrl}
          </span>
        </div>

        {/* Embedded Payment Website View */}
        <div style={{ flex: 1, width: "100%", position: "relative", background: "#fff" }}>
          <iframe
            src={paymentUrl}
            title="TNeSevai Payment Gateway"
            style={{
              width: "100%",
              height: "100%",
              border: "none"
            }}
            sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
          />
        </div>

        {/* Footer */}
        <div style={{
          padding: "0.75rem 1.25rem",
          background: "var(--surface-1)",
          borderTop: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between"
        }}>
          <span style={{ fontSize: "0.75rem", color: "var(--text-3)", display: "flex", alignItems: "center", gap: "0.375rem" }}>
            <LuCircleCheck size={14} color="#10b981" /> Application filled · Complete payment above
          </span>
          <button
            onClick={onClose}
            className="btn-primary"
            style={{ padding: "0.4rem 1rem", fontSize: "0.825rem" }}
          >
            Done / Close Payment Modal
          </button>
        </div>
      </div>
    </div>
  );
}
