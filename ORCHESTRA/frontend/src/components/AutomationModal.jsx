import React, { useState, useEffect } from 'react';
import { LuTriangleAlert } from "react-icons/lu";

export default function AutomationModal({ isOpen, eventData, onSubmit, onAction }) {
  const [inputValue, setInputValue]           = useState("");
  const [captchaSrc, setCaptchaSrc]           = useState("");
  const [multiInputValues, setMultiInputValues] = useState({});
  const [refreshing, setRefreshing]           = useState(false);
  const [otpSending, setOtpSending]           = useState(false);

  useEffect(() => {
    setInputValue("");
    setMultiInputValues({});
    setRefreshing(false);

    if (eventData?.type === 'REQUEST_CAPTCHA') {
      if (eventData.image) {
        setCaptchaSrc(eventData.image);
      } else {
        fetch(`${import.meta.env.VITE_API_BASE}/automation/captcha-b64?t=${Date.now()}`)
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

  // Update captcha image when backend sends a refreshed one
  useEffect(() => {
    if (eventData?.type === 'REQUEST_CAPTCHA' && eventData.image) {
      setCaptchaSrc(eventData.image);
      setRefreshing(false);
    }
  }, [eventData?.image]);

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

  const handleRefreshCaptcha = () => {
    setRefreshing(true);
    setInputValue("");
    onAction && onAction({ type: "REFRESH_CAPTCHA" });
  };

  const handleGenerateOtp = () => {
    setOtpSending(true);
    onAction && onAction({ type: "GENERATE_OTP" });
    setTimeout(() => setOtpSending(false), 2500);
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

        {/* Captcha image + refresh */}
        {eventData.type === 'REQUEST_CAPTCHA' && (
          <div style={{ marginBottom: "1.25rem" }}>
            <div style={{ background: "var(--surface-2)", padding: "0.875rem", borderRadius: "var(--radius-md)", textAlign: "center", border: "1px solid var(--border)", marginBottom: "0.625rem" }}>
              {captchaSrc
                ? <img src={captchaSrc} alt="Captcha" style={{ maxWidth: "100%", height: "auto", borderRadius: "var(--radius-sm)", opacity: refreshing ? 0.4 : 1, transition: "opacity 0.2s" }} />
                : <p style={{ color: "var(--text-3)", fontSize: "0.75rem", margin: 0 }}>Loading captcha...</p>
              }
            </div>
            <button
              type="button"
              onClick={handleRefreshCaptcha}
              disabled={refreshing}
              style={{ width: "100%", padding: "0.5rem", borderRadius: "var(--radius-md)", border: "1.5px solid var(--border)", background: "var(--surface-2)", color: "var(--text-2)", fontSize: "0.8rem", cursor: refreshing ? "not-allowed" : "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "0.375rem" }}
            >
              <span style={{ display: "inline-block", animation: refreshing ? "spin 0.8s linear infinite" : "none" }}>↻</span>
              {refreshing ? "Loading new captcha…" : "Refresh Captcha"}
            </button>
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
            {/* Generate OTP button — only shown for OTP prompt */}
            {eventData.type === 'REQUEST_OTP' && (
              <button
                type="button"
                onClick={handleGenerateOtp}
                disabled={otpSending}
                style={{
                  width: "100%", padding: "0.6rem", borderRadius: "var(--radius-md)",
                  border: `1.5px solid var(--accent)`,
                  background: otpSending ? "var(--accent)" : "transparent",
                  color: otpSending ? "#fff" : "var(--accent)",
                  fontSize: "0.8rem", fontWeight: 600,
                  cursor: otpSending ? "not-allowed" : "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center", gap: "0.4rem",
                  transition: "background 0.2s, color 0.2s",
                }}
              >
                <span style={{ display: "inline-block", animation: otpSending ? "spin 0.8s linear infinite" : "none", fontSize: "1rem" }}>⟳</span>
                {otpSending ? "Sending OTP…" : "Generate OTP"}
              </button>
            )}
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
