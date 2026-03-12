import { useState } from "react";
import { MdOutlineCloudUpload, MdDeleteOutline } from "react-icons/md";

// ── Reusable floating-label input ─────────────────────────────────────────────
function FloatingInput({ label, name, type = "text", value, onChange, maxLength }) {
  const [focused, setFocused] = useState(false);
  const active = focused || !!value;

  return (
    <div style={{ position: "relative", flex: "1", minWidth: "180px" }}>
      <label
        style={{
          position: "absolute",
          left: active ? "10px" : "12px",
          top: active ? "-9px" : "50%",
          transform: active ? "translateY(0)" : "translateY(-50%)",
          fontSize: active ? "11px" : "14px",
          color: active ? "#b8860b" : "#999",
          backgroundColor: "#f9f9f9",
          padding: active ? "0 4px" : "0",
          pointerEvents: "none",
          transition: "top 0.18s ease, font-size 0.18s ease, color 0.18s ease, padding 0.18s ease, left 0.18s ease",
          fontWeight: active ? 500 : 400,
          zIndex: 1,
          whiteSpace: "nowrap",
        }}
      >
        {label}
      </label>
      <input
        type={type}
        name={name}
        value={value}
        onChange={onChange}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        maxLength={maxLength}
        style={{
          width: "100%",
          padding: "10px 12px",
          borderRadius: "8px",
          border: `1px solid ${focused ? "#b8860b" : "#ccc"}`,
          backgroundColor: "#f9f9f9",
          fontSize: "14px",
          color: "#333",
          outline: "none",
          transition: "border-color 0.18s ease",
          boxSizing: "border-box",
        }}
      />
    </div>
  );
}
// ─────────────────────────────────────────────────────────────────────────────

export default function DocumentChecklist({ onProceed, onExit, isProceeding, onOpenSocket }) {
  const [checkedItems, setCheckedItems] = useState({
    aadharCard: false,
    rationCard: false,
    photo: false,
    drivingLicense: false,
  });

  const [expandedItem, setExpandedItem] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState({});
  const [rawFiles, setRawFiles] = useState({});
  const [extractedData, setExtractedData] = useState({});
  const [isUploading, setIsUploading] = useState({});
  const [uploadError, setUploadError] = useState(null);

  const [bulkResults, setBulkResults] = useState(null);
  const [playwrightPayload, setPlaywrightPayload] = useState(null);
  const [submitError, setSubmitError] = useState(null);

  const [credentials, setCredentials] = useState({
    username: "",
    password: "",
    can_number: "",
    aadhar_number: ""
  });

  const [addressDetails, setAddressDetails] = useState({
    village: "",
    building_no: "",
    street_name: "",
    pincode: "",
    from_date: "",
    to_date: ""
  });

  const documents = [
    { id: "aadharCard", label: "Aadhar card" },
    { id: "rationCard", label: "Ration card" },
    { id: "photo", label: "Applicant Photograph" },
    { id: "drivingLicense", label: "Driving license" },
  ];

  const handleCredChange = (e) => setCredentials({ ...credentials, [e.target.name]: e.target.value });
  const handleAddrChange = (e) => setAddressDetails({ ...addressDetails, [e.target.name]: e.target.value });

  const toggleExpand = (id) => {
    setExpandedItem((prev) => (prev === id ? null : id));
    setUploadError(null);
  };

  const handleRemoveFile = (id) => {
    setUploadedFiles((prev) => { const u = { ...prev }; delete u[id]; return u; });
    setRawFiles((prev) => { const u = { ...prev }; delete u[id]; return u; });
    setExtractedData((prev) => { const u = { ...prev }; delete u[id]; return u; });
    setCheckedItems((prev) => ({ ...prev, [id]: false }));
  };

  const handleFileUpload = async (e, id) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsUploading((prev) => ({ ...prev, [id]: true }));
    setUploadError(null);

    const formData = new FormData();
    formData.append("file", file);

    const extUrl =
      id === "photo"
        ? "http://localhost:8002/verify/photo"
        : "http://localhost:8002/extract";

    try {
      const response = await fetch(extUrl, { method: "POST", body: formData });

      if (response.ok) {
        const data = await response.json();

        if (id === "photo" && data.is_human_photo === false) {
          throw new Error("Invalid Photograph. Please ensure the image clearly shows a human person.");
        }

        if (id !== "photo" && data.extracted_data && data.extracted_data.length > 0) {
          setExtractedData((prev) => ({ ...prev, [id]: data.extracted_data }));
        }

        setUploadedFiles((prev) => ({ ...prev, [id]: file.name }));
        setRawFiles((prev) => ({ ...prev, [id]: file }));
        setCheckedItems((prev) => ({ ...prev, [id]: true }));
        setExpandedItem(null);
      } else {
        throw new Error("Server error handling upload.");
      }
    } catch (err) {
      console.error("Upload failed:", err);
      setUploadError(err.message || "Upload Failed. Please try again.");
    } finally {
      setIsUploading((prev) => ({ ...prev, [id]: false }));
    }
  };

  const isAllChecked = Object.values(checkedItems).every(Boolean);

  const handleProceedClick = async () => {
    setSubmitError(null);

    // Open WebSocket NOW — before any fetch calls — so it's ready when
    // Playwright sends its first event (REQUEST_CAPTCHA usually comes within seconds)
    if (onOpenSocket) onOpenSocket();

    const formData = new FormData();
    if (rawFiles.aadharCard) formData.append("aadhaar", rawFiles.aadharCard);
    if (rawFiles.rationCard) formData.append("ration", rawFiles.rationCard);
    if (rawFiles.drivingLicense) formData.append("driving", rawFiles.drivingLicense);
    if (rawFiles.photo) formData.append("photo", rawFiles.photo);

    try {
      // Step 1: Extract & validate all documents
      const bulkRes = await fetch("http://localhost:8002/process-all", { method: "POST", body: formData });
      if (!bulkRes.ok) throw new Error(`Document extraction failed (HTTP ${bulkRes.status})`);
      const bulkData = await bulkRes.json();

      if (bulkData.status === "success" && bulkData.result) {
        console.log("Bulk Validation Results:", bulkData.result);
        setBulkResults(bulkData.result);
        const combined = bulkData.result.combined;

        // Step 2: Build payload matching EXACT default_json_payload field names
        const aadharNum = (credentials.aadhar_number || (combined.aadhaar_number || "")).replace(/\s/g, '');
        const payload = {
          credentials: {
            username: credentials.username,
            password: credentials.password
          },
          applicant_details: {
            can_number:     credentials.can_number   || "",
            aadhar_number:  aadharNum,
            dob:            combined.dob             || "",
            ration_card_no: combined.ration_card_number || "",
            name:           combined.username        || "",
            father_name:    combined.father_name     || "",
            gender:         combined.gender          || "",
            religion:       combined.religion        || "",
            community:      combined.community       || "",
            mobile_number:  combined.phone_number    || "",
            email:          combined.email           || ""
          },
          address_details: {
            state:        combined.state        || "Tamil Nadu",
            district:     combined.district     || "",
            village:      combined.taluk        || combined.district || "",
            area:         combined.area         || "",
            building_no:  combined.door_no      || "",
            street_name:  combined.street_name  || combined.area   || "",
            pincode:      combined.pincode      || "",
            from_date:    addressDetails.from_date,
            to_date:      addressDetails.to_date,
            // Permanent address (same as current by default)
            perm_state:        combined.state        || "Tamil Nadu",
            perm_district:     combined.district     || "",
            perm_village:      combined.taluk        || combined.district || "",
            perm_building_no:  combined.door_no      || "",
            perm_street_name:  combined.street_name  || combined.area   || "",
            perm_pincode:      combined.pincode      || ""
          },
          documents: {
            photo_path:            bulkData.saved_paths?.["Photo"]   || "",
            self_decl_path:        "",
            address_proof_path:    bulkData.saved_paths?.["Aadhaar"] || "",
            driving_license_path:  bulkData.saved_paths?.["Driving License"] || "",
            address_doc_no:        aadharNum
          }
        };

        console.log("Submitting payload to Playwright:", payload);
        setPlaywrightPayload(payload);

        // Step 3: Fire Playwright — runs in background on the server
        const submitRes = await fetch("http://localhost:8000/submit-application", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (!submitRes.ok) {
          throw new Error(`Automation server error (HTTP ${submitRes.status}). Is the ORCHESTRA backend running on port 8000?`);
        }

        console.log("Playwright agent started.");

        // Step 4: Notify parent component (closes checklist, shows success state)
        if (onProceed) await onProceed();

      } else {
        throw new Error("Document extraction returned no results. Please check your uploaded files.");
      }
    } catch (e) {
      console.error("Failed to process or submit application:", e);
      setSubmitError(e.message || "An unexpected error occurred. Please try again.");
    }
  };


  const isFormValid = isAllChecked &&
                      credentials.username &&
                      credentials.password &&
                      addressDetails.from_date &&
                      addressDetails.to_date;

  if (bulkResults) {
    const p = playwrightPayload;
    const sectionStyle = {
      backgroundColor: "#fff",
      border: "1px solid #e8e8e8",
      borderRadius: "10px",
      padding: "14px 16px",
      marginBottom: "12px",
    };
    const headingStyle = {
      fontSize: "12px",
      fontWeight: 700,
      textTransform: "uppercase",
      letterSpacing: "0.06em",
      color: "#b8860b",
      marginBottom: "10px",
      display: "flex",
      alignItems: "center",
      gap: "6px",
    };
    const rowStyle = {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      fontSize: "13px",
      padding: "4px 0",
      borderBottom: "1px solid #f2f2f2",
    };
    const labelStyle = { color: "#666", fontWeight: 500 };
    const valueStyle = { color: "#222", fontWeight: 600, textAlign: "right", maxWidth: "60%", wordBreak: "break-all" };
    const badge = (src) => (
      <span style={{
        fontSize: "10px", fontWeight: 600, padding: "2px 6px", borderRadius: "10px", marginLeft: "6px",
        backgroundColor: src === "extracted" ? "#e8f5e9" : "#e3f2fd",
        color:            src === "extracted" ? "#2e7d32"  : "#1565c0",
      }}>{src === "extracted" ? "📄 Extracted" : "✏️ Input"}</span>
    );
    const Row = ({ label, value, src }) => (
      <div style={rowStyle}>
        <span style={labelStyle}>{label}{src && badge(src)}</span>
        <span style={valueStyle}>{value || <span style={{color:"#ccc"}}>—</span>}</span>
      </div>
    );

    return (
      <div className="document-checklist-container" style={{ maxHeight: "72vh", overflowY: "auto" }}>
        <h3 style={{ marginBottom: "4px" }}>✅ Processing Complete</h3>
        <p style={{ fontSize: "13px", color: "#777", marginBottom: "16px" }}>
          Review the data sent to Playwright below. Automation has started in the background.
        </p>

        {/* ── Validation Summary ── */}
        <div style={{ ...sectionStyle, backgroundColor: "#fffdf0", border: "1px solid #f0d080" }}>
          <div style={headingStyle}>📊 Validation Summary</div>
          <Row label="Name Match"       value={`${bulkResults.validation?.name_similarity?.toFixed(1) ?? "—"}%`} />
          <Row label="DOB Match"        value={bulkResults.validation?.dob_match ? "✅ Yes" : "❌ No"} />
          <Row label="Confidence Score" value={`${bulkResults.confidence_score ?? "—"}%`} />
          <div style={{ ...rowStyle, borderBottom: "none" }}>
            <span style={labelStyle}>Status</span>
            <span style={{
              fontWeight: 700, fontSize: "13px",
              color: bulkResults.validation?.name_match ? "#2e7d32" : "#e65100"
            }}>
              {bulkResults.validation?.name_match ? "APPROVED" : "REVIEW REQUIRED"}
            </span>
          </div>
        </div>

        {/* ── Credentials ── */}
        {p && (
          <>
            <div style={sectionStyle}>
              <div style={headingStyle}>🔐 Portal Credentials</div>
              <Row label="Username" value={p.credentials?.username} src="input" />
              <Row label="Password" value={"•".repeat((p.credentials?.password || "").length)} src="input" />
            </div>

            {/* ── Applicant Details ── */}
            <div style={sectionStyle}>
              <div style={headingStyle}>👤 Applicant Details</div>
              <Row label="Name"            value={p.applicant_details?.name}           src="extracted" />
              <Row label="Father Name"     value={p.applicant_details?.father_name}    src="extracted" />
              <Row label="Gender"          value={p.applicant_details?.gender}         src="extracted" />
              <Row label="Religion"        value={p.applicant_details?.religion}       src="extracted" />
              <Row label="Community"       value={p.applicant_details?.community}      src="extracted" />
              <Row label="CAN Number"      value={p.applicant_details?.can_number}     src="input" />
              <Row label="Aadhaar Number"  value={p.applicant_details?.aadhar_number}  src="input" />
              <Row label="Date of Birth"   value={p.applicant_details?.dob}            src="extracted" />
              <Row label="Ration Card No"  value={p.applicant_details?.ration_card_no} src="extracted" />
              <Row label="Mobile Number"   value={p.applicant_details?.mobile_number}  src="extracted" />
              <Row label="Email"           value={p.applicant_details?.email}          src="extracted" />
            </div>

            {/* ── Address Details ── */}
            <div style={sectionStyle}>
              <div style={headingStyle}>🏠 Current Address Details</div>
              <Row label="State"           value={p.address_details?.state}        src="extracted" />
              <Row label="District"        value={p.address_details?.district}     src="extracted" />
              <Row label="Village / Taluk" value={p.address_details?.village}      src="extracted" />
              <Row label="Area / Locality" value={p.address_details?.area}         src="extracted" />
              <Row label="Building No"     value={p.address_details?.building_no}  src="extracted" />
              <Row label="Street Name"     value={p.address_details?.street_name}  src="extracted" />
              <Row label="Pincode"         value={p.address_details?.pincode}      src="extracted" />
              <Row label="Residing From"   value={p.address_details?.from_date}    src="input" />
              <Row label="Residing To"     value={p.address_details?.to_date}      src="input" />
            </div>

            {/* ── Documents ── */}
            <div style={sectionStyle}>
              <div style={headingStyle}>📎 Documents Being Uploaded</div>
              <Row label="Photo"           value={p.documents?.photo_path?.split(/[\\/]/).pop()}         src="extracted" />
              <Row label="Self-Declaration" value={p.documents?.self_decl_path?.split(/[\\/]/).pop() || "—"} />
              <Row label="Address Proof"   value={p.documents?.address_proof_path?.split(/[\\/]/).pop()} src="extracted" />
              <Row label="Address Doc No"  value={p.documents?.address_doc_no}                           src="extracted" />
            </div>
          </>
        )}

        <div className="checklist-actions">
          <div style={{ flex: 1, fontSize: "13px", color: "#555", display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ color: "#4caf50", fontSize: "18px" }}>●</span>
            Playwright automation is running in the background.
          </div>
          <button className="btn-exit" onClick={onExit}>Close</button>
        </div>
      </div>
    );
  }



  return (
    <div className="document-checklist-container" style={{maxHeight: '70vh', overflowY: 'auto'}}>
      <h3>TNeSevai Application Details</h3>

      {/* ── Section 1: Portal Credentials ── */}
      <form onSubmit={(e) => e.preventDefault()} autoComplete="on">
      <div className="input-section" style={{marginBottom: "20px", padding: "15px", backgroundColor: "#fff", borderRadius: "8px"}}>
        <h4>1. Portal Credentials</h4>
        <div style={{display: "flex", gap: "10px", marginTop: "10px", flexWrap: "wrap"}}>
          <FloatingInput label="TNeSevai Username" name="username" value={credentials.username} onChange={handleCredChange} />
          <FloatingInput label="Password" name="password" type="password" value={credentials.password} onChange={handleCredChange} />
          <FloatingInput label="CAN Number" name="can_number" value={credentials.can_number} onChange={handleCredChange} />
          <FloatingInput label="Aadhar Number *" name="aadhar_number" value={credentials.aadhar_number} onChange={handleCredChange} maxLength={12} />
        </div>
      </div>
      </form>

      {/* ── Section 2: Residency Constraints ── */}
      <div className="input-section" style={{marginBottom: "20px", padding: "15px", backgroundColor: "#fff", borderRadius: "8px"}}>
        <h4>2. Residency Constraints</h4>
        <div style={{display: "flex", gap: "10px", marginTop: "10px", flexWrap: "wrap"}}>
          <FloatingInput label="Residing From (DD/MM/YYYY)" name="from_date" value={addressDetails.from_date} onChange={handleAddrChange} />
          <FloatingInput label="Residing To (DD/MM/YYYY)" name="to_date" value={addressDetails.to_date} onChange={handleAddrChange} />
        </div>
      </div>

      {/* ── Section 3: Document Checklist ── */}
      <h3>3. Document Checklist</h3>
      <p>Please ensure you have all the required documents ready for extraction & upload:</p>
      <div className="checklist-items">
        {documents.map((doc) => (
          <div key={doc.id} className={`checklist-item-wrapper ${checkedItems[doc.id] ? "checked" : ""}`}>
            <div className="checklist-item-header" onClick={() => toggleExpand(doc.id)}>
              <div className="checklist-left">
                <span className={`checkbox-custom ${checkedItems[doc.id] ? "checked" : ""}`}></span>
                <span className="checklist-label">{doc.label}</span>
              </div>
              <span className="expand-icon">{expandedItem === doc.id ? "▲" : "▼"}</span>
            </div>

            {expandedItem === doc.id && (
              <div className="checklist-dropdown">
                {uploadedFiles[doc.id] ? (
                  <div className="file-success-container">
                    <div className="file-success">
                      <div className="file-success-info">
                        <span className="check-icon">✓</span>
                        <span className="file-name">{uploadedFiles[doc.id]}</span>
                      </div>
                      <button className="btn-remove-file" onClick={() => handleRemoveFile(doc.id)} title="Remove document">
                        <MdDeleteOutline />
                      </button>
                    </div>
                    {extractedData[doc.id] && extractedData[doc.id].map((extract, idx) => (
                      <div key={idx} className="extracted-data-card">
                        <h4 style={{ margin: "5px 0", fontSize: "14px", color: "#333" }}>{extract.certificate_type} Details</h4>
                        <ul style={{ listStyleType: "none", padding: 0, margin: 0, fontSize: "13px", color: "#555" }}>
                          {Object.entries(extract.extracted_fields || extract)
                            .filter(([k]) => k !== "certificate_type")
                            .map(([key, value]) => (
                              <li key={key} style={{ marginBottom: "3px" }}><strong>{key.replace(/_/g, ' ').toUpperCase()}:</strong> {value}</li>
                            ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="upload-area">
                    <MdOutlineCloudUpload className="upload-area-icon" />
                    <div className="upload-text-container">
                      <p className="upload-prompt">Upload your {doc.label}</p>
                      <p className="upload-subprompt">PDF, JPG, or PNG (max 5MB)</p>
                    </div>
                    {uploadError && <p className="upload-error">{uploadError}</p>}
                    <label className="upload-btn-local">
                      {isUploading[doc.id] ? "Uploading..." : "Browse Files"}
                      <input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(e) => handleFileUpload(e, doc.id)} disabled={isUploading[doc.id]} hidden />
                    </label>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {submitError && (
        <div style={{
          margin: "10px 0",
          padding: "10px 14px",
          backgroundColor: "#fff3cd",
          border: "1px solid #ffc107",
          borderRadius: "8px",
          color: "#856404",
          fontSize: "13px",
          lineHeight: "1.5"
        }}>
          ⚠️ {submitError}
        </div>
      )}

      <div className="checklist-actions">
        <button className="btn-exit" onClick={onExit} disabled={isProceeding}>Exit</button>
        <button
          className={`btn-proceed ${isProceeding ? "loading" : ""}`}
          onClick={handleProceedClick}
          disabled={!isFormValid || isProceeding}
        >
          {isProceeding ? "Processing..." : "Proceed"}
        </button>
      </div>
    </div>
  );
}

// ── Style constants ────────────────────────────────────────────────────────────
const inputStyles = {
  flex: "1",
  padding: "10px 12px",
  borderRadius: "6px",
  border: "1px solid #ccc",
  backgroundColor: "#f9f9f9",
  color: "#333",
  fontSize: "14px"
};

