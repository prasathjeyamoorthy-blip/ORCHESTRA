import { useState, useEffect, useRef } from "react";
import { MdOutlineCloudUpload, MdDeleteOutline } from "react-icons/md";
import { LuCircleCheck, LuChevronDown, LuChevronUp, LuTriangleAlert, LuChevronLeft, LuChevronRight, LuCheck, LuLoader, LuEye, LuEyeOff, LuCalendar, LuWrench, LuLock } from "react-icons/lu";

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

const DOCUMENTS = [
  { id: "aadharCard",     label: "Aadhar card",                               pdfOnly: false },
  { id: "rationCard",     label: "Ration card",                               pdfOnly: false },
  { id: "photo",          label: "Applicant Photograph",                      pdfOnly: false },
  { id: "drivingLicense", label: "Address Proof (Driving License / Aadhaar)", pdfOnly: false },
];

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];
const WEEKDAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

function getTodayFormatted() {
  const d = new Date();
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const year = d.getFullYear();
  return `${day}/${month}/${year}`;
}

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
        top: "calc(100% + 8px)",
        left: 0,
        width: "285px",
        maxWidth: "calc(100vw - 48px)",
        background: "rgba(18, 18, 22, 0.97)",
        backdropFilter: "blur(24px)",
        WebkitBackdropFilter: "blur(24px)",
        border: "1px solid rgba(255, 255, 255, 0.14)",
        borderRadius: "0.875rem",
        boxShadow: "0 12px 36px rgba(0,0,0,0.8), 0 0 0 1px rgba(255,255,255,0.08)",
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
function FloatingInput({ label, name, type = "text", value, onChange, maxLength, isDate = false, autoComplete = "on" }) {
  const [focused, setFocused] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showCalendar, setShowCalendar] = useState(false);
  const [isAutofilled, setIsAutofilled] = useState(false);

  const isPassword = type === "password";
  const inputType = isPassword ? (showPassword ? "text" : "password") : type;
  const active = focused || !!value || showCalendar || isAutofilled;

  const handleAnimationStart = (e) => {
    if (e.animationName === "onAutoFillStart") {
      setIsAutofilled(true);
      if (e.target.value && e.target.value !== value) {
        onChange?.({ target: { name, value: e.target.value } });
      }
    } else if (e.animationName === "onAutoFillCancel") {
      setIsAutofilled(false);
    }
  };

  const handleCalendarClick = () => {
    setShowCalendar(prev => !prev);
  };

  return (
    <div style={{ position: "relative", flex: "1 1 200px", minWidth: "140px", marginBottom: "0.25rem", boxSizing: "border-box" }}>
      <input
        type={inputType}
        name={name}
        id={`fi_${name}`}
        placeholder=" "
        value={value ?? ""}
        onChange={onChange}
        onInput={onChange}
        onAnimationStart={handleAnimationStart}
        onFocus={() => setFocused(true)}
        onBlur={(e) => {
          setFocused(false);
          if (e.target.value && e.target.value !== value) {
            onChange?.({ target: { name, value: e.target.value } });
          }
        }}
        maxLength={maxLength}
        autoComplete={autoComplete}
        style={{
          width: "100%", boxSizing: "border-box",
          padding: "0.5rem 0.875rem",
          paddingRight: (isPassword || isDate) ? "2.5rem" : "0.875rem",
          paddingTop: "1.15rem",
          paddingBottom: "0.45rem",
          background: C.surface2,
          border: `1.5px solid ${(focused || showCalendar || isAutofilled) ? "rgba(255,255,255,0.4)" : C.border}`,
          borderRadius: "0.625rem", color: C.text, fontSize: 14,
          outline: "none", fontFamily: "inherit",
          boxShadow: (focused || showCalendar || isAutofilled) ? "0 0 0 3px rgba(255,255,255,0.06)" : "none",
          transition: "border-color 0.18s, box-shadow 0.18s",
        }}
      />
      <label
        htmlFor={`fi_${name}`}
        style={{
          position: "absolute", left: 12, top: "50%",
          transform: active ? "translateY(-130%) scale(0.78)" : "translateY(-50%)",
          fontSize: active ? 11 : 14, color: C.text2,
          background: active ? C.surface2 : "transparent",
          padding: active ? "0 4px" : 0,
          pointerEvents: "none", transition: "all 0.18s ease",
          transformOrigin: "left center", whiteSpace: "nowrap",
          zIndex: 1,
        }}
      >{label}</label>
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
              textAlign: "center",
              lineHeight: 1.25,
              wordBreak: "break-word",
              padding: "0 2px"
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
    <div style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      marginTop: "1.5rem",
      paddingTop: "1.25rem",
      borderTop: `1px solid ${C.border}`,
      width: "100%",
      boxSizing: "border-box",
      flexWrap: "wrap",
      gap: "0.75rem"
    }}>
      <button onClick={onBack} disabled={step === 0} style={{
        ...btnBase,
        background: "#1c1c1c", color: step === 0 ? C.text3 : C.text,
        border: "1px solid #2a2a2a", opacity: step === 0 ? 0.4 : 1,
        cursor: step === 0 ? "not-allowed" : "pointer",
      }}>
        <LuChevronLeft size={15} /> Back
      </button>
      <div style={{ display: "flex", gap: "0.625rem", alignItems: "center" }}>
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
          {isExtracting ? <><LuLoader size={14} style={{ animation: "spin 1s linear infinite" }} /> Validating documents…</>
            : isSubmitting ? <><LuLoader size={14} style={{ animation: "spin 1s linear infinite" }} /> Processing…</>
            : isLast ? <><LuCheck size={14} /> Proceed to Automation</>
            : <>Next <LuChevronRight size={15} /></>}
        </button>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function DocumentChecklist({ _onProceed, onExit, isProceeding, onOpenSocket, automationStatus, onResetAutomationStatus }) {
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
  const [isDeletingSavedApp, setIsDeletingSavedApp] = useState(false);
  const [deleteSavedAppMsg, setDeleteSavedAppMsg]   = useState("");
  const [credentials, setCredentials]     = useState(() => {
    try {
      const saved = sessionStorage.getItem("tnega_draft_credentials");
      if (saved) return JSON.parse(saved);
    } catch (_) {}
    return {
      username: "",
      password: "",
      can_number: "",
      aadhar_number: "",
    };
  });
  const [addressDetails, setAddressDetails] = useState(() => ({
    from_date: "",
    to_date: getTodayFormatted(),
  }));
  const [completedSteps, setCompletedSteps] = useState({ loggedIn: false, formFilled: false, docsUploaded: false, submitted: false });

  // ── Cleaner WebSocket event listener ──────────────────────────────────────────
  useEffect(() => {
    const onStatus = (e) => setDeleteSavedAppMsg(e.detail);
    const onDone = (e) => {
      setDeleteSavedAppMsg(e.detail || "Saved application deleted successfully!");
      setIsDeletingSavedApp(false);
      setTimeout(() => setDeleteSavedAppMsg(""), 7000);
    };
    const onError = (e) => {
      setDeleteSavedAppMsg(e.detail || "Failed to delete saved application");
      setIsDeletingSavedApp(false);
      setTimeout(() => setDeleteSavedAppMsg(""), 8000);
    };
    window.addEventListener("cleaner_status", onStatus);
    window.addEventListener("cleaner_done", onDone);
    window.addEventListener("cleaner_error", onError);
    return () => {
      window.removeEventListener("cleaner_status", onStatus);
      window.removeEventListener("cleaner_done", onDone);
      window.removeEventListener("cleaner_error", onError);
    };
  }, []);

  // ── Live Automation step progression tracking ──────────────────────────────────
  useEffect(() => {
    if (!automationStatus) return;
    const s = automationStatus.toLowerCase();

    // Ignore cleaner or developer tooling messages completely
    if (s.includes("cleaner") || s.includes("deleted") || s.includes("saved application")) {
      return;
    }

    const isStage1 =
      s.includes("otp verified") ||
      s.includes("loading the form") ||
      s.includes("filling in your application") ||
      s.includes("saving your address") ||
      s.includes("submitting the application") ||
      s.includes("starting document uploads") ||
      s.includes("uploading your") ||
      s.includes("all documents uploaded") ||
      s.includes("payment page reached");

    const isStage2 =
      s.includes("saving your address") ||
      s.includes("submitting the application") ||
      s.includes("starting document uploads") ||
      s.includes("uploading your") ||
      s.includes("all documents uploaded") ||
      s.includes("payment page reached");

    const isStage3 =
      s.includes("all documents uploaded") ||
      s.includes("going to payment") ||
      s.includes("payment page reached");

    const isStage4 =
      s.includes("payment page reached") ||
      (s.includes("done!") && s.includes("payment"));

    setCompletedSteps(prev => ({
      loggedIn:     prev.loggedIn     || isStage1,
      formFilled:   prev.formFilled   || isStage2,
      docsUploaded: prev.docsUploaded || isStage3,
      submitted:    prev.submitted    || isStage4,
    }));
  }, [automationStatus]);

  const documents = DOCUMENTS;

  const [supabaseDocUrls, setSupabaseDocUrls] = useState({});

  // ── Restore existing user documents from Supabase on mount ───────────────────
  const [savedProfileLoaded, setSavedProfileLoaded] = useState(false);
  const [savedProfile, setSavedProfile] = useState({});

  // ── Restore existing user profile & documents from Supabase on mount ──────────────
  useEffect(() => {
    const userPhone = sessionStorage.getItem("user_phone");
    if (!userPhone) return;

    fetch(`${import.meta.env.VITE_API_BASE}/user-profile?phone_number=${encodeURIComponent(userPhone)}`)
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data && data.status === "success" && data.data) {
          const profileData = data.data.profile || {};
          const docsMap     = data.data.documents || {};

          setSavedProfile(profileData);

          // 1. Restore credentials & address details
          const credsObj = profileData.credentials || {};
          const appObj   = profileData.applicant_details || {};
          const t1Obj    = profileData.tab1_credentials || {};
          const addrObj  = profileData.address_details || {};

          // Find extracted aadhaar and can from documents (e.g. from Aadhaar card OCR)
          let docAadhaar = "";
          let docCan = "";
          Object.values(docsMap).forEach(doc => {
            if (Array.isArray(doc?.extracted_data)) {
              doc.extracted_data.forEach(item => {
                const a = item?.aadhaar_number || item?.aadhar_number;
                if (a && !docAadhaar) docAadhaar = String(a).replace(/\D/g, "").slice(0, 12);
                const c = item?.can_number || item?.can;
                if (c && !docCan) docCan = String(c).trim();
              });
            }
          });

          const restoredUsername = credsObj.username || t1Obj.username || profileData.username || "";
          const restoredPassword = credsObj.password || t1Obj.password || profileData.password || "";
          const restoredCan      = credsObj.can_number || credsObj.can || appObj.can_number || appObj.can || t1Obj.can_number || t1Obj.can || profileData.can_number || profileData.can || docCan || "";
          const restoredAadhar   = credsObj.aadhar_number || credsObj.aadhaar_number || appObj.aadhar_number || appObj.aadhaar_number || t1Obj.aadhar_number || t1Obj.aadhaar_number || profileData.aadhar_number || profileData.aadhaar_number || docAadhaar || "";

          setCredentials(prev => {
            const next = {
              username:      restoredUsername || prev.username,
              password:      restoredPassword || prev.password,
              can_number:    restoredCan      || prev.can_number,
              aadhar_number: restoredAadhar   || prev.aadhar_number,
            };
            try { sessionStorage.setItem("tnega_draft_credentials", JSON.stringify(next)); } catch (_) {}
            return next;
          });

          setAddressDetails(prev => ({
            from_date: addrObj.from_date || prev.from_date,
            to_date:   prev.to_date || getTodayFormatted(), // always keep today's date, never restore old to_date
          }));

          // 2. Restore document checklist items & Supabase URLs
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
          }

          if (profileData.has_saved_profile || Object.keys(restoredChecked).length > 0) {
            setSavedProfileLoaded(true);
            console.log("[User Memory] Auto-restored user profile & documents from Supabase ✓");
          }
        }
      })
      .catch(err => console.warn("[User Memory] Error fetching restored user profile:", err));
  }, []);

  const handleCredChange = (e) => {
    const val = e.target.name === "aadhar_number" ? e.target.value.replace(/\D/g, "").slice(0, 12) : e.target.value;
    setCredentials(prev => {
      const next = { ...prev, [e.target.name]: val };
      try { sessionStorage.setItem("tnega_draft_credentials", JSON.stringify(next)); } catch (_) {}
      return next;
    });
  };
  const handleAddrChange = (e) => setAddressDetails({ ...addressDetails, [e.target.name]: e.target.value });

  const handleRemoveFile = (id) => {
    setUploadedFiles(p => { const u = { ...p }; delete u[id]; return u; });
    setRawFiles(p => { const u = { ...p }; delete u[id]; return u; });
    setExtractedData(p => { const u = { ...p }; delete u[id]; return u; });
    setSupabaseDocUrls(p => { const u = { ...p }; delete u[id]; return u; });
    setCheckedItems(p => ({ ...p, [id]: false }));
  };

  const handleClearSavedData = () => {
    setUploadedFiles({});
    setRawFiles({});
    setExtractedData({});
    setCheckedItems({ aadharCard: false, rationCard: false, photo: false, drivingLicense: false });
    setSupabaseDocUrls({});
    setSavedProfileLoaded(false);
    setSavedProfile({});
    setCredentials({ username: "", password: "", can_number: "", aadhar_number: "" });
    try { sessionStorage.removeItem("tnega_draft_credentials"); } catch (_) {}
    setAddressDetails({ from_date: "", to_date: getTodayFormatted() });
    fetch(`${import.meta.env.VITE_DOC_API_BASE}/clear-cache`, { method: "POST" }).catch(() => {});
  };

  // ── Portal Action: Delete Saved Application on portal ──────────────────
  const handleDeleteSavedApp = async () => {
    const un = (credentials?.username || "").trim();
    const pw = (credentials?.password || "").trim();
    if (!un || !pw) {
      setDeleteSavedAppMsg("Please enter your TNeSevai username and password in Step 1 first.");
      setTimeout(() => setDeleteSavedAppMsg(""), 5000);
      return;
    }
    const apiBase = (import.meta.env.VITE_API_BASE || "http://localhost:8001").replace(/\/$/, "");

    setIsDeletingSavedApp(true);
    setDeleteSavedAppMsg("Launching browser on portal…");

    try {
      if (onOpenSocket) {
        await onOpenSocket().catch(err => console.warn("[WebSocket] onOpenSocket warning:", err));
      }

      for (let i = 0; i < 8; i++) {
        try {
          const s = await fetch(`${apiBase}/ws/status`);
          const d = await s.json();
          if (d.connected) break;
        } catch (_) {}
        await new Promise(r => setTimeout(r, 300));
      }

      const res = await fetch(`${apiBase}/delete-saved-application`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          credentials: { username: un, password: pw }
        })
      });

      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }

      setDeleteSavedAppMsg("Cleaner running on portal. Enter captcha in modal if requested.");
    } catch (e) {
      console.error("[Cleaner Error]", e);
      setDeleteSavedAppMsg(`Failed to start cleaner: ${e.message || "Unknown error"}`);
      setIsDeletingSavedApp(false);
      setTimeout(() => setDeleteSavedAppMsg(""), 6000);
    }
  };

  const handleFileUpload = async (e, id) => {
    const file = e.target.files[0];
    if (!file) return;

    const isPhoto = id === "photo";
    const fileExt = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    const allowedPhotoExts = [".jpg", ".jpeg", ".png", ".webp"];
    const allowedDocExts = [".pdf", ".jpg", ".jpeg", ".png", ".webp"];

    if (isPhoto) {
      if (!allowedPhotoExts.includes(fileExt)) {
        setUploadError("Please upload a JPG or PNG photograph for face verification.");
        e.target.value = "";
        return;
      }
    } else {
      if (!allowedDocExts.includes(fileExt)) {
        setUploadError("Please upload an official PDF or high-quality image (JPG, PNG).");
        e.target.value = "";
        return;
      }
    }

    if (file.size > 5 * 1024 * 1024) {
      setUploadError("File size exceeds 5 MB. Please upload a file under 5 MB.");
      e.target.value = "";
      return;
    }

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
        if (id !== "photo" && data.extracted_data?.length > 0) {
          setExtractedData(p => ({ ...p, [id]: data.extracted_data }));
          if (id === "aadharCard" || id === "drivingLicense" || id === "addressProof" || id === "rationCard") {
            const ex = data.extracted_data.find(r => r && typeof r === "object") || {};
            setAddressDetails(prev => ({
              ...prev,
              village:     prev.village     || ex.area    || ex.taluk  || "",
              building_no: prev.building_no || ex.door_no || "",
              street_name: prev.street_name || ex.street  || ex.street_name || "",
              pincode:     prev.pincode     || ex.pincode || "",
            }));
            const detectedAadhaar = ex.aadhaar_number || ex.aadhar_number;
            if (detectedAadhaar) {
              const cleanAadhaar = String(detectedAadhaar).replace(/\D/g, "").slice(0, 12);
              setCredentials(prev => {
                const next = { ...prev, aadhar_number: prev.aadhar_number || cleanAadhaar };
                try { sessionStorage.setItem("tnega_draft_credentials", JSON.stringify(next)); } catch (_) {}
                return next;
              });
            }
            const detectedCan = ex.can_number || ex.can;
            if (detectedCan) {
              setCredentials(prev => {
                const next = { ...prev, can_number: prev.can_number || String(detectedCan).trim() };
                try { sessionStorage.setItem("tnega_draft_credentials", JSON.stringify(next)); } catch (_) {}
                return next;
              });
            }
          }
        }

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
    // Reset all step progress for fresh run
    setCompletedSteps({ loggedIn: false, formFilled: false, docsUploaded: false, submitted: false });
    if (onResetAutomationStatus) onResetAutomationStatus();
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

      const savedApplicant = savedProfile.applicant_details || {};
      const savedAddress   = savedProfile.address_details || {};
      const savedSupUrls   = savedProfile.supabase_urls || {};

      const orchPaths = bulkData.saved_paths || {};
      const supUrls   = { ...savedSupUrls, ...(bulkData.supabase_urls || {}), ...supabaseDocUrls };

      setBulkResults(bulkData.result || { combined: savedApplicant, confidence_score: 100 });
      const c = { ...savedApplicant, ...(bulkData.result?.combined || {}) };
      const aadharNum = (credentials.aadhar_number || c.aadhaar_number || c.aadhar_number || "").replace(/\s/g, "").slice(0, 12);
      const canNum    = (credentials.can_number || c.can_number || c.can || "").trim();

      if (aadharNum || canNum) {
        setCredentials(prev => {
          const next = {
            ...prev,
            aadhar_number: prev.aadhar_number || aadharNum,
            can_number: prev.can_number || canNum,
          };
          try { sessionStorage.setItem("tnega_draft_credentials", JSON.stringify(next)); } catch (_) {}
          return next;
        });
      }
      const isBadAddrVal = (val, appN, appF) => {
        if (!val) return true;
        const s = String(val).trim().toLowerCase();
        if (!s) return true;
        if (appN && s === String(appN).trim().toLowerCase()) return true;
        if (appF && s === String(appF).trim().toLowerCase()) return true;
        if (s.includes("c/o") || s.includes("s/o") || s.includes("d/o") || s.includes("w/o")) return true;
        return false;
      };

      const appNameVal = c.username || c.name || savedApplicant.name || "";
      const appFatherVal = c.father_name || savedApplicant.father_name || "";

      let doorVal = c.door_no || c.building_no || "";
      let streetVal = c.street_name || c.area || "";

      if ((!doorVal || !streetVal) && c.address && typeof c.address === "string") {
        const parts = c.address.split(",").map(s => s.trim()).filter(Boolean);
        if (parts.length > 0 && !doorVal && !isBadAddrVal(parts[0], appNameVal, appFatherVal)) {
          doorVal = parts[0];
        }
        if (parts.length > 1 && !streetVal && !isBadAddrVal(parts[1], appNameVal, appFatherVal)) {
          streetVal = parts[1];
        }
      }

      const validBldg = isBadAddrVal(doorVal, appNameVal, appFatherVal) ? (savedAddress.building_no || "") : doorVal;
      const validSt   = isBadAddrVal(streetVal, appNameVal, appFatherVal) ? (savedAddress.street_name || validBldg) : streetVal;
      const finalSt   = validSt || validBldg || "";

      const payload = {
        credentials: { username: credentials.username, password: credentials.password },
        applicant_details: {
          can_number: credentials.can_number || c.can_number || "",
          aadhar_number: aadharNum,
          dob: c.dob || savedApplicant.dob || "",
          ration_card_no: c.ration_card_number || c.ration_card_no || c.number || savedApplicant.ration_card_no || "",
          name: appNameVal,
          father_name: appFatherVal,
          gender: c.gender || savedApplicant.gender || "",
          religion: c.religion || savedApplicant.religion || "",
          community: c.community || savedApplicant.community || "",
          mobile_number: c.phone_number || c.mobile_number || savedApplicant.mobile_number || "",
          email: c.email || savedApplicant.email || ""
        },
        address_details: {
          state: c.state || savedAddress.state || "Tamil Nadu",
          district: c.district || savedAddress.district || "",
          village: c.taluk || c.district || savedAddress.village || "",
          area: isBadAddrVal(c.area, appNameVal, appFatherVal) ? "" : (c.area || savedAddress.area || ""),
          building_no: validBldg,
          street_name: finalSt,
          pincode: c.pincode || savedAddress.pincode || "",
          from_date: addressDetails.from_date || savedAddress.from_date || "",
          to_date: addressDetails.to_date || savedAddress.to_date || getTodayFormatted(),
          perm_state: c.state || savedAddress.perm_state || "Tamil Nadu",
          perm_district: c.district || savedAddress.perm_district || "",
          perm_village: c.taluk || c.district || savedAddress.perm_village || "",
          perm_building_no: validBldg,
          perm_street_name: finalSt,
          perm_pincode: c.pincode || savedAddress.perm_pincode || ""
        },
        documents: {
          photo_path:
            supUrls.Photo || supUrls.photo || supUrls.photo_path ||
            orchPaths.Photo || orchPaths.photo || orchPaths.photo_path || "",
          self_decl_path: "",
          aadhaar_path:
            supUrls.Aadhaar || supUrls.aadhaar || supUrls.aadharCard ||
            orchPaths.Aadhaar || orchPaths.aadhaar || orchPaths.aadharCard || "",
          address_proof_path:
            supUrls["Driving License"] || supUrls.drivingLicense || supUrls.driving ||
            supUrls["Ration Card"] || supUrls.rationCard || supUrls.ration ||
            supUrls.Aadhaar || supUrls.aadharCard || supUrls.aadhaar ||
            orchPaths["Driving License"] || orchPaths.drivingLicense || orchPaths.driving ||
            orchPaths["Ration Card"] || orchPaths.rationCard || orchPaths.ration ||
            orchPaths.Aadhaar || orchPaths.aadharCard || orchPaths.aadhaar || "",
          address_doc_no:
            c.dl_number || c.driving_license_number || c.driving_licence_number ||
            c.license_number || c.ration_card_number || c.smart_card_no ||
            c.aadhaar_number || c.aadhar_number || savedApplicant.address_doc_no || ""
        },
      };

      const apiBase = (import.meta.env.VITE_API_BASE || "http://localhost:8001").replace(/\/$/, "");
      if (onOpenSocket) {
        await onOpenSocket().catch(err => console.warn("[WebSocket] onOpenSocket warning:", err));
      }

      // Verify WebSocket connectivity to backend (up to ~5 seconds)
      let wsReady = false;
      for (let i = 0; i < 12; i++) {
        try {
          const s = await fetch(`${apiBase}/ws/status`);
          const d = await s.json();
          if (d.connected) {
            wsReady = true;
            break;
          }
        } catch (_) {}
        await new Promise(r => setTimeout(r, 400));
      }

      if (!wsReady) {
        console.warn("[WebSocket] Live socket not detected within 5s; proceeding with submission as backend queues events.");
      }

      const submitRes = await fetch(`${apiBase}/submit-application`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!submitRes.ok) throw new Error(`Automation server error (HTTP ${submitRes.status}).`);
    } catch (e) {
      setSubmitError(e.message || "An unexpected error occurred.");
      setIsExtracting(false);
    }
  };

  // ── Success / automation live screen ────────────────────────────────────────
  if (bulkResults) {
    const isDone = automationStatus && (
      (automationStatus.toLowerCase().includes("done!") && automationStatus.toLowerCase().includes("payment")) ||
      automationStatus.toLowerCase().includes("payment page reached") ||
      automationStatus.toLowerCase().includes("went wrong")
    );
    const isError = automationStatus && automationStatus.toLowerCase().includes("went wrong");

    const handleLiveClose = () => {
      setBulkResults(null);
      setCompletedSteps({ loggedIn: false, formFilled: false, docsUploaded: false, submitted: false });
      if (onResetAutomationStatus) onResetAutomationStatus();
      if (onExit) onExit();
    };

    return (
      <div className="cl-card fade-up" style={{ maxHeight: "none", marginBottom: "2rem" }}>
        <div className="cl-live-header">
          <div className={`cl-live-icon ${isDone ? (isError ? "error" : "done") : "running"}`} style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
            {isDone ? (isError ? <LuTriangleAlert size={16} /> : <LuCheck size={16} />) : <span className="cl-spin-ring" />}
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
              <div className="cl-step-dot" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
                {s.done ? <LuCheck size={11} /> : i + 1}
              </div>
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
          <button className="btn-secondary" onClick={handleLiveClose}>Close</button>
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
    <div className="cl-card fade-up" style={{
      background: "#141414",
      border: "1px solid #2a2a2a",
      borderRadius: "1.25rem",
      padding: "1.5rem",
      maxHeight: "none",
      overflow: "visible",
      marginBottom: "2.5rem",
      boxSizing: "border-box"
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "0.5rem", marginBottom: "1.25rem" }}>
        <h3 className="cl-title" style={{ margin: 0, color: "#fff" }}>TNeSevai Application Details</h3>
        <button
          type="button"
          disabled={isDeletingSavedApp}
          onClick={handleDeleteSavedApp}
          style={{
            background: "rgba(239, 68, 68, 0.12)",
            border: "1px solid rgba(239, 68, 68, 0.4)",
            color: "#fca5a5",
            borderRadius: "9999px",
            padding: "0.35rem 0.85rem",
            fontSize: "0.78rem",
            fontWeight: 600,
            cursor: isDeletingSavedApp ? "not-allowed" : "pointer",
            display: "inline-flex",
            alignItems: "center",
            gap: "0.4rem",
            transition: "all 0.2s",
          }}
          title="Log into portal and delete pending Saved Applications"
        >
          {isDeletingSavedApp ? <LuLoader size={13} style={{ animation: "spin 1s linear infinite" }} /> : <MdDeleteOutline size={14} />}
          <span>{isDeletingSavedApp ? "Deleting on Portal…" : "Clear Saved Draft"}</span>
        </button>
      </div>

      {deleteSavedAppMsg && (
        <div style={{
          background: "rgba(168, 85, 247, 0.12)",
          border: "1px solid rgba(168, 85, 247, 0.35)",
          borderRadius: "0.75rem",
          padding: "0.6rem 0.9rem",
          marginBottom: "1rem",
          color: "#c084fc",
          fontSize: "0.82rem",
          display: "flex",
          alignItems: "center",
          gap: "0.5rem"
        }}>
          {isDeletingSavedApp && <LuLoader size={14} style={{ animation: "spin 1s linear infinite" }} />}
          <span>{deleteSavedAppMsg}</span>
        </div>
      )}

      {savedProfileLoaded && (
        <div style={{
          background: "rgba(52, 211, 153, 0.1)",
          border: "1px solid rgba(52, 211, 153, 0.3)",
          borderRadius: "0.75rem",
          padding: "0.75rem 1rem",
          marginBottom: "1rem",
          color: "#34d399",
          fontSize: "0.85rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "0.5rem"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <LuCircleCheck size={16} /> Welcome back! Your profile details and uploaded documents were loaded from Supabase.
          </div>
          <button
            type="button"
            onClick={handleClearSavedData}
            style={{
              background: "rgba(239, 68, 68, 0.15)",
              border: "1px solid rgba(239, 68, 68, 0.4)",
              color: "#fca5a5",
              borderRadius: "9999px",
              padding: "0.3rem 0.75rem",
              fontSize: "0.75rem",
              fontWeight: 600,
              cursor: "pointer",
              flexShrink: 0
            }}
          >
            Clear &amp; Start Fresh
          </button>
        </div>
      )}

      <StepBar current={step} total={STEPS.length} steps={STEPS} />

      {/* ── Step 0: Portal Credentials ── */}
      {step === 0 && (
        <div style={sectionStyle}>
          <div style={sectionLabel}>Portal Credentials</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
            <FloatingInput label="TNeSevai Username" name="username"      value={credentials.username}      onChange={handleCredChange} autoComplete="username" />
            <FloatingInput label="Password"          name="password"      type="password" value={credentials.password} onChange={handleCredChange} autoComplete="current-password" />
            <FloatingInput label="CAN Number"        name="can_number"    value={credentials.can_number}    onChange={handleCredChange} autoComplete="off" />
            <FloatingInput label="Aadhar Number *"   name="aadhar_number" value={credentials.aadhar_number} onChange={handleCredChange} maxLength={12} autoComplete="off" />
          </div>

          <div style={{
            marginTop: "1rem", paddingTop: "0.75rem",
            borderTop: "1px dashed rgba(255,255,255,0.08)",
            display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "0.5rem"
          }}>
            <span style={{ fontSize: "0.75rem", color: "#a855f7", fontWeight: 600, display: "flex", alignItems: "center", gap: "0.35rem" }}>
              <LuWrench size={13} /> Portal Utility
            </span>
            <button
              type="button"
              disabled={isDeletingSavedApp}
              onClick={handleDeleteSavedApp}
              style={{
                background: "rgba(239, 68, 68, 0.12)",
                border: "1px solid rgba(239, 68, 68, 0.4)",
                color: "#fca5a5",
                borderRadius: "0.5rem",
                padding: "0.35rem 0.75rem",
                fontSize: "0.75rem",
                fontWeight: 600,
                cursor: isDeletingSavedApp ? "not-allowed" : "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "0.35rem"
              }}
              title="Delete draft Saved Application on portal"
            >
              {isDeletingSavedApp ? <LuLoader size={12} style={{ animation: "spin 1s linear infinite" }} /> : <MdDeleteOutline size={13} />}
              <span>{isDeletingSavedApp ? "Deleting on Portal…" : "Clear Draft on Portal"}</span>
            </button>
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
            Ensure all required documents are ready for upload:
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
                                <LuLock size={12} /> PIN Download
                              </button>
                              <button className="cl-remove-btn" onClick={() => handleRemoveFile(doc.id)}><MdDeleteOutline size={17} /></button>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <label className="upload-zone" style={{ opacity: isUploading[doc.id] ? 0.6 : 1 }}>
                          <input
                            type="file"
                            accept={doc.id === "photo" ? "image/jpeg,image/png,image/jpg" : ".pdf,application/pdf,image/jpeg,image/png,image/jpg"}
                            onChange={e => handleFileUpload(e, doc.id)}
                            disabled={isUploading[doc.id]}
                            hidden
                          />
                          <div className="upload-zone-icon"><MdOutlineCloudUpload size={22} /></div>
                          <p className="cl-upload-title">{isUploading[doc.id] ? "Uploading…" : `Upload ${doc.label}`}</p>
                          <p className="cl-upload-sub">{doc.id === "photo" ? "JPG or PNG · max 5 MB" : "Official PDF or image · max 5 MB"}</p>
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
