import React, { useState, useEffect, useRef } from "react";
import { sendOtpApi, verifyOtpApi } from "../api/chatApi";

export default function OtpModal({ isOpen, onClose, onSuccess }) {
  const [step, setStep] = useState("phone"); // "phone" | "otp" | "pin"
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState(["", "", "", ""]);
  const [pin, setPin] = useState(["", "", "", "", "", ""]);
  const [verificationId, setVerificationId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [timer, setTimer] = useState(30);
  const [canResend, setCanResend] = useState(false);
  const otpInputRefs = useRef([]);
  const pinInputRefs = useRef([]);

  useEffect(() => {
    let interval;
    if (step === "otp" && timer > 0) {
      interval = setInterval(() => {
        setTimer((prev) => prev - 1);
      }, 1000);
    } else if (timer === 0) {
      setCanResend(true);
    }
    return () => clearInterval(interval);
  }, [step, timer]);

  if (!isOpen) return null;

  const handlePhoneChange = (e) => {
    const val = e.target.value.replace(/\D/g, "").slice(0, 10);
    setPhone(val);
    setError("");
  };

  const handleSendOtp = async (e) => {
    if (e) e.preventDefault();
    if (phone.length < 10) {
      setError("Please enter a valid 10-digit Indian mobile number.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await sendOtpApi(phone);
      setVerificationId(res.verification_id || "");
      setStep("otp");
      setTimer(30);
      setCanResend(false);
      setTimeout(() => {
        if (otpInputRefs.current[0]) otpInputRefs.current[0].focus();
      }, 100);
    } catch (err) {
      setError(err.message || "Failed to send OTP. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleOtpChange = (index, value) => {
    const val = value.replace(/\D/g, "");
    if (!val && value !== "") return;

    const newOtp = [...otp];
    newOtp[index] = val.slice(-1);
    setOtp(newOtp);
    setError("");

    if (val && index < 3) {
      otpInputRefs.current[index + 1]?.focus();
    }
  };

  const handlePinChange = (index, value) => {
    const val = value.replace(/\D/g, "");
    if (!val && value !== "") return;

    const newPin = [...pin];
    newPin[index] = val.slice(-1);
    setPin(newPin);
    setError("");

    if (val && index < 5) {
      pinInputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index, e, isPin = false) => {
    const refs = isPin ? pinInputRefs : otpInputRefs;
    const arr = isPin ? pin : otp;
    if (e.key === "Backspace" && !arr[index] && index > 0) {
      refs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e, isPin = false) => {
    e.preventDefault();
    const len = isPin ? 6 : 4;
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, len);
    if (pasted.length === len) {
      const digits = pasted.split("");
      if (isPin) {
        setPin(digits);
        pinInputRefs.current[5]?.focus();
      } else {
        setOtp(digits);
        otpInputRefs.current[3]?.focus();
      }
    }
  };

  const handleVerifyOtp = async (e) => {
    if (e) e.preventDefault();
    const code = otp.join("");
    if (code.length < 4) {
      setError("Please enter the complete 4-digit OTP code.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await verifyOtpApi(phone, code, verificationId);
      if (res.success) {
        sessionStorage.setItem("user_phone", phone);
        setStep("pin");
        setTimeout(() => {
          if (pinInputRefs.current[0]) pinInputRefs.current[0].focus();
        }, 100);
      } else {
        setError(res.message || "Invalid OTP code.");
      }
    } catch (err) {
      setError(err.message || "OTP verification failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleSavePin = async (e) => {
    if (e) e.preventDefault();
    const pinCode = pin.join("");
    if (pinCode.length < 6) {
      setError("Please enter a complete 6-digit Security Encryption PIN.");
      return;
    }

    try {
      const { setUserPin } = await import("../utils/crypto");
      setUserPin(phone, pinCode);
      onSuccess(phone);
    } catch (err) {
      setError("Failed to initialize security key.");
    }
  };

  const handleResend = () => {
    if (!canResend) return;
    setOtp(["", "", "", ""]);
    handleSendOtp();
  };

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 1000,
      display: "flex", alignItems: "center", justifyContent: "center",
      background: "rgba(2, 6, 23, 0.75)",
      backdropFilter: "blur(24px) saturate(180%)",
      WebkitBackdropFilter: "blur(24px) saturate(180%)",
      padding: "1.25rem"
    }}>
      {/* Ultra Glassmorphic Container */}
      <div style={{
        width: "100%", maxWidth: "440px",
        background: "linear-gradient(135deg, rgba(255, 255, 255, 0.07), rgba(255, 255, 255, 0.02))",
        backdropFilter: "blur(30px) saturate(190%)",
        WebkitBackdropFilter: "blur(30px) saturate(190%)",
        border: "1px solid rgba(255, 255, 255, 0.15)",
        borderRadius: "28px", padding: "2.5rem 2.25rem",
        boxShadow: "0 30px 60px -12px rgba(0, 0, 0, 0.75), inset 0 1px 0 rgba(255, 255, 255, 0.25), 0 0 50px rgba(168, 85, 247, 0.15)",
        color: "#f8fafc", fontFamily: "'Plus Jakarta Sans', sans-serif"
      }}>
        {/* Glass Tag Pill */}
        <div style={{ display: "flex", justifyContent: "center", marginBottom: "1.5rem" }}>
          <span style={{
            fontSize: "0.7rem", fontWeight: "700", letterSpacing: "0.15em",
            textTransform: "uppercase", color: "#c084fc",
            padding: "0.35rem 0.9rem", borderRadius: "9999px",
            background: "rgba(168, 85, 247, 0.12)",
            border: "1px solid rgba(168, 85, 247, 0.3)",
            boxShadow: "0 0 15px rgba(168, 85, 247, 0.2)",
            backdropFilter: "blur(8px)"
          }}>
            {step === "pin" ? "ZERO-KNOWLEDGE ENCRYPTION" : "SECURITY VERIFICATION"}
          </span>
        </div>

        {/* Title & Description */}
        <div style={{ textAlign: "center", marginBottom: "1.75rem" }}>
          <h2 style={{ fontSize: "1.5rem", fontWeight: "800", margin: "0 0 0.5rem 0", color: "#ffffff", letterSpacing: "-0.02em" }}>
            {step === "phone" ? "Mobile Verification" : step === "otp" ? "Verification Code" : "Set 6-Digit Security PIN"}
          </h2>
          <p style={{ fontSize: "0.875rem", color: "rgba(226, 232, 240, 0.7)", margin: 0, lineHeight: 1.5, fontWeight: "400" }}>
            {step === "phone"
              ? "Please enter your 10-digit mobile number to receive an OTP via Message Central."
              : step === "otp"
              ? `Enter the 4-digit code sent to +91 ${phone}`
              : "Enter a 6-digit Security PIN. This PIN encrypts your chats & document uploads so only you can unlock them."}
          </p>
        </div>

        {/* Error Glass Pill */}
        {error && (
          <div style={{
            padding: "0.8rem 1rem", borderRadius: "14px",
            background: "rgba(239, 68, 68, 0.12)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            color: "#fca5a5", fontSize: "0.85rem", fontWeight: "500",
            marginBottom: "1.25rem", textAlign: "center",
            backdropFilter: "blur(10px)"
          }}>
            {error}
          </div>
        )}

        {/* Step 1: Phone Input Form */}
        {step === "phone" && (
          <form onSubmit={handleSendOtp} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.75rem", fontWeight: "700", color: "rgba(226, 232, 240, 0.7)", marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Mobile Number
              </label>
              <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
                <span style={{
                  position: "absolute", left: "16px",
                  color: "rgba(255, 255, 255, 0.9)", fontWeight: "700", fontSize: "0.95rem",
                  letterSpacing: "0.02em"
                }}>
                  +91
                </span>
                <input
                  type="tel"
                  value={phone}
                  onChange={handlePhoneChange}
                  placeholder="98765 43210"
                  maxLength={10}
                  autoFocus
                  style={{
                    width: "100%", padding: "0.9rem 1rem 0.9rem 4rem",
                    background: "rgba(255, 255, 255, 0.05)",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    borderRadius: "16px", color: "#ffffff", fontSize: "1.05rem", fontWeight: "600",
                    letterSpacing: "0.08em", outline: "none", transition: "all 0.25s ease",
                    backdropFilter: "blur(10px)",
                    boxShadow: "inset 0 2px 4px rgba(0, 0, 0, 0.3)"
                  }}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || phone.length < 10}
              style={{
                width: "100%", padding: "0.95rem",
                borderRadius: "16px", border: "none",
                background: phone.length === 10
                  ? "linear-gradient(135deg, rgba(147, 51, 234, 0.9), rgba(79, 70, 229, 0.9))"
                  : "rgba(255, 255, 255, 0.08)",
                backdropFilter: "blur(10px)",
                color: phone.length === 10 ? "#ffffff" : "rgba(255, 255, 255, 0.35)",
                fontWeight: "700", fontSize: "0.95rem", letterSpacing: "0.02em",
                cursor: phone.length === 10 && !loading ? "pointer" : "not-allowed",
                boxShadow: phone.length === 10 ? "0 10px 25px -5px rgba(147, 51, 234, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.3)" : "none",
                transition: "all 0.3s ease"
              }}
            >
              {loading ? "Sending OTP..." : "Send OTP"}
            </button>
          </form>
        )}

        {/* Step 2: OTP Verification Form */}
        {step === "otp" && (
          <form onSubmit={handleVerifyOtp} style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            <div>
              <div style={{ display: "flex", justifyContent: "center", gap: "14px" }}>
                {otp.map((digit, idx) => (
                  <input
                    key={idx}
                    ref={(el) => (otpInputRefs.current[idx] = el)}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleOtpChange(idx, e.target.value)}
                    onKeyDown={(e) => handleKeyDown(idx, e, false)}
                    onPaste={(e) => handlePaste(e, false)}
                    style={{
                      width: "68px", height: "64px",
                      textAlign: "center", fontSize: "1.6rem", fontWeight: "700",
                      background: digit ? "rgba(168, 85, 247, 0.12)" : "rgba(255, 255, 255, 0.05)",
                      border: digit ? "1.5px solid rgba(168, 85, 247, 0.8)" : "1px solid rgba(255, 255, 255, 0.15)",
                      borderRadius: "16px", color: "#ffffff", outline: "none",
                      backdropFilter: "blur(10px)",
                      boxShadow: digit ? "0 0 18px rgba(168, 85, 247, 0.35)" : "inset 0 2px 4px rgba(0, 0, 0, 0.3)",
                      transition: "all 0.25s ease"
                    }}
                  />
                ))}
              </div>
            </div>

            {/* Timer & Edit Number Controls */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "0.85rem", color: "rgba(226, 232, 240, 0.7)" }}>
              <button
                type="button"
                onClick={() => { setStep("phone"); setError(""); }}
                style={{
                  background: "none", border: "none", color: "rgba(255, 255, 255, 0.7)",
                  cursor: "pointer", fontSize: "0.85rem", fontWeight: "500"
                }}
              >
                Edit Number
              </button>

              {canResend ? (
                <button
                  type="button"
                  onClick={handleResend}
                  style={{ background: "none", border: "none", color: "#c084fc", fontWeight: "700", cursor: "pointer" }}
                >
                  Resend OTP
                </button>
              ) : (
                <span style={{ fontSize: "0.825rem", color: "rgba(255, 255, 255, 0.5)" }}>Resend in {timer}s</span>
              )}
            </div>

            <button
              type="submit"
              disabled={loading || otp.join("").length < 4}
              style={{
                width: "100%", padding: "0.95rem",
                borderRadius: "16px", border: "none",
                background: otp.join("").length === 4
                  ? "linear-gradient(135deg, rgba(168, 85, 247, 0.9), rgba(236, 72, 153, 0.9))"
                  : "rgba(255, 255, 255, 0.08)",
                backdropFilter: "blur(10px)",
                color: otp.join("").length === 4 ? "#ffffff" : "rgba(255, 255, 255, 0.35)",
                fontWeight: "700", fontSize: "0.95rem", letterSpacing: "0.02em",
                cursor: otp.join("").length === 4 && !loading ? "pointer" : "not-allowed",
                boxShadow: otp.join("").length === 4 ? "0 10px 25px -5px rgba(168, 85, 247, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.3)" : "none",
                transition: "all 0.3s ease"
              }}
            >
              {loading ? "Verifying..." : "Verify OTP"}
            </button>
          </form>
        )}

        {/* Step 3: 6-Digit Security PIN Form */}
        {step === "pin" && (
          <form onSubmit={handleSavePin} style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            <div>
              <div style={{ display: "flex", justifyContent: "center", gap: "8px" }}>
                {pin.map((digit, idx) => (
                  <input
                    key={idx}
                    ref={(el) => (pinInputRefs.current[idx] = el)}
                    type="password"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handlePinChange(idx, e.target.value)}
                    onKeyDown={(e) => handleKeyDown(idx, e, true)}
                    onPaste={(e) => handlePaste(e, true)}
                    style={{
                      width: "48px", height: "54px",
                      textAlign: "center", fontSize: "1.5rem", fontWeight: "700",
                      background: digit ? "rgba(52, 211, 153, 0.12)" : "rgba(255, 255, 255, 0.05)",
                      border: digit ? "1.5px solid rgba(52, 211, 153, 0.8)" : "1px solid rgba(255, 255, 255, 0.15)",
                      borderRadius: "14px", color: "#ffffff", outline: "none",
                      backdropFilter: "blur(10px)",
                      boxShadow: digit ? "0 0 16px rgba(52, 211, 153, 0.35)" : "inset 0 2px 4px rgba(0, 0, 0, 0.3)",
                      transition: "all 0.25s ease"
                    }}
                  />
                ))}
              </div>
            </div>



            <button
              type="submit"
              disabled={pin.join("").length < 6}
              style={{
                width: "100%", padding: "0.95rem",
                borderRadius: "16px", border: "none",
                background: pin.join("").length === 6
                  ? "linear-gradient(135deg, rgba(16, 185, 129, 0.9), rgba(5, 150, 105, 0.9))"
                  : "rgba(255, 255, 255, 0.08)",
                backdropFilter: "blur(10px)",
                color: pin.join("").length === 6 ? "#ffffff" : "rgba(255, 255, 255, 0.35)",
                fontWeight: "700", fontSize: "0.95rem", letterSpacing: "0.02em",
                cursor: pin.join("").length === 6 ? "pointer" : "not-allowed",
                boxShadow: pin.join("").length === 6 ? "0 10px 25px -5px rgba(16, 185, 129, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.3)" : "none",
                transition: "all 0.3s ease"
              }}
            >
              Lock &amp; Start Session
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
