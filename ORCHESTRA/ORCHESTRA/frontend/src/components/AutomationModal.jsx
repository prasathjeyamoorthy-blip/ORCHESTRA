import React, { useState, useEffect } from 'react';
import { LuTriangleAlert } from "react-icons/lu";

export default function AutomationModal({ isOpen, eventData, onSubmit }) {
  const [inputValue, setInputValue]           = useState("");
  const [captchaSrc, setCaptchaSrc]           = useState("");
  const [multiInputValues, setMultiInputValues] = useState({});

  useEffect(() => {
    setInputValue("");
    setMultiInputValues({});
    setCaptchaSrc("");

    if (eventData?.type === 'REQUEST_CAPTCHA') {
      if (eventData.image) {
        setCaptchaSrc(eventData.image);
      } else {
        fetch(`http://localhost:8000/automation/captcha-b64?t=${Date.now()}`)
          .then(r => r.json())
          .then(d => { if (d.image) setCaptchaSrc(d.image); })
          .catch(err => console.error("[Captcha] Failed to load:", err));
      }
    }

    if (eventData?.type === 'REQUEST_MISSING_DETAILS' && eventData.missing_fields) {
      const init = {};
      eventData.missing_fields.forEach(f => init[f] = "");
      setMultiInputValues(init);
    }
  }, [eventData]);

  if (!isOpen || !eventData) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (eventData.type === 'REQUEST_MISSING_DETAILS') {
      if (!Object.values(multiInputValues).every(v => v.trim())) return;
      onSubmit(multiInputValues);
    } else {
      if (!inputValue.trim()) return;
      onSubmit(inputValue);
    }
  };

  const inputStyle = {
    width: "100%",
    padding: "0.75rem 0.875rem",
    borderRadius: "var(--radius-md)",
    border: "1.5px solid var(--border)",
    background: "var(--surface-2)",
    fontSize: "0.875rem",
    color: "var(--text)",
    outline: "none",
    boxSizing: "border-box",
    fontFamily: "inherit",
    transition: "border-color 0.2s, box-shadow 0.2s",
  };

  return (
    <div className="overlay">
      <div className="modal-card">
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", marginBottom: "0.875rem" }}>
          <div className="modal-icon">
            <LuTriangleAlert size={18} />
          </div>
          <h2 className="modal-title">Action Required</h2>
        </div>

        <p className="modal-sub" style={{ marginBottom: "1.25rem" }}>{eventData.message}</p>

        {/* Captcha image */}
        {eventData.type === 'REQUEST_CAPTCHA' && (
          <div style={{ background: "var(--surface-2)", padding: "0.875rem", borderRadius: "var(--radius-md)", marginBottom: "1.25rem", textAlign: "center", border: "1px solid var(--border)" }}>
            {captchaSrc
              ? <img src={captchaSrc} alt="Captcha" style={{ maxWidth: "100%", height: "auto", borderRadius: "var(--radius-sm)" }} />
              : <p style={{ color: "var(--text-3)", fontSize: "0.75rem", margin: 0 }}>Loading captcha...</p>
            }
          </div>
        )}

        {/* Multi-field form */}
        {eventData.type === 'REQUEST_MISSING_DETAILS' ? (
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.875rem" }}>
            {eventData.missing_fields?.map((field, idx) => (
              <div key={idx} style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text)", textTransform: "capitalize" }}>
                  {field.replace(/_/g, ' ')}
                </label>
                <input
                  type="text"
                  value={multiInputValues[field] || ""}
                  onChange={e => setMultiInputValues(p => ({ ...p, [field]: e.target.value }))}
                  placeholder={`Enter ${field.replace(/_/g, ' ')}`}
                  style={inputStyle}
                  autoFocus={idx === 0}
                />
              </div>
            ))}
            <button type="submit" className="btn-primary" style={{ width: "100%", marginTop: "0.25rem" }}>Submit Details</button>
          </form>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.875rem" }}>
            <input
              type="text"
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              placeholder={
                eventData.type === 'REQUEST_CAPTCHA' ? "Enter captcha code" :
                eventData.type === 'REQUEST_OTP'     ? "Enter OTP" :
                eventData.type === 'REQUEST_RESUME'  ? "Type anything to continue..." :
                "Enter value"
              }
              style={inputStyle}
              autoFocus
            />
            <button type="submit" className="btn-primary" style={{ width: "100%" }}>
              {eventData.type === 'REQUEST_RESUME' ? "Continue" : "Submit"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
