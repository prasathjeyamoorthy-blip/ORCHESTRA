import { useState, useEffect } from "react";
import { MdOutlineCloudUpload, MdDeleteOutline } from "react-icons/md";
import { LuCircleCheck, LuChevronDown, LuChevronUp, LuTriangleAlert, LuChevronLeft, LuChevronRight, LuCheck, LuLoader } from "react-icons/lu";

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

// ── Floating label input ──────────────────────────────────────────────────────
function FloatingInput({ label, name, type = "text", value, onChange, maxLength }) {
  const [focused, setFocused] = useState(false);
  const active = focused || !!value;
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
      }}>{label}</label>
      <input
        type={type} name={name} value={value} onChange={onChange}
        onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}
        maxLength={maxLength}
        style={{
          width: "100%", boxSizing: "border-box",
          padding: "0.75rem 0.875rem", paddingTop: active ? "1.1rem" : "0.75rem",
          background: C.surface2,
          border: `1.5px solid ${focused ? "rgba(255,255,255,0.4)" : C.border}`,
          borderRadius: "0.625rem", color: C.text, fontSize: 14,
          outline: "none", fontFamily: "inherit",
          boxShadow: focused ? "0 0 0 3px rgba(255,255,255,0.06)" : "none",
          transition: "border-color 0.18s, box-shadow 0.18s",
        }}
      />
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
            <span style={{
              fontSize: 10, marginTop: 5, fontWeight: i === current ? 700 : 400,
              color: i === current ? "#ffffff" : C.text3,
              whiteSpace: "nowrap",
            }}>{s.title}</span>
          </div>
        ))}
      </div>
      <div style={{ height: 3, background: "#2a2a2a", borderRadius: 99, overflow: "hidden", marginTop: 4 }}>
        <div style={{
          height: "100%", background: "#ffffff", borderRadius: 99,
          width: `${(current / (total - 1)) * 100}%`,
          transition: "width 0.3s ease",
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
export default function DocumentChecklist({ onProceed, onExit, isProceeding, onOpenSocket, automationStatus }) {
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

  const handleCredChange = (e) => setCredentials({ ...credentials, [e.target.name]: e.target.value });
  const handleAddrChange = (e) => setAddressDetails({ ...addressDetails, [e.target.name]: e.target.value });

  const handleRemoveFile = (id) => {
    setUploadedFiles(p => { const u = { ...p }; delete u[id]; return u; });
    setRawFiles(p => { const u = { ...p }; delete u[id]; return u; });
    setExtractedData(p => { const u = { ...p }; delete u[id]; return u; });
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
        setUploadedFiles(p => ({ ...p, [id]: file.name }));
        setRawFiles(p => ({ ...p, [id]: file }));
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

  const isAllChecked  = Object.values(checkedItems).every(Boolean);
  const canNext = [
    credentials.username && credentials.password,
    addressDetails.from_date && addressDetails.to_date,
    isAllChecked,
  ][step];

  const handleProceedClick = async () => {
    setSubmitError(null);
    setIsExtracting(true);
    const extractForm = new FormData();
    if (rawFiles.aadharCard)     extractForm.append("aadhaar", rawFiles.aadharCard);
    if (rawFiles.rationCard)     extractForm.append("ration",  rawFiles.rationCard);
    if (rawFiles.drivingLicense) extractForm.append("driving", rawFiles.drivingLicense);
    if (rawFiles.photo)          extractForm.append("photo",   rawFiles.photo);
    try {
      const bulkRes = await fetch(`${import.meta.env.VITE_DOC_API_BASE}/process-all`, { method: "POST", body: extractForm });
      if (!bulkRes.ok) throw new Error(`Document extraction failed (HTTP ${bulkRes.status})`);
      const bulkData = await bulkRes.json();
      if (!(bulkData.status === "success" && bulkData.result)) throw new Error("Document extraction returned no results.");

      const uploadForm = new FormData();
      if (rawFiles.aadharCard)     uploadForm.append("aadhaar", rawFiles.aadharCard);
      if (rawFiles.rationCard)     uploadForm.append("ration",  rawFiles.rationCard);
      if (rawFiles.drivingLicense) uploadForm.append("driving", rawFiles.drivingLicense);
      if (rawFiles.photo)          uploadForm.append("photo",   rawFiles.photo);
      const uploadRes = await fetch(`${import.meta.env.VITE_DOC_API_BASE}/upload-documents`, { method: "POST", body: uploadForm });
      if (!uploadRes.ok) throw new Error(`File upload failed (HTTP ${uploadRes.status})`);
      const uploadData = await uploadRes.json();
      const orchPaths = uploadData.saved_paths || {};

      setBulkResults(bulkData.result);
      const c = bulkData.result.combined;
      const aadharNum = (credentials.aadhar_number || c.aadhaar_number || "").replace(/\s/g, "");
      const payload = {
        credentials: { username: credentials.username, password: credentials.password },
        applicant_details: { can_number: credentials.can_number || "", aadhar_number: aadharNum, dob: c.dob || "", ration_card_no: c.ration_card_number || "", name: c.username || "", father_name: c.father_name || "", gender: c.gender || "", religion: c.religion || "", community: c.community || "", mobile_number: c.phone_number || "", email: c.email || "" },
        address_details: { state: c.state || "Tamil Nadu", district: c.district || "", village: c.taluk || c.district || "", area: c.area || "", building_no: c.door_no || "", street_name: c.street_name || c.area || "", pincode: c.pincode || "", from_date: addressDetails.from_date, to_date: addressDetails.to_date, perm_state: c.state || "Tamil Nadu", perm_district: c.district || "", perm_village: c.taluk || c.district || "", perm_building_no: c.door_no || "", perm_street_name: c.street_name || c.area || "", perm_pincode: c.pincode || "" },
        documents: { photo_path: orchPaths.photo || "", self_decl_path: "", aadhaar_path: orchPaths.aadhaar || "", address_proof_path: orchPaths.driving || orchPaths.ration || "", address_doc_no: c.dl_number || "" },
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
        <div className="cl-actions" style={{ marginTop: "1.25rem" }}>
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
    <div className="cl-card fade-up" style={{ background: "#141414", border: "1px solid #2a2a2a" }}>
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
            <FloatingInput label="Residing From (DD/MM/YYYY)" name="from_date" value={addressDetails.from_date} onChange={handleAddrChange} />
            <FloatingInput label="Residing To (DD/MM/YYYY)"   name="to_date"   value={addressDetails.to_date}   onChange={handleAddrChange} />
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
                            <button className="cl-remove-btn" onClick={() => handleRemoveFile(doc.id)}><MdDeleteOutline size={17} /></button>
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
        <div className="cl-error-block" style={{ marginTop: "0.75rem" }}>
          <LuTriangleAlert size={16} /> {submitError}
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
