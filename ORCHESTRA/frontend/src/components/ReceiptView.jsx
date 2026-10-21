import { useState } from "react";
import {
  LuFileBadge,
  LuReceiptIndianRupee,
  LuDownload,
  LuCircleCheck,
  LuSearch,
  LuFileText,
  LuFileCheck,
  LuRotateCcw,
} from "react-icons/lu";

export default function ReceiptView({ currentLanguage = "en" }) {
  const isTa = currentLanguage === "ta";

  const [appNo, setAppNo] = useState("");
  const [fetching, setFetching] = useState(false);
  const [certReady, setCertReady] = useState(false);
  const [fetchedAppNo, setFetchedAppNo] = useState("");

  const handleFetchCert = (e) => {
    e?.preventDefault();
    const cleanAppNo = appNo.trim();
    if (!cleanAppNo) return;

    setFetching(true);
    setCertReady(false);
    setFetchedAppNo(cleanAppNo);

    setTimeout(() => {
      setFetching(false);
      setCertReady(true);
    }, 3500);
  };

  const handleReset = () => {
    setCertReady(false);
    setAppNo("");
    setFetchedAppNo("");
  };

  return (
    <div className="view-page fade-up" style={{ maxWidth: "720px", margin: "0 auto" }}>
      {/* ── View Header ── */}
      <div className="view-header" style={{ marginBottom: "2rem" }}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem", padding: "0.35rem 0.85rem", borderRadius: "9999px", background: "rgba(34,197,94,0.12)", border: "1px solid rgba(34,197,94,0.3)", color: "#4ade80", fontSize: "0.8rem", fontWeight: 700, marginBottom: "0.85rem" }}>
          <LuCircleCheck size={14} /> {isTa ? "செயல்முறை முடிந்தது" : "Process Completed"}
        </div>
        <h2 className="view-title" style={{ fontSize: "1.75rem", display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <LuFileBadge size={28} style={{ color: "#a855f7" }} />
          {isTa ? "ரசீது & சான்றிதழ் பதிவிறக்கம்" : "Receipt & Certificate Downloads"}
        </h2>
        <p className="view-sub" style={{ fontSize: "0.925rem" }}>
          {isTa
            ? "உங்கள் விண்ணப்பக் கட்டண ரசீதைப் பதிவிறக்கவும் மற்றும் உங்கள் விண்ணப்ப எண்ணைக் கொடுத்து குடியிருப்புச் சான்றிதழைப் பெறவும்."
            : "Download your official payment receipt and retrieve your Residence Certificate using your Application Number."}
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>

        {/* ── SECTION 1: PAYMENT RECEIPT ── */}
        <div
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(99,102,241,0.25)",
            borderRadius: "1.25rem",
            padding: "1.5rem",
            backdropFilter: "blur(16px)",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              position: "absolute", top: 0, left: 0, right: 0, height: "3px",
              background: "linear-gradient(90deg, #6366f1, #8b5cf6, #a855f7)",
            }}
          />

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.25rem", flexWrap: "wrap", gap: "0.75rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <div style={{ width: "2.35rem", height: "2.35rem", borderRadius: "0.55rem", background: "rgba(99,102,241,0.18)", display: "flex", alignItems: "center", justifyContent: "center", color: "#818cf8", flexShrink: 0 }}>
                <LuReceiptIndianRupee size={20} />
              </div>
              <div>
                <span style={{ fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "rgba(255,255,255,0.45)", fontWeight: 700 }}>
                  {isTa ? "பகுதி 1: கட்டண ரசீது" : "Section 1: Payment Receipt"}
                </span>
                <h3 style={{ margin: "0.15rem 0 0", color: "#fff", fontSize: "1.15rem", fontWeight: 700 }}>
                  {isTa ? "அரசு இ-சேவை கட்டண ரசீது" : "Official e-Sevai Payment Receipt"}
                </h3>
              </div>
            </div>
            <span
              style={{
                display: "inline-flex", alignItems: "center", gap: "0.35rem",
                padding: "0.3rem 0.75rem", borderRadius: "9999px",
                background: "rgba(34,197,94,0.15)", color: "#4ade80",
                fontSize: "0.78rem", fontWeight: 600,
              }}
            >
              <LuCircleCheck size={13} /> {isTa ? "கட்டணம் செலுத்தப்பட்டது" : "Payment Complete"}
            </span>
          </div>

          <div
            style={{
              display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "0.75rem",
              background: "rgba(0,0,0,0.25)", borderRadius: "0.75rem", padding: "0.85rem 1rem", marginBottom: "1.25rem",
            }}
          >
            <div>
              <span style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", display: "block" }}>
                {isTa ? "சேவை" : "Service"}
              </span>
              <strong style={{ fontSize: "0.88rem", color: "#fff" }}>
                {isTa ? "குடியிருப்புச் சான்றிதழ்" : "Residence Certificate"}
              </strong>
            </div>
            <div>
              <span style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", display: "block" }}>
                {isTa ? "கட்டணத் தொகை" : "Amount Paid"}
              </span>
              <strong style={{ fontSize: "0.88rem", color: "#4ade80" }}>₹60.00</strong>
            </div>
            <div>
              <span style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", display: "block" }}>
                {isTa ? "வகை" : "Document Type"}
              </span>
              <strong style={{ fontSize: "0.88rem", color: "#fff" }}>PDF Document</strong>
            </div>
          </div>

          <a
            href="/receipt.pdf"
            download="Receipt.pdf"
            style={{
              display: "inline-flex", alignItems: "center", justifyContent: "center", gap: "0.5rem",
              padding: "0.75rem 1.5rem", borderRadius: "0.65rem",
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              color: "#fff", fontWeight: 700, fontSize: "0.92rem",
              textDecoration: "none", boxShadow: "0 4px 16px rgba(99,102,241,0.35)",
              transition: "transform 0.15s ease, opacity 0.15s ease",
            }}
            onMouseEnter={e => e.currentTarget.style.opacity = "0.9"}
            onMouseLeave={e => e.currentTarget.style.opacity = "1"}
          >
            <LuDownload size={16} /> {isTa ? "ரசீதைப் பதிவிறக்கவும்" : "Download Receipt"}
          </a>
        </div>

        {/* ── SECTION 2: CERTIFICATE RETRIEVAL ── */}
        <div
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(168,85,247,0.25)",
            borderRadius: "1.25rem",
            padding: "1.5rem",
            backdropFilter: "blur(16px)",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              position: "absolute", top: 0, left: 0, right: 0, height: "3px",
              background: "linear-gradient(90deg, #a855f7, #ec4899, #22c55e)",
            }}
          />

          <div style={{ display: "flex", alignItems: "flex-start", gap: "0.75rem", marginBottom: "1.25rem" }}>
            <div style={{ width: "2.35rem", height: "2.35rem", borderRadius: "0.55rem", background: "rgba(168,85,247,0.18)", display: "flex", alignItems: "center", justifyContent: "center", color: "#c084fc", flexShrink: 0, marginTop: "0.15rem" }}>
              <LuFileBadge size={20} />
            </div>
            <div>
              <span style={{ fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "rgba(255,255,255,0.45)", fontWeight: 700 }}>
                {isTa ? "பகுதி 2: சான்றிதழ் பெறுதல்" : "Section 2: Residence Certificate Retrieval"}
              </span>
              <h3 style={{ margin: "0.15rem 0 0.25rem", color: "#fff", fontSize: "1.15rem", fontWeight: 700 }}>
                {isTa ? "குடியிருப்புச் சான்றிதழைப் பெறுக" : "Get Your Residence Certificate"}
              </h3>
              <p style={{ margin: 0, color: "rgba(255,255,255,0.65)", fontSize: "0.85rem" }}>
                {isTa
                  ? "உங்கள் சான்றிதழைப் பெற உங்கள் விண்ணப்ப எண்ணை (Application Number) உள்ளிடவும்:"
                  : "Please enter your Application Number to fetch and download your Residence Certificate:"}
              </p>
            </div>
          </div>

          {!certReady && !fetching && (
            <form onSubmit={handleFetchCert} style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
              <div
                style={{
                  display: "flex", alignItems: "center", gap: "0.6rem",
                  background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.15)",
                  borderRadius: "0.65rem", padding: "0.65rem 0.85rem",
                }}
              >
                <LuSearch size={18} style={{ color: "rgba(255,255,255,0.4)", flexShrink: 0 }} />
                <input
                  type="text"
                  value={appNo}
                  onChange={e => setAppNo(e.target.value)}
                  placeholder={isTa ? "விண்ணப்ப எண்ணை உள்ளிடவும் (e.g. TN-7202401230101)" : "Enter Application Number (e.g. TN-7202401230101)"}
                  style={{
                    width: "100%", background: "transparent", border: "none", outline: "none",
                    color: "#fff", fontSize: "0.9rem",
                  }}
                  autoFocus
                />
              </div>

              <button
                type="submit"
                disabled={!appNo.trim()}
                style={{
                  display: "inline-flex", alignItems: "center", justifyContent: "center", gap: "0.5rem",
                  padding: "0.75rem 1.5rem", borderRadius: "0.65rem", border: "none",
                  background: appNo.trim() ? "linear-gradient(135deg, #a855f7, #6366f1)" : "rgba(255,255,255,0.08)",
                  color: appNo.trim() ? "#fff" : "rgba(255,255,255,0.3)",
                  fontWeight: 700, fontSize: "0.92rem",
                  cursor: appNo.trim() ? "pointer" : "not-allowed",
                  transition: "background 0.2s ease, opacity 0.2s ease",
                  boxShadow: appNo.trim() ? "0 4px 16px rgba(168,85,247,0.3)" : "none",
                }}
              >
                <LuFileCheck size={16} /> {isTa ? "சான்றிதழைப் பெறுக" : "Fetch Certificate"}
              </button>
            </form>
          )}

          {fetching && (
            <div
              style={{
                display: "flex", alignItems: "center", gap: "1rem",
                padding: "1.25rem", borderRadius: "0.85rem",
                background: "rgba(168,85,247,0.08)", border: "1px solid rgba(168,85,247,0.25)",
              }}
            >
              <span
                style={{
                  display: "inline-block", width: "24px", height: "24px",
                  border: "2.5px solid rgba(168,85,247,0.25)", borderTopColor: "#a855f7",
                  borderRadius: "50%", animation: "spin 0.85s linear infinite", flexShrink: 0,
                }}
              />
              <div>
                <p style={{ margin: 0, color: "#fff", fontWeight: 600, fontSize: "0.92rem" }}>
                  {isTa ? "சான்றிதழ் பெறப்படுகிறது..." : "Retrieving Residence Certificate…"}
                </p>
                <p style={{ margin: "0.2rem 0 0", color: "#c084fc", fontSize: "0.82rem" }}>
                  {isTa
                    ? `விண்ணப்ப எண் ${fetchedAppNo} க்கான விவரங்கள் சரிபார்க்கப்படுகின்றன`
                    : `Fetching verified certificate for Application Number ${fetchedAppNo}`}
                </p>
              </div>
            </div>
          )}

          {certReady && (
            <div
              className="fade-up"
              style={{
                background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.3)",
                borderRadius: "0.85rem", padding: "1.25rem",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.75rem" }}>
                <LuCircleCheck size={22} style={{ color: "#4ade80", flexShrink: 0 }} />
                <div>
                  <h4 style={{ margin: 0, color: "#fff", fontSize: "1rem", fontWeight: 700 }}>
                    {isTa ? "உங்கள் குடியிருப்புச் சான்றிதழ் தயார்!" : "Your Residence Certificate is Ready!"}
                  </h4>
                  <p style={{ margin: "0.2rem 0 0", color: "rgba(255,255,255,0.6)", fontSize: "0.82rem" }}>
                    {isTa ? "விண்ணப்ப எண்:" : "Application Number:"} <strong style={{ color: "#fff" }}>{fetchedAppNo}</strong>
                  </p>
                </div>
              </div>

              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", marginTop: "1rem" }}>
                <a
                  href="/certificate.pdf"
                  download="ResidenceCertificate.pdf"
                  style={{
                    display: "inline-flex", alignItems: "center", gap: "0.5rem",
                    padding: "0.7rem 1.4rem", borderRadius: "0.5rem",
                    background: "linear-gradient(135deg, #22c55e, #16a34a)",
                    color: "#fff", fontWeight: 700, fontSize: "0.9rem",
                    textDecoration: "none", boxShadow: "0 4px 14px rgba(34,197,94,0.35)",
                  }}
                >
                  <LuDownload size={16} /> {isTa ? "சான்றிதழைப் பதிவிறக்கவும்" : "Download Certificate"}
                </a>

                <button
                  onClick={handleReset}
                  style={{
                    display: "inline-flex", alignItems: "center", gap: "0.4rem",
                    padding: "0.7rem 1.1rem", borderRadius: "0.5rem",
                    background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.15)",
                    color: "rgba(255,255,255,0.8)", fontSize: "0.85rem", fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  <LuRotateCcw size={14} /> {isTa ? "மற்றொரு விண்ணப்ப எண்" : "Fetch Another Number"}
                </button>
              </div>
            </div>
          )}
        </div>

      </div>

      <div style={{ marginTop: "2rem", padding: "1rem", borderRadius: "0.75rem", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", gap: "0.6rem", color: "rgba(255,255,255,0.45)", fontSize: "0.8rem" }}>
        <LuFileText size={16} />
        <span>
          {isTa
            ? "அனைத்து ஆவணங்களும் தமிழ்நாடு மின்னாளுமை முகமை (TNeGA) மூலம் டிஜிட்டல் முறையில் கையொப்பமிடப்பட்டுள்ளன."
            : "All generated documents are digitally signed and verified under Tamil Nadu e-Governance Agency guidelines."}
        </span>
      </div>
    </div>
  );
}
