import { useState, useEffect, useRef } from "react";
import { MdOutlineCloudUpload, MdDeleteOutline } from "react-icons/md";
import { LuCircleCheck, LuChevronDown, LuChevronUp, LuTriangleAlert, LuChevronLeft, LuChevronRight, LuCheck, LuLoader, LuEye, LuEyeOff, LuCalendar } from "react-icons/lu";

// ── Design tokens ─────────────────────────────────────────────────────────────
const C = {
  bg:        "#0a0a0a",
  surface:   "#141414",
  surface2:  "#1c1c1c",
  border:    "#2a2a2a",
  primary:   "#ffffff",
  primaryDim:"rgba(255,255,255,0.08)",
  text:      "#ffffff",
  text2:     "#a0a0a0",
  text3:     "#555555",
  error:     "#f87171",
  success:   "#34d399",
};

const STEPS = [
  { id: "credentials", title: "Portal Credentials" },
  { id: "residency",   title: "Residency" },
  { id: "documents",   title: "Documents" },
];

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];
const WEEKDAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

function DarkCalendarPopover({ value, onSelect, onClose }) {
  const popoverRef = useRef(null);

  // Parse initial selected date from DD/MM/YYYY
  const parseInitialDate = () => {
    if (value && typeof value === "string") {
      const parts = value.split("/");
      if (parts.length === 3) {
        const d = parseInt(parts[0], 10);
        const m = parseInt(parts[1], 10) - 1;
        const y = parseInt(parts[2], 10);
        if (!isNaN(d) && !isNaN(m) && !isNaN(y)) {
          return { month: m, year: y };
        }
      }
    }
    const today = new Date();
    return { month: today.getMonth(), year: today.getFullYear() };
  };

  const initial = parseInitialDate();
  const [viewMonth, setViewMonth] = useState(initial.month);
  const [viewYear, setViewYear] = useState(initial.year);

  // Close on outer click
  useEffect(() => {
    const handleOuter = (e) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) {
        onClose?.();
      }
    };
    document.addEventListener("mousedown", handleOuter);
    return () => document.removeEventListener("mousedown", handleOuter);
  }, [onClose]);

  const prevMonth = () => {
    if (viewMonth === 0) {
      setViewMonth(11);
      setViewYear(v => v - 1);
    } else {
      setViewMonth(v => v - 1);
    }
  };

  const nextMonth = () => {
    if (viewMonth === 11) {
      setViewMonth(0);
      setViewYear(v => v + 1);
    } else {
      setViewMonth(v => v + 1);
    }
  };

  // Generate calendar days (6 rows x 7 cols = 42 cells)
  const firstDayIdx = new Date(viewYear, viewMonth, 1).getDay();
  const daysInCurrentMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
  const daysInPrevMonth = new Date(viewYear, viewMonth, 0).getDate();

  const cells = [];
  // Trailing days from previous month
  for (let i = firstDayIdx - 1; i >= 0; i--) {
    cells.push({
      day: daysInPrevMonth - i,
      month: viewMonth === 0 ? 11 : viewMonth - 1,
      year: viewMonth === 0 ? viewYear - 1 : viewYear,
      isCurrentMonth: false,
    });
  }
  // Days of current month
  for (let d = 1; d <= daysInCurrentMonth; d++) {
    cells.push({
      day: d,
      month: viewMonth,
      year: viewYear,
      isCurrentMonth: true,
    });
  }
  // Leading days of next month
  const totalSoFar = cells.length;
  for (let n = 1; n <= 42 - totalSoFar; n++) {
    cells.push({
      day: n,
      month: viewMonth === 11 ? 0 : viewMonth + 1,
      year: viewMonth === 11 ? viewYear + 1 : viewYear,
      isCurrentMonth: false,
    });
  }

  const today = new Date();
  const isToday = (c) => c.day === today.getDate() && c.month === today.getMonth() && c.year === today.getFullYear();

  const isSelected = (c) => {
    if (!value) return false;
    const parts = value.split("/");
    if (parts.length !== 3) return false;
    return (
      c.day === parseInt(parts[0], 10) &&
      c.month === parseInt(parts[1], 10) - 1 &&
      c.year === parseInt(parts[2], 10)
    );
  };

  const handleSelectDay = (c) => {
    const dayStr = String(c.day).padStart(2, "0");
    const monthStr = String(c.month + 1).padStart(2, "0");
    const formatted = `${dayStr}/${monthStr}/${c.year}`;
    onSelect(formatted);
    onClose?.();
  };

  const currentSystemYear = new Date().getFullYear();
  const yearOptions = Array.from({ length: currentSystemYear - 1950 + 1 }, (_, i) => currentSystemYear - i);

  return (
    <div
      ref={popoverRef}
      style={{
        position: "absolute",
        bottom: "calc(100% + 8px)",
        left: 0,
        width: "285px",
        background: "rgba(18, 18, 22, 0.97)",
        backdropFilter: "blur(24px)",
        WebkitBackdropFilter: "blur(24px)",
        border: "1px solid rgba(255, 255, 255, 0.14)",
        borderRadius: "0.875rem",
        boxShadow: "0 -12px 36px rgba(0,0,0,0.8), 0 0 0 1px rgba(255,255,255,0.05)",
        padding: "0.875rem",
        zIndex: 1000,
        animation: "fade-in 0.15s ease-out",
      }}
    >
      {/* Header with Month/Year Selectors & Nav */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem", gap: "0.375rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
          {/* Month Select */}
          <select
            value={viewMonth}
            onChange={(e) => setViewMonth(Number(e.target.value))}
            style={{
              background: "rgba(255, 255, 255, 0.08)",
              color: "#ffffff",
              border: "1px solid rgba(255, 255, 255, 0.15)",
              borderRadius: "0.375rem",
              padding: "0.25rem 0.4rem",
              fontSize: "0.8125rem",
              fontWeight: 600,
              outline: "none",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            {MONTH_NAMES.map((mName, idx) => (
              <option key={idx} value={idx} style={{ background: "#1c1c1c", color: "#ffffff" }}>
                {mName}
              </option>
            ))}
          </select>

          {/* Year Select (1950 to present) */}
          <select
            value={viewYear}
            onChange={(e) => setViewYear(Number(e.target.value))}
            style={{
              background: "rgba(255, 255, 255, 0.08)",
              color: "#ffffff",
              border: "1px solid rgba(255, 255, 255, 0.15)",
              borderRadius: "0.375rem",
              padding: "0.25rem 0.4rem",
              fontSize: "0.8125rem",
              fontWeight: 600,
              outline: "none",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            {yearOptions.map((y) => (
              <option key={y} value={y} style={{ background: "#1c1c1c", color: "#ffffff" }}>
                {y}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
          <button
            type="button"
            onClick={prevMonth}
            style={{
              background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "0.375rem", width: "1.65rem", height: "1.65rem",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "#ffffff", cursor: "pointer", transition: "background 0.12s"
            }}
            onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.14)"}
            onMouseLeave={e => e.currentTarget.style.background = "rgba(255,255,255,0.06)"}
          >
            <LuChevronLeft size={15} />
          </button>
          <button
            type="button"
            onClick={nextMonth}
            style={{
              background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "0.375rem", width: "1.65rem", height: "1.65rem",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "#ffffff", cursor: "pointer", transition: "background 0.12s"
            }}
            onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.14)"}
            onMouseLeave={e => e.currentTarget.style.background = "rgba(255,255,255,0.06)"}
          >
            <LuChevronRight size={15} />
          </button>
        </div>
      </div>

      {/* Weekday Labels */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: "0.125rem", marginBottom: "0.375rem", textAlign: "center" }}>
        {WEEKDAYS.map((w, idx) => (
          <span key={idx} style={{ fontSize: "0.72rem", fontWeight: 600, color: "rgba(255,255,255,0.4)" }}>
            {w}
          </span>
        ))}
      </div>

      {/* Days Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: "0.125rem" }}>
        {cells.map((c, i) => {
          const selected = isSelected(c);
          const currentToday = isToday(c);
          return (
            <button
              key={i}
              type="button"
              onClick={() => handleSelectDay(c)}
              style={{
                width: "100%",
                height: "2rem",
                borderRadius: "0.375rem",
                border: currentToday && !selected ? "1px solid #a855f7" : "none",
                background: selected
                  ? "linear-gradient(135deg, #a855f7, #6366f1)"
                  : "transparent",
                color: selected
                  ? "#ffffff"
                  : c.isCurrentMonth
                  ? "rgba(255,255,255,0.9)"
                  : "rgba(255,255,255,0.25)",
                fontSize: "0.78rem",
                fontWeight: selected || currentToday ? 700 : 400,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: selected ? "0 4px 12px rgba(168, 85, 247, 0.4)" : "none",
                transition: "all 0.12s ease"
              }}
              onMouseEnter={e => {
                if (!selected) e.currentTarget.style.background = "rgba(255,255,255,0.1)";
              }}
              onMouseLeave={e => {
                if (!selected) e.currentTarget.style.background = "transparent";
              }}
            >
              {c.day}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── Floating label input ──────────────────────────────────────────────────────
function FloatingInput({ label, name, type = "text", value, onChange, maxLength, isDate = false }) {
  const [focused, setFocused] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showCalendar, setShowCalendar] = useState(false);

  const isPassword = type === "password";
  const inputType = isPassword ? (showPassword ? "text" : "password") : type;
  const active = focused || !!value || showCalendar;

  const handleCalendarClick = () => {
    setShowCalendar(prev => !prev);
  };

  return (
    <div style={{ position: "relative", flex: 1, minWidth: 160, marginBottom: "0.25rem" }}>
      <label style={{
        position: "absolute", left: 12, top: "50%",
        transform: active ? "translateY(-130%) scale(0.78)" : "translateY(-50%)",
        fontSize: active ? 11 : 14, color: C.text2,
        background: active ? C.surface2 : "transparent",
        padding: active ? "0 4px" : 0,
        pointerEvents: "none", transition: "all 0.18s ease",
        transformOrigin: "left center", whiteSpace: "nowrap",
        zIndex: 1,
      }}>{label}</label>
      <input
        type={inputType} name={name} value={value} onChange={onChange}
        onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}
        maxLength={maxLength}
        style={{
          width: "100%", boxSizing: "border-box",
          padding: "0.75rem 0.875rem",
          paddingRight: (isPassword || isDate) ? "2.5rem" : "0.875rem",
          paddingTop: active ? "1.1rem" : "0.75rem",
          background: C.surface2,
          border: `1.5px solid ${(focused || showCalendar) ? "rgba(255,255,255,0.4)" : C.border}`,
          borderRadius: "0.625rem", color: C.text, fontSize: 14,
          outline: "none", fontFamily: "inherit",
          boxShadow: (focused || showCalendar) ? "0 0 0 3px rgba(255,255,255,0.06)" : "none",
          transition: "border-color 0.18s, box-shadow 0.18s",
        }}
      />
      {isPassword && (
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          style={{
            position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)",
            background: "none", border: "none", color: C.text2, cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "center",
            padding: 4, borderRadius: 4, zIndex: 2, transition: "color 0.18s",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = C.text)}
          onMouseLeave={(e) => (e.currentTarget.style.color = C.text2)}
          title={showPassword ? "Hide password" : "Show password"}
        >
          {showPassword ? <LuEyeOff size={16} /> : <LuEye size={16} />}
        </button>
      )}
      {isDate && (
        <div style={{ position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 2 }}>
          <button
            type="button"
            onClick={handleCalendarClick}
            style={{
              background: "none", border: "none", color: showCalendar ? "#ffffff" : C.text2, cursor: "pointer",
              display: "flex", alignItems: "center", justifyContent: "center",
              padding: 4, borderRadius: 4, transition: "color 0.18s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = C.text)}
            onMouseLeave={(e) => (e.currentTarget.style.color = showCalendar ? "#ffffff" : C.text2)}
            title="Open calendar picker"
          >
            <LuCalendar size={17} />
          </button>
        </div>
      )}
      {isDate && showCalendar && (
        <DarkCalendarPopover
          value={value}
          onSelect={(dateStr) => {
            onChange({ target: { name, value: dateStr } });
          }}
          onClose={() => setShowCalendar(false)}
        />
      )}
    </div>
  );
}

// ── Step progress bar ─────────────────────────────────────────────────────────
function StepBar({ current, total, steps }) {
  return (
    <div style={{ marginBottom: "1.75rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
        {steps.map((s, i) => (
          <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", flex: 1 }}>
            <div style={{
              width: 28, height: 28, borderRadius: "50%",
              background: i <= current ? "#ffffff" : "#2a2a2a",
              border: `2px solid ${i <= current ? "#ffffff" : "#3a3a3a"}`,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 12, fontWeight: 700,
              color: i <= current ? "#000" : C.text3,
              boxShadow: i === current ? "0 0 0 4px rgba(255,255,255,0.12)" : "none",
              transition: "all 0.25s",
            }}>
              {i < current ? <LuCheck size={13} /> : i + 1}
            </div>
            <div style={{
              fontSize: 11, fontWeight: 600,
              color: i <= current ? C.text : C.text3,
              marginTop: 6, transition: "color 0.25s",
            }}>{s.title}</div>
          </div>
        ))}
      </div>
      <div style={{ height: 3, background: "#2a2a2a", borderRadius: 99, overflow: "hidden", marginTop: 4 }}>
        <div style={{
          height: "100%", width: `${((current + 1) / total) * 100}%`,
          background: "#ffffff",
          transition: "width 0.3s ease-in-out",
        }} />
      </div>
    </div>
  );
}

// ── Nav buttons ───────────────────────────────────────────────────────────────
function NavButtons({ step, totalSteps, onBack, onNext, onSubmit, onExit, canNext, isSubmitting, isExtracting }) {
  const isLast = step === totalSteps - 1;
  const disabled = !canNext || isSubmitting || isExtracting;
  const btnBase = {
    display: "inline-flex", alignItems: "center", gap: "0.375rem",
    padding: "0.65rem 1.375rem", borderRadius: "9999px",
    fontSize: 14, fontWeight: 600, cursor: "pointer",
    border: "none", fontFamily: "inherit", transition: "all 0.15s",
  };
  return (
    <div style={{ display: "flex", justifyContent: "space-between", marginTop: "1.5rem", paddingTop: "1.25rem", borderTop: `1px solid ${C.border}` }}>
      <button onClick={onBack} disabled={step === 0} style={{
        ...btnBase,
        background: "#1c1c1c", color: step === 0 ? C.text3 : C.text,
        border: "1px solid #2a2a2a", opacity: step === 0 ? 0.4 : 1,
      }}>
        <LuChevronLeft size={15} /> Back
      </button>
      <div style={{ display: "flex", gap: "0.625rem" }}>
        <button onClick={onExit} style={{
          ...btnBase,
          background: "#1c1c1c", color: C.text2,
          border: "1px solid #2a2a2a",
        }}>
          Exit
        </button>
        <button onClick={isLast ? onSubmit : onNext} disabled={disabled} style={{
          ...btnBase,
          background: disabled ? "#2a2a2a" : "#e0e0e0",
          color: disabled ? C.text3 : "#000",
          opacity: disabled ? 0.5 : 1,
        }}>
          {isExtracting ? <><LuLoader size={14} style={{ animation: "spin 1s linear infinite" }} /> Extracting…</>
            : isSubmitting ? <><LuLoader size={14} style={{ animation: "spin 1s linear infinite" }} /> Processing…</>
            : isLast ? <><LuCheck size={14} /> Proceed to Automation</>
            : <>Next <LuChevronRight size={15} /></>}
        </button>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function DocumentChecklist({ onProceed, onExit, isProceeding, onOpenSocket, automationStatus, onResetAutomationStatus }) {
  const [step, setStep] = useState(0);
  const [checkedItems, setCheckedItems]   = useState({ aadharCard: false, rationCard: false, photo: false, drivingLicense: false });
  const [expandedItem, setExpandedItem]   = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState({});
  const [rawFiles, setRawFiles]           = useState({});
  const [extractedData, setExtractedData] = useState({});
  const [isUploading, setIsUploading]     = useState({});
  const [uploadError, setUploadError]     = useState(null);
  const [bulkResults, setBulkResults]     = useState(null);
  const [submitError, setSubmitError]     = useState(null);
  const [isExtracting, setIsExtracting]   = useState(false);
  const [credentials, setCredentials]     = useState({ username: "", password: "", can_number: "", aadhar_number: "" });
  const [addressDetails, setAddressDetails] = useState({ from_date: "", to_date: "" });
  const [completedSteps, setCompletedSteps] = useState({ loggedIn: false, formFilled: false, docsUploaded: false, submitted: false });

  useEffect(() => {
    if (!automationStatus) return;
    const s = automationStatus.toLowerCase();
    setCompletedSteps(prev => ({
      loggedIn:     prev.loggedIn     || s.includes("otp verified") || s.includes("loading the form") || s.includes("filling in") || s.includes("saving your address") || s.includes("uploading") || s.includes("all documents") || s.includes("payment") || s.includes("done"),
      formFilled:   prev.formFilled   || s.includes("saving your address") || s.includes("submitting the application") || s.includes("uploading") || s.includes("all documents") || s.includes("payment") || s.includes("done"),
      docsUploaded: prev.docsUploaded || s.includes("all documents uploaded") || s.includes("going to payment") || s.includes("payment") || s.includes("done"),
      submitted:    prev.submitted    || s.includes("done!") || s.includes("payment page reached"),
    }));
  }, [automationStatus]);

  const documents = [
    { id: "aadharCard",     label: "Aadhar card" },
    { id: "rationCard",     label: "Ration card" },
    { id: "photo",          label: "Applicant Photograph" },
    { id: "drivingLicense", label: "Driving license" },
  ];

  const [supabaseDocUrls, setSupabaseDocUrls] = useState({});

  // ── Restore existing user documents from Supabase on mount ───────────────────
  useEffect(() => {
    const userPhone = sessionStorage.getItem("user_phone");
    if (!userPhone) return;

    fetch(`${import.meta.env.VITE_API_BASE}/api/user-documents?phone_number=${encodeURIComponent(userPhone)}`)
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data && data.documents) {
          const docsMap = data.documents;
          const restoredFiles = {};
          const restoredUrls = {};
          const restoredExtracted = {};
          const restoredChecked = {};

          Object.keys(docsMap).forEach(docId => {
            const docInfo = docsMap[docId];
            if (docInfo.filename) restoredFiles[docId] = docInfo.filename;
            if (docInfo.supabase_url) restoredUrls[docId] = docInfo.supabase_url;
            if (docInfo.extracted_data && docInfo.extracted_data.length > 0) {
              restoredExtracted[docId] = docInfo.extracted_data;
            }
            restoredChecked[docId] = true;
          });

          if (Object.keys(restoredChecked).length > 0) {
            setUploadedFiles(prev => ({ ...prev, ...restoredFiles }));
            setSupabaseDocUrls(prev => ({ ...prev, ...restoredUrls }));
            setExtractedData(prev => ({ ...prev, ...restoredExtracted }));
            setCheckedItems(prev => ({ ...prev, ...restoredChecked }));
            console.log("[User Memory] Auto-restored user documents from Supabase:", Object.keys(restoredChecked));
          }
        }
      })
      .catch(err => console.warn("[User Memory] Error fetching restored user documents:", err));
  }, []);

  const handleCredChange = (e) => setCredentials({ ...credentials, [e.target.name]: e.target.value });
  const handleAddrChange = (e) => setAddressDetails({ ...addressDetails, [e.target.name]: e.target.value });

  const handleRemoveFile = (id) => {
    setUploadedFiles(p => { const u = { ...p }; delete u[id]; return u; });
    setRawFiles(p => { const u = { ...p }; delete u[id]; return u; });
    setExtractedData(p => { const u = { ...p }; delete u[id]; return u; });
    setSupabaseDocUrls(p => { const u = { ...p }; delete u[id]; return u; });
    setCheckedItems(p => ({ ...p, [id]: false }));
  };

  const handleFileUpload = async (e, id) => {
    const file = e.target.files[0];
    if (!file) return;
    setIsUploading(p => ({ ...p, [id]: true }));
    setUploadError(null);
    const formData = new FormData();
    formData.append("file", file);
    const extUrl = id === "photo"
      ? `${import.meta.env.VITE_DOC_API_BASE}/verify/photo`
      : `${import.meta.env.VITE_DOC_API_BASE}/extract`;
    try {
      const res = await fetch(extUrl, { method: "POST", body: formData });
      if (res.ok) {
        const data = await res.json();
        if (id === "photo" && data.is_human_photo === false)
          throw new Error("Invalid Photograph. Please ensure the image clearly shows a human person.");
        if (id !== "photo" && data.extracted_data?.length > 0)
          setExtractedData(p => ({ ...p, [id]: data.extracted_data }));

        // ── Zero-Knowledge Client-Side Document Encryption ────────────────────
        let encryptedUrl = "";
        try {
          const { encryptDocumentBytesZK } = await import("../utils/crypto");
          const userPhone = sessionStorage.getItem("user_phone") || "default";
          const fileBuffer = await file.arrayBuffer();
          const encBuffer = await encryptDocumentBytesZK(fileBuffer, userPhone);
          const encBlob = new Blob([encBuffer], { type: "application/octet-stream" });
          const encForm = new FormData();
          encForm.append("file", encBlob, `${file.name}.zkenc`);
          encForm.append("phone_number", userPhone);

          const encRes = await fetch(`${import.meta.env.VITE_DOC_API_BASE}/upload-encrypted-doc`, {
            method: "POST",
            body: encForm,
          });
          if (encRes.ok) {
            const encData = await encRes.json();
            encryptedUrl = encData.supabase_url;
            console.log(`[ZK Storage] Uploaded encrypted binary document -> ${encryptedUrl}`);

            // Register document in user's personalized Supabase registry
            if (userPhone && encryptedUrl) {
              fetch(`${import.meta.env.VITE_API_BASE}/api/user-documents`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  phone_number: userPhone,
                  doc_id: id,
                  filename: file.name,
                  supabase_url: encryptedUrl,
                  extracted_data: data.extracted_data || []
                })
              }).catch(e => console.warn("[User Memory] Error persisting doc registry:", e));
            }
          }
        } catch (encErr) {
          console.warn("[ZK Storage] Zero-Knowledge document encryption warning:", encErr);
        }

        setUploadedFiles(p => ({ ...p, [id]: file.name }));
        setRawFiles(p => ({ ...p, [id]: file }));
        if (encryptedUrl) setSupabaseDocUrls(p => ({ ...p, [id]: encryptedUrl }));
        setCheckedItems(p => ({ ...p, [id]: true }));
        setExpandedItem(null);
      } else {
        let detail = "";
        try { const b = await res.json(); detail = b.detail || b.message || ""; } catch (_) {}
        throw new Error(`Upload failed (HTTP ${res.status})${detail ? ": " + detail : "."}`);
      }
    } catch (err) {
      setUploadError(err.message || "Upload failed. Please try again.");
    } finally {
      setIsUploading(p => ({ ...p, [id]: false }));
    }
  };

  const handleDownloadEncryptedDoc = async (id) => {
    const docUrl = supabaseDocUrls[id];
    const userPhone = sessionStorage.getItem("user_phone") || "default";
    const fileName = uploadedFiles[id] || `${id}.pdf`;

    const pinInput = window.prompt("Enter your 6-digit Security PIN to decrypt and download your document:");
    if (!pinInput) return;

    try {
      let fileBuffer;
      if (docUrl) {
        const resp = await fetch(docUrl);
        if (!resp.ok) throw new Error(`Could not fetch document from Supabase (HTTP ${resp.status})`);
        fileBuffer = await resp.arrayBuffer();
      } else if (rawFiles[id]) {
        fileBuffer = await rawFiles[id].arrayBuffer();
      } else {
        throw new Error("No document available for download.");
      }

      const { decryptDocumentBytesZK } = await import("../utils/crypto");
      const decryptedBuf = await decryptDocumentBytesZK(fileBuffer, userPhone, pinInput.trim());

      const isPdf = fileName.toLowerCase().endsWith(".pdf");
      const mimeType = isPdf ? "application/pdf" : "image/jpeg";
      const blob = new Blob([decryptedBuf], { type: mimeType });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = fileName;
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (err) {
      alert("Decryption Failed: " + (err.message || "Invalid 6-digit PIN. Only the document owner can decrypt this file."));
    }
  };

  const isAllChecked  = Object.values(checkedItems).every(Boolean);
  const canNext = [
    credentials.username && credentials.password,
    addressDetails.from_date && addressDetails.to_date,
    isAllChecked,
  ][step];

  // ── Retry: reset all automation state then re-run the full flow ──────────────
  const handleRetryClick = async () => {
    // Reset step completions so the UI shows fresh progress for the new run
    setCompletedSteps({ loggedIn: false, formFilled: false, docsUploaded: false, submitted: false });
    // Reset the parent-held automationStatus so the header shows "Starting automation…"
    if (onResetAutomationStatus) onResetAutomationStatus();
    setSubmitError(null);
    setIsExtracting(false);
    // Small delay to let React flush the state resets before starting the new run
    await new Promise(r => setTimeout(r, 50));
    await handleProceedClick();
  };

  const handleProceedClick = async () => {
    setSubmitError(null);
    setIsExtracting(true);
    const extractForm = new FormData();
    if (rawFiles.aadharCard)     extractForm.append("aadhaar", rawFiles.aadharCard);
    if (rawFiles.rationCard)     extractForm.append("ration",  rawFiles.rationCard);
    if (rawFiles.drivingLicense) extractForm.append("driving", rawFiles.drivingLicense);
    if (rawFiles.photo)          extractForm.append("photo",   rawFiles.photo);

    // Pass pre-extracted JSON data so backend reuses it without calling VLM again
    if (extractedData.aadharCard)     extractForm.append("pre_aadhaar", JSON.stringify(extractedData.aadharCard));
    if (extractedData.rationCard)     extractForm.append("pre_ration",  JSON.stringify(extractedData.rationCard));
    if (extractedData.drivingLicense) extractForm.append("pre_driving", JSON.stringify(extractedData.drivingLicense));

    try {
      const bulkRes = await fetch(`${import.meta.env.VITE_DOC_API_BASE}/process-all`, { method: "POST", body: extractForm });
      if (!bulkRes.ok) throw new Error(`Document extraction failed (HTTP ${bulkRes.status})`);
      const bulkData = await bulkRes.json();
      if (!(bulkData.status === "success" && bulkData.result)) throw new Error("Document extraction returned no results.");

      const orchPaths = bulkData.saved_paths || {};
      const supUrls   = bulkData.supabase_urls || {};

      setBulkResults(bulkData.result);
      const c = bulkData.result.combined;
      const aadharNum = (credentials.aadhar_number || c.aadhaar_number || "").replace(/\s/g, "");
      const payload = {
        credentials: { username: credentials.username, password: credentials.password },
        applicant_details: { can_number: credentials.can_number || "", aadhar_number: aadharNum, dob: c.dob || "", ration_card_no: c.ration_card_number || "", name: c.username || "", father_name: c.father_name || "", gender: c.gender || "", religion: c.religion || "", community: c.community || "", mobile_number: c.phone_number || "", email: c.email || "" },
        address_details: { state: c.state || "Tamil Nadu", district: c.district || "", village: c.taluk || c.district || "", area: c.area || "", building_no: c.door_no || "", street_name: c.street_name || c.area || "", pincode: c.pincode || "", from_date: addressDetails.from_date, to_date: addressDetails.to_date, perm_state: c.state || "Tamil Nadu", perm_district: c.district || "", perm_village: c.taluk || c.district || "", perm_building_no: c.door_no || "", perm_street_name: c.street_name || c.area || "", perm_pincode: c.pincode || "" },
        documents: {
          photo_path: supUrls.Photo || orchPaths.Photo || orchPaths.photo || "",
          self_decl_path: "",
          aadhaar_path: supUrls.Aadhaar || orchPaths.Aadhaar || orchPaths.aadhaar || "",
          address_proof_path: supUrls["Driving License"] || supUrls["Ration Card"] || orchPaths["Driving License"] || orchPaths["Ration Card"] || orchPaths.driving || orchPaths.ration || "",
          address_doc_no: c.dl_number || ""
        },
      };

      if (onOpenSocket) await onOpenSocket();
      for (let i = 0; i < 10; i++) {
        try { const s = await fetch(`${import.meta.env.VITE_API_BASE}/ws/status`); const d = await s.json(); if (d.connected) break; } catch (_) {}
        await new Promise(r => setTimeout(r, 500));
      }
      const submitRes = await fetch(`${import.meta.env.VITE_API_BASE}/submit-application`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      if (!submitRes.ok) throw new Error(`Automation server error (HTTP ${submitRes.status}).`);
    } catch (e) {
      setSubmitError(e.message || "An unexpected error occurred.");
      setIsExtracting(false);
    }
  };

  // ── Success / automation live screen ────────────────────────────────────────
  if (bulkResults) {
    const isDone  = automationStatus && (automationStatus.includes("Done!") || automationStatus.includes("Payment page") || automationStatus.includes("went wrong"));
    const isError = automationStatus && automationStatus.includes("went wrong");
    return (
      <div className="cl-card fade-up">
        <div className="cl-live-header">
          <div className={`cl-live-icon ${isDone ? (isError ? "error" : "done") : "running"}`}>
            {isDone ? (isError ? "✕" : "✓") : <span className="cl-spin-ring" />}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <h3 className="cl-title" key={automationStatus} style={{ animation: "status-fade 0.35s ease both" }}>
              {automationStatus || "Starting automation…"}
            </h3>
            <p className="cl-sub" style={{ marginTop: "0.2rem" }}>
              {isDone
                ? (isError ? "Please try again or contact support." : "Payment page opened in your browser — complete your payment there.")
                : "Sit back — we're handling everything for you."}
            </p>
          </div>
        </div>
        <div className="cl-steps">
          {[
            { label: "Logged in",           done: completedSteps.loggedIn },
            { label: "Form filled",         done: completedSteps.formFilled },
            { label: "Documents uploaded",  done: completedSteps.docsUploaded },
            { label: "Submitted to portal", done: completedSteps.submitted },
          ].map((s, i) => (
            <div key={i} className={`cl-step ${s.done ? "done" : ""}`}>
              <div className="cl-step-dot">{s.done ? "✓" : i + 1}</div>
              <span className="cl-step-label">{s.label}</span>
            </div>
          ))}
        </div>
        <div className="cl-actions" style={{ marginTop: "1.25rem", display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
          {isError && (
            <button
              className="btn-primary"
              onClick={handleRetryClick}
              style={{
                padding: "0.6rem 1.25rem", fontSize: "0.875rem", fontWeight: 600,
                background: "linear-gradient(135deg, #a855f7, #6366f1)", color: "#fff",
                border: "none", borderRadius: "9999px", cursor: "pointer"
              }}
            >
              Retry
            </button>
          )}
          <button className="btn-secondary" onClick={onExit}>Close</button>
        </div>
      </div>
    );
  }

  // ── Step content ─────────────────────────────────────────────────────────────
  const sectionStyle = {
    background: "#1c1c1c",
    border: "1px solid #2a2a2a",
    borderRadius: "1rem",
    padding: "1.5rem",
    marginBottom: "1rem",
  };
  const sectionLabel = {
    fontSize: 11, fontWeight: 700, color: C.text2,
    textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "1.25rem",
  };

  return (
    <div className="cl-card fade-up" style={{ background: "#141414", border: "1px solid #2a2a2a", overflow: "visible" }}>
      <h3 className="cl-title" style={{ marginBottom: "1.5rem", color: "#fff" }}>TNeSevai Application Details</h3>

      <StepBar current={step} total={STEPS.length} steps={STEPS} />

      {/* ── Step 0: Portal Credentials ── */}
      {step === 0 && (
        <div style={sectionStyle}>
          <div style={sectionLabel}>Portal Credentials</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
            <FloatingInput label="TNeSevai Username" name="username"      value={credentials.username}      onChange={handleCredChange} />
            <FloatingInput label="Password"          name="password"      type="password" value={credentials.password} onChange={handleCredChange} />
            <FloatingInput label="CAN Number"        name="can_number"    value={credentials.can_number}    onChange={handleCredChange} />
            <FloatingInput label="Aadhar Number *"   name="aadhar_number" value={credentials.aadhar_number} onChange={handleCredChange} maxLength={12} />
          </div>
        </div>
      )}

      {/* ── Step 1: Residency ── */}
      {step === 1 && (
        <div style={sectionStyle}>
          <div style={sectionLabel}>Residency Constraints</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
            <FloatingInput label="Residing From (DD/MM/YYYY)" name="from_date" isDate value={addressDetails.from_date} onChange={handleAddrChange} />
            <FloatingInput label="Residing To (DD/MM/YYYY)"   name="to_date"   isDate value={addressDetails.to_date}   onChange={handleAddrChange} />
          </div>
        </div>
      )}

      {/* ── Step 2: Documents ── */}
      {step === 2 && (
        <div>
          <p className="cl-sub" style={{ marginBottom: "0.875rem" }}>
            Ensure all required documents are ready for extraction &amp; upload:
          </p>
          <div className="cl-doc-list">
            {documents.map(doc => {
              const isChecked  = checkedItems[doc.id];
              const isExpanded = expandedItem === doc.id;
              return (
                <div key={doc.id} className={`cl-doc-item${isChecked ? " checked" : ""}${isExpanded ? " expanded" : ""}`}>
                  <div className="cl-doc-header" onClick={() => { setExpandedItem(p => p === doc.id ? null : doc.id); setUploadError(null); }}>
                    <div className="cl-doc-left">
                      <div className={`cl-checkbox${isChecked ? " checked" : ""}`}>
                        {isChecked && <LuCircleCheck size={13} color="#fff" />}
                      </div>
                      <span className="cl-doc-label">{doc.label}</span>
                    </div>
                    {isExpanded ? <LuChevronUp size={16} className="cl-chevron" /> : <LuChevronDown size={16} className="cl-chevron" />}
                  </div>
                  {isExpanded && (
                    <div className="cl-doc-body fade-up">
                      {uploadedFiles[doc.id] ? (
                        <div>
                          <div className="cl-file-row">
                            <div className="cl-file-name"><LuCircleCheck size={15} /><span>{uploadedFiles[doc.id]}</span></div>
                            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                              <button
                                type="button"
                                title="Decrypt and download document using your 6-digit PIN"
                                onClick={() => handleDownloadEncryptedDoc(doc.id)}
                                style={{
                                  padding: "0.25rem 0.65rem", borderRadius: "9999px",
                                  background: "rgba(52, 211, 153, 0.12)", color: "#34d399",
                                  border: "1px solid rgba(52, 211, 153, 0.4)",
                                  fontSize: "0.725rem", fontWeight: 600, cursor: "pointer",
                                  display: "flex", alignItems: "center", gap: "4px"
                                }}
                              >
                                🔒 PIN Download
                              </button>
                              <button className="cl-remove-btn" onClick={() => handleRemoveFile(doc.id)}><MdDeleteOutline size={17} /></button>
                            </div>
                          </div>
                          {extractedData[doc.id]?.map((extract, idx) => (
                            <div key={idx} className="cl-extracted">
                              <h5 className="cl-extracted-title">{extract.certificate_type} Details</h5>
                              <ul className="cl-extracted-list">
                                {Object.entries(extract.extracted_fields || extract).filter(([k]) => k !== "certificate_type").map(([k, v]) => (
                                  <li key={k}><strong>{k.replace(/_/g, " ").toUpperCase()}:</strong> {v}</li>
                                ))}
                              </ul>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <label className="upload-zone" style={{ opacity: isUploading[doc.id] ? 0.6 : 1 }}>
                          <input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={e => handleFileUpload(e, doc.id)} disabled={isUploading[doc.id]} hidden />
                          <div className="upload-zone-icon"><MdOutlineCloudUpload size={22} /></div>
                          <p className="cl-upload-title">{isUploading[doc.id] ? "Uploading…" : `Upload ${doc.label}`}</p>
                          <p className="cl-upload-sub">PDF, JPG or PNG · max 5 MB</p>
                          {uploadError && <div className="cl-error-inline"><LuTriangleAlert size={13} /> {uploadError}</div>}
                          <span className="upload-zone-btn">{isUploading[doc.id] ? "Uploading…" : "Browse Files"}</span>
                        </label>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {submitError && (
        <div className="cl-error-block" style={{ marginTop: "0.75rem", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <LuTriangleAlert size={16} /> <span>{submitError}</span>
          </div>
          <button
            type="button"
            onClick={handleProceedClick}
            style={{
              padding: "0.35rem 0.85rem", borderRadius: "9999px",
              background: "#ef4444", color: "#ffffff",
              border: "none", fontSize: "0.75rem", fontWeight: 700,
              cursor: "pointer", flexShrink: 0
            }}
          >
            Retry
          </button>
        </div>
      )}

      <NavButtons
        step={step}
        totalSteps={STEPS.length}
        onBack={() => setStep(s => Math.max(0, s - 1))}
        onNext={() => setStep(s => Math.min(STEPS.length - 1, s + 1))}
        onSubmit={handleProceedClick}
        onExit={onExit}
        canNext={!!canNext}
        isSubmitting={isProceeding}
        isExtracting={isExtracting}
      />
    </div>
  );
}
