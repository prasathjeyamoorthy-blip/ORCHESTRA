import { useState } from "react";
import { MdOutlineCloudUpload, MdDeleteOutline } from "react-icons/md";

export default function DocumentChecklist({ onProceed, onExit, isProceeding }) {
  const [checkedItems, setCheckedItems] = useState({
    aadharCard: false,
    rationCard: false,
    photo: false,
    drivingLicense: false,
  });

  const [expandedItem, setExpandedItem] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState({});
  const [extractedData, setExtractedData] = useState({});
  const [isUploading, setIsUploading] = useState({});
  const [uploadError, setUploadError] = useState(null);

  // New states for User Input
  const [credentials, setCredentials] = useState({
    username: "",
    password: "",
    can_number: ""
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
    setUploadError(null); // Clear errors when navigating
  };

  const handleRemoveFile = (id) => {
    setUploadedFiles((prev) => {
      const updated = { ...prev };
      delete updated[id];
      return updated;
    });
    setExtractedData((prev) => {
      const updated = { ...prev };
      delete updated[id];
      return updated;
    });
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
      const response = await fetch(extUrl, {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();

        // Specific photograph verification logic
        if (id === "photo" && data.is_human_photo === false) {
          throw new Error(
            "Invalid Photograph. Please ensure the image clearly shows a human person.",
          );
        }

        if (id !== "photo" && data.extracted_data && data.extracted_data.length > 0) {
          setExtractedData((prev) => ({ ...prev, [id]: data.extracted_data }));
        }

        // Mark as uploaded and immediately check the item
        setUploadedFiles((prev) => ({ ...prev, [id]: file.name }));
        setCheckedItems((prev) => ({ ...prev, [id]: true }));
        // Collapse once successfully uploaded
        setExpandedItem(null);
      } else {
        throw new Error("Server error handling upload.");
      }
    } catch (err) {
      console.error("Upload failed:", err);
      // Fallback message if err doesn't have a readable desc
      setUploadError(err.message || "Upload Failed. Please try again.");
    } finally {
      setIsUploading((prev) => ({ ...prev, [id]: false }));
    }
  };

  const isAllChecked = Object.values(checkedItems).every(Boolean);

  const handleProceedClick = async () => {
    // Helper to extract fields from either nested "extracted_fields" or flat payload
    const getFields = (docType) => {
      if (extractedData[docType] && extractedData[docType].length > 0) {
        return extractedData[docType][0].extracted_fields || extractedData[docType][0] || {};
      }
      return {};
    };

    const aFields = getFields("aadharCard");
    const rFields = getFields("rationCard");
    const dlFields = getFields("drivingLicense");
    
    let canStr = credentials.can_number || ""; // Dynamic CAN Number
    let aadharStr = aFields.aadhaar_number || aFields.aadhar_number || "";
    let rationStr = rFields.ration_card_number || "";
    
    // Look for DOB in Aadhaar, fallback to Driving License, then Ration Card
    let dobStr = aFields.dob || dlFields.dob || rFields.dob || "";

    // Build the payload
    const payload = {
      credentials: credentials,
      applicant_details: {
        can_number: canStr,
        aadhar_number: aadharStr.replace(/\s/g, ''),
        dob: dobStr,
        ration_card_no: rationStr
      },
      address_details: {
        village: aFields.village_town || aFields.city || aFields.taluk || dlFields.village_town || "",
        building_no: aFields.building_number || aFields.door_no || dlFields.door_number || "",
        street_name: aFields.street_name || aFields.street || aFields.area || dlFields.street || "",
        pincode: aFields.pincode || dlFields.pincode || rFields.pincode || "",
        from_date: addressDetails.from_date,
        to_date: addressDetails.to_date
      },
      documents: {
        photo_path: uploadedFiles.photo ? `e:/DESKTOP/ORCHESTRA_NEW/ORCHESTRA/DocumentUploadAgent/uploads/${uploadedFiles.photo}` : "",
        self_decl_path: "",  // Dynamic, Playwright handles the download and signing flow
        address_proof_path: uploadedFiles.aadharCard ? `e:/DESKTOP/ORCHESTRA_NEW/ORCHESTRA/DocumentUploadAgent/uploads/${uploadedFiles.aadharCard}` : "",
        address_doc_no: aadharStr.replace(/\s/g, '')
      }
    };

    try {
      await fetch("http://localhost:8000/submit-application", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
    } catch (e) {
      console.error("Failed to submit to playwright endpoint", e);
    }

    if (onProceed) {
      await onProceed();
    }
  };

  const isFormValid = isAllChecked && 
                      credentials.username && 
                      credentials.password &&
                      addressDetails.from_date &&
                      addressDetails.to_date;

  return (
    <div className="document-checklist-container" style={{maxHeight: '70vh', overflowY: 'auto'}}>
      <h3>TNeSevai Application Details</h3>
      
      <div className="input-section" style={{marginBottom: "20px", padding: "15px", backgroundColor: "#fff", borderRadius: "8px"}}>
        <h4>1. Portal Credentials</h4>
        <div style={{display: "flex", gap: "10px", marginTop: "10px", flexWrap: "wrap"}}>
           <input type="text" name="username" placeholder="TNeSevai Username" value={credentials.username} onChange={handleCredChange} style={inputStyles} />
           <input type="password" name="password" placeholder="Password" value={credentials.password} onChange={handleCredChange} style={inputStyles} />
           <input type="text" name="can_number" placeholder="Enter CAN Number" value={credentials.can_number} onChange={handleCredChange} style={inputStyles} />
        </div>
      </div>

      <div className="input-section" style={{marginBottom: "20px", padding: "15px", backgroundColor: "#fff", borderRadius: "8px"}}>
        <h4>2. Residency Constraints</h4>
        <div style={{display: "flex", gap: "10px", marginTop: "10px", flexWrap: "wrap"}}>
           <div style={{display: "flex", gap: "5px", alignItems: "center", width: "100%"}}>
             <label style={{fontSize: "12px", color: "#666"}}>Residing From:</label>
             <input type="text" name="from_date" placeholder="DD/MM/YYYY" value={addressDetails.from_date} onChange={handleAddrChange} style={inputStyles} />
           </div>
           
           <div style={{display: "flex", gap: "5px", alignItems: "center", width: "100%"}}>
             <label style={{fontSize: "12px", color: "#666"}}>Residing To:</label>
             <input type="text" name="to_date" placeholder="DD/MM/YYYY" value={addressDetails.to_date} onChange={handleAddrChange} style={inputStyles} />
           </div>
        </div>
      </div>

      <h3>3. Document Checklist</h3>
      <p>Please ensure you have all the required documents ready for extraction & upload:</p>
      <div className="checklist-items">
        {documents.map((doc) => (
          <div
            key={doc.id}
            className={`checklist-item-wrapper ${checkedItems[doc.id] ? "checked" : ""}`}
          >
            <div
              className="checklist-item-header"
              onClick={() => toggleExpand(doc.id)}
            >
              <div className="checklist-left">
                <span
                  className={`checkbox-custom ${checkedItems[doc.id] ? "checked" : ""}`}
                ></span>
                <span className="checklist-label">{doc.label}</span>
              </div>
              <span className="expand-icon">
                {expandedItem === doc.id ? "▲" : "▼"}
              </span>
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
                      <button
                        className="btn-remove-file"
                        onClick={() => handleRemoveFile(doc.id)}
                        title="Remove document"
                      >
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
                      <p className="upload-subprompt">
                        PDF, JPG, or PNG (max 5MB)
                      </p>
                    </div>
                    {uploadError && (
                      <p className="upload-error">{uploadError}</p>
                    )}
                    <label className="upload-btn-local">
                      {isUploading[doc.id] ? "Uploading..." : "Browse Files"}
                      <input
                        type="file"
                        accept=".pdf,.jpg,.jpeg,.png"
                        onChange={(e) => handleFileUpload(e, doc.id)}
                        disabled={isUploading[doc.id]}
                        hidden
                      />
                    </label>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="checklist-actions">
        <button className="btn-exit" onClick={onExit} disabled={isProceeding}>
          Exit
        </button>
        <button
          className={`btn-proceed ${isProceeding ? "loading" : ""}`}
          onClick={handleProceedClick}
          disabled={!isFormValid || isProceeding}
        >
          {isProceeding ? "Proceeding..." : "Proceed"}
        </button>
      </div>
    </div>
  );
}

const inputStyles = {
  flex: "1",
  padding: "10px 12px",
  borderRadius: "6px",
  border: "1px solid #ccc",
  backgroundColor: "#f9f9f9",
  color: "#333",
  fontSize: "14px"
};
