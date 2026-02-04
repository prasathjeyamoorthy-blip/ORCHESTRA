import { MdOutlineDocumentScanner } from "react-icons/md";

export default function DocumentUpload({ onFileSelect }) {
  const handleChange = (e) => {
    const file = e.target.files[0];
    if (file) onFileSelect(file);
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
