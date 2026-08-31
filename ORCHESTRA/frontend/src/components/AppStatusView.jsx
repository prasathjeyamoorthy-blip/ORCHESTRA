import { useState } from "react";
import { LuSearch, LuCircleCheck, LuClock, LuTriangleAlert } from "react-icons/lu";

export default function AppStatusView({ currentLanguage = "en" }) {
  const [refNo, setRefNo] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const isTa = currentLanguage === "ta";

  const handleCheck = async (e) => {
    e.preventDefault();
    if (!refNo.trim()) return;
    setLoading(true);
    // Simulate a lookup — replace with real API call when available
    await new Promise(r => setTimeout(r, 1200));
    setResult({
      ref: refNo.trim(),
      status: "pending",
      label: isTa ? "பரிசீலனையில் உள்ளது" : "Under Review",
      updated: new Date().toLocaleDateString(isTa ? "ta-IN" : "en-IN", { day: "2-digit", month: "short", year: "numeric" }),
      message: isTa ? "உங்கள் விண்ணப்பம் பெறப்பட்டு சம்பந்தப்பட்ட அதிகாரியால் பரிசீலிக்கப்பட்டு வருகிறது." : "Your application has been received and is currently under review by the concerned authority.",
    });
    setLoading(false);
  };

  const statusMeta = {
    approved: { icon: <LuCircleCheck size={20} />, color: "var(--primary)", bg: "var(--primary-light)" },
    pending:  { icon: <LuClock size={20} />,       color: "#f59e0b",         bg: "rgba(245,158,11,0.1)" },
    rejected: { icon: <LuTriangleAlert size={20} />, color: "#ef4444",       bg: "rgba(239,68,68,0.08)" },
  };

  return (
    <div className="view-page">
      <div className="view-header">
        <h2 className="view-title">{isTa ? "விண்ணப்ப நிலையை அறிய" : "Track Application"}</h2>
        <p className="view-sub">{isTa ? "உங்கள் விண்ணப்பத்தின் தற்போதைய நிலையைச் சரிபார்க்க குறிப்பு எண்ணை உள்ளிடவும்." : "Enter your application reference number to check the current status."}</p>
      </div>

      <form onSubmit={handleCheck} className="status-form">
        <div className="status-input-wrap">
          <LuSearch size={16} color="var(--text-3)" style={{ flexShrink: 0 }} />
          <input
            className="status-input"
            placeholder={isTa ? "குறிப்பு / விண்ணப்ப எண்ணை உள்ளிடவும்" : "Enter reference / application number"}
            value={refNo}
            onChange={e => setRefNo(e.target.value)}
          />
        </div>
        <button type="submit" className="btn-primary" disabled={loading || !refNo.trim()}>
          {loading ? (isTa ? "சரிபார்க்கப்படுகிறது…" : "Checking…") : (isTa ? "நிலையைச் சரிபார்க்கவும்" : "Check Status")}
        </button>
      </form>

      {result && (() => {
        const meta = statusMeta[result.status] || statusMeta.pending;
        return (
          <div className="status-result" style={{ borderColor: meta.color }}>
            <div className="status-result-header" style={{ background: meta.bg, color: meta.color }}>
              {meta.icon}
              <span>{result.label}</span>
            </div>
            <div className="status-result-body">
              <div className="status-row"><span>{isTa ? "குறிப்பு எண்" : "Reference No."}</span><strong>{result.ref}</strong></div>
              <div className="status-row"><span>{isTa ? "கடைசியாக புதுப்பிக்கப்பட்டது" : "Last Updated"}</span><strong>{result.updated}</strong></div>
              <div className="status-row"><span>{isTa ? "குறிப்புகள்" : "Remarks"}</span><span style={{ color: "var(--text-2)", fontSize: "0.8125rem" }}>{result.message}</span></div>
            </div>
          </div>
        );
      })()}

      <p className="view-note">
        {isTa ? "உங்கள் விண்ணப்பத்தை நேரடியாக " : "You can also track your application directly on the "}
        <a href="https://www.tnesevai.tn.gov.in/citizen/trackApplication" target="_blank" rel="noreferrer">
          {isTa ? "TNeGA இ-சேவை தளத்திலும் தொடரலாம்" : "TNeGA e-Sevai portal"}
        </a>.
      </p>
    </div>
  );
}
