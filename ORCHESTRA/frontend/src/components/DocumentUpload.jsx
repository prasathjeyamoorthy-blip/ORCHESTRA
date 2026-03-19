import { MdOutlineDocumentScanner } from "react-icons/md";

export default function DocumentUpload({ onFileSelect }) {
  const handleChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

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
    <label className="document-upload-icon" title="Upload document">
      <MdOutlineDocumentScanner className="upload-icon" />

      <input
        type="file"
        accept=".pdf,.jpg,.jpeg,.png"
        onChange={handleChange}
        hidden
      />
    </label>
  );
}
