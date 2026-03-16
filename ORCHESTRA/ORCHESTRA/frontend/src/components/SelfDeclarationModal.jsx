import { useState } from "react";
import { LuFilePen, LuDownload } from "react-icons/lu";

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
      onSubmit(data.file_path);
    } catch (error) {
      alert("Failed to upload signed declaration. Please try again.");
      setIsUploading(false);
    }
  };

  const handleDownload = () => {
    window.open(`http://localhost:8000/download-declaration`, '_blank');
  };

  return (
    <div className="overlay">
      <div className="modal-card" style={{ maxWidth: '32rem' }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: "2.5rem", height: "2.5rem", borderRadius: "0.75rem", backgroundColor: "hsl(var(--primary)/0.1)", color: "hsl(var(--primary))" }}>
            <LuFilePen size={24} />
          </div>
          <h2 style={{ fontSize: "1.25rem", fontWeight: 700, margin: 0, color: "hsl(var(--foreground))" }}>
            Self-Declaration Form
          </h2>
        </div>
        
        <p style={{ color: "hsl(var(--muted-foreground))", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
          The Self-Declaration Form has been generated. Please follow these steps:
        </p>

        <ol style={{ fontSize: "0.875rem", color: "hsl(var(--foreground))", paddingLeft: "1.5rem", marginBottom: "1.5rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          <li>Download the form using the button below</li>
          <li>Print the form</li>
          <li>Sign it manually</li>
          <li>Scan or photograph the signed form</li>
          <li>Upload the signed version below</li>
        </ol>

        <button
          onClick={handleDownload}
          className="btn-primary"
          style={{ width: "100%", marginBottom: "1.5rem" }}
        >
          <LuDownload size={16} /> Download Self-Declaration Form
        </button>

        <div style={{ border: "1.5px dashed hsl(var(--border))", borderRadius: "1rem", padding: "1.5rem", textAlign: "center", marginBottom: "1.5rem", backgroundColor: "hsl(var(--secondary)/0.5)", transition: "all 0.2s" }} className="hover:border-primary/50">
          {uploadedFile ? (
            <div>
              <p style={{ color: "hsl(var(--primary))", fontWeight: 600, fontSize: "0.875rem", marginBottom: "0.5rem" }}>
                ✓ {uploadedFile.name}
              </p>
              <button
                onClick={() => setUploadedFile(null)}
                className="btn-secondary"
                style={{ color: "hsl(var(--destructive))", borderColor: "hsl(var(--destructive)/0.2)", backgroundColor: "hsl(var(--destructive)/0.05)" }}
              >
                Remove
              </button>
            </div>
          ) : (
            <div>
              <p style={{ color: "hsl(var(--foreground))", fontWeight: 500, fontSize: "0.875rem", marginBottom: "0.75rem" }}>
                Upload Signed Self-Declaration Form
              </p>
              <label style={{ display: "inline-block", cursor: "pointer" }}>
                <span className="btn-secondary">Choose File</span>
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={handleFileUpload}
                  style={{ display: "none" }}
                />
              </label>
              <p style={{ fontSize: "0.75rem", color: "hsl(var(--muted-foreground))", marginTop: "0.75rem", marginBottom: 0 }}>
                Supported: PDF, JPG, PNG (max 5MB)
              </p>
            </div>
          )}
        </div>

        <div style={{ display: "flex", gap: "0.75rem" }}>
          <button onClick={onExit} disabled={isUploading} className="btn-secondary" style={{ flex: 1 }}>
            Exit
          </button>
          <button onClick={handleSubmit} disabled={!uploadedFile || isUploading} className="btn-primary" style={{ flex: 2 }}>
            {isUploading ? "Uploading..." : "Submit Signed Form"}
          </button>
        </div>
      </div>
    </div>
  );
}
