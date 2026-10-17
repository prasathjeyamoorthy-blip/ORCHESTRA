import { MdOutlineDocumentScanner } from "react-icons/md";

export default function DocumentUpload({ onFileSelect }) {
  const handleChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      console.warn("❌ Only PDF documents are accepted to prevent extraction hallucination.");
      return;
    }

    // keep existing behavior
    onFileSelect(file);

    // send file to RAG agent backend
    const formData = new FormData();
    formData.append("file", file);
  
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE}/upload`, {
        method: "POST",
        body: formData
      });

      const data = await response.json();
      console.log("📦 Extracted JSON from backend:", data);
    } catch (err) {
      console.error("❌ Document upload failed:", err);
    }
  };

  return (
    <label className="document-upload-icon" title="Upload PDF document">
      <MdOutlineDocumentScanner className="upload-icon" />

      <input
        type="file"
        accept=".pdf,application/pdf"
        onChange={handleChange}
        hidden
      />
    </label>
  );
}
