import { useState } from "react";
import { MdOutlineCloudUpload, MdDeleteOutline } from "react-icons/md";

export default function DocumentChecklist({ onProceed, onExit, isProceeding }) {
  const [checkedItems, setCheckedItems] = useState({
    photo: false,
    addressProof: false,
    selfDeclaration: false,
  });

  const [expandedItem, setExpandedItem] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState({});
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  const documents = [
    { id: "photo", label: "Applicant Photograph" },
    {
      id: "addressProof",
      label: "Current Address Proof (Eg: Driving License)",
    },
    { id: "selfDeclaration", label: "Self Declaration of Applicant" },
  ];

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
    setCheckedItems((prev) => ({ ...prev, [id]: false }));
  };

  const handleFileUpload = async (e, id) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append("file", file);

    const extUrl =
      id === "photo"
        ? "http://localhost:8000/verify/photo"
        : "http://localhost:8000/upload";

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
      setIsUploading(false);
    }
  };

  const isAllChecked = Object.values(checkedItems).every(Boolean);

  const handleProceedClick = async () => {
    if (onProceed) {
      await onProceed();
    }
  };

  return (
    <div className="document-checklist-container">
      <h3>Document Checklist</h3>
      <p>Please ensure you have all the required documents ready for upload:</p>
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
                      {isUploading ? "Uploading..." : "Browse Files"}
                      <input
                        type="file"
                        accept=".pdf,.jpg,.jpeg,.png"
                        onChange={(e) => handleFileUpload(e, doc.id)}
                        disabled={isUploading}
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
          disabled={!isAllChecked || isProceeding}
        >
          {isProceeding ? "Proceeding..." : "Proceed"}
        </button>
      </div>
    </div>
  );
}
