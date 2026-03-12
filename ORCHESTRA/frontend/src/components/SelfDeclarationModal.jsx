import { useState } from "react";

export default function SelfDeclarationModal({ isOpen, downloadPath, onSubmit, onExit }) {
  const [uploadedFile, setUploadedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);

  if (!isOpen) return null;

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setUploadedFile(file);
    }
  };

  const handleSubmit = async () => {
    if (!uploadedFile) {
      alert("Please upload the signed Self-Declaration form first!");
      return;
    }

    setIsUploading(true);
    
    try {
      // Upload the signed file to backend
      const formData = new FormData();
      formData.append("file", uploadedFile);
      
      const response = await fetch("http://localhost:8000/upload-signed-declaration", {
        method: "POST",
        body: formData
      });
      
      if (!response.ok) {
        throw new Error("Failed to upload signed declaration");
      }
      
      const data = await response.json();
      console.log("Signed declaration uploaded:", data);
      
      // Send the saved file path back to Playwright
      onSubmit(data.file_path);
    } catch (error) {
      console.error("Error uploading signed declaration:", error);
      alert("Failed to upload signed declaration. Please try again.");
      setIsUploading(false);
    }
  };

  const handleDownload = () => {
    // Trigger download of the form
    window.open(`http://localhost:8000/download-declaration`, '_blank');
  };

  return (
    <div style={{
      position: "fixed",
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: "rgba(0, 0, 0, 0.7)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 9999,
    }}>
      <div style={{
        backgroundColor: "#fff",
        borderRadius: "12px",
        padding: "30px",
        maxWidth: "500px",
        width: "90%",
        boxShadow: "0 10px 40px rgba(0,0,0,0.3)",
      }}>
        <h2 style={{ marginTop: 0, color: "#b8860b", fontSize: "22px" }}>
          📄 Self-Declaration Form
        </h2>
        
        <p style={{ color: "#555", lineHeight: "1.6", marginBottom: "20px" }}>
          The Self-Declaration Form has been generated. Please follow these steps:
        </p>

        <ol style={{ color: "#333", lineHeight: "1.8", paddingLeft: "20px" }}>
          <li>Download the form using the button below</li>
          <li>Print the form</li>
          <li>Sign it manually</li>
          <li>Scan or photograph the signed form</li>
          <li>Upload the signed version below</li>
        </ol>

        <button
          onClick={handleDownload}
          style={{
            width: "100%",
            padding: "12px",
            backgroundColor: "#4CAF50",
            color: "white",
            border: "none",
            borderRadius: "8px",
            fontSize: "16px",
            fontWeight: "600",
            cursor: "pointer",
            marginBottom: "20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "8px",
          }}
        >
          <span>⬇️</span> Download Self-Declaration Form
        </button>

        <div style={{
          border: "2px dashed #ccc",
          borderRadius: "8px",
          padding: "20px",
          textAlign: "center",
          marginBottom: "20px",
          backgroundColor: "#f9f9f9",
        }}>
          {uploadedFile ? (
            <div>
              <p style={{ color: "#4CAF50", fontWeight: "600", margin: "10px 0" }}>
                ✓ {uploadedFile.name}
              </p>
              <button
                onClick={() => setUploadedFile(null)}
                style={{
                  padding: "6px 12px",
                  backgroundColor: "#ff5252",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontSize: "14px",
                }}
              >
                Remove
              </button>
            </div>
          ) : (
            <div>
              <p style={{ color: "#666", marginBottom: "10px" }}>
                Upload Signed Self-Declaration Form
              </p>
              <label style={{
                display: "inline-block",
                padding: "10px 20px",
                backgroundColor: "#2196F3",
                color: "white",
                borderRadius: "6px",
                cursor: "pointer",
                fontSize: "14px",
                fontWeight: "600",
              }}>
                Choose File
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={handleFileUpload}
                  style={{ display: "none" }}
                />
              </label>
              <p style={{ fontSize: "12px", color: "#999", marginTop: "10px" }}>
                Supported: PDF, JPG, PNG (max 5MB)
              </p>
            </div>
          )}
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button
            onClick={onExit}
            disabled={isUploading}
            style={{
              flex: 1,
              padding: "12px",
              backgroundColor: "#757575",
              color: "white",
              border: "none",
              borderRadius: "8px",
              fontSize: "16px",
              fontWeight: "600",
              cursor: isUploading ? "not-allowed" : "pointer",
              opacity: isUploading ? 0.6 : 1,
            }}
          >
            Exit
          </button>
          <button
            onClick={handleSubmit}
            disabled={!uploadedFile || isUploading}
            style={{
              flex: 2,
              padding: "12px",
              backgroundColor: uploadedFile && !isUploading ? "#b8860b" : "#ccc",
              color: "white",
              border: "none",
              borderRadius: "8px",
              fontSize: "16px",
              fontWeight: "600",
              cursor: uploadedFile && !isUploading ? "pointer" : "not-allowed",
            }}
          >
            {isUploading ? "Uploading..." : "Submit Signed Form"}
          </button>
        </div>
      </div>
    </div>
  );
}
