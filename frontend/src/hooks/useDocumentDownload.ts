import { useState } from "react";
import { supabase } from "../lib/supabase";
import { decryptFile, deriveKEK, unwrapMEK } from "../lib/crypto";
import { getSessionKey } from "../lib/keySession";

export interface DocumentMeta {
  id: string;
  storagePath: string;
  originalFilename: string;
  originalMimeType: string;
  fileSizeBytes: number;
  createdAt: string;
}

export function useDocumentDownload() {
  const [downloading, setDownloading] = useState(false);
  const [error,       setError]       = useState<string | null>(null);

  /** Fetch all documents for the current user. */
  async function listDocuments(onNotLoggedIn: () => void): Promise<DocumentMeta[]> {
    const mek = getSessionKey();
    if (!mek) { onNotLoggedIn(); return []; }

    const { data: { user } } = await supabase.auth.getUser();
    if (!user) { onNotLoggedIn(); return []; }

    const { data, error } = await supabase
      .from("document_meta")
      .select("id, storage_path, original_filename, original_mime_type, file_size_bytes, created_at")
      .eq("user_id", user.id)        // always scope to current user
      .order("created_at", { ascending: false });

    if (error || !data) return [];

    return data.map(row => ({
      id:               row.id,
      storagePath:      row.storage_path,
      originalFilename: row.original_filename,
      originalMimeType: row.original_mime_type,
      fileSizeBytes:    row.file_size_bytes,
      createdAt:        row.created_at,
    }));
  }

  /**
   * Download and decrypt a document.
   * Requires the user's password to re-derive the KEK and unwrap the MEK.
   * This means even if the session is compromised, files can't be downloaded
   * without the password.
   */
  async function download(
    doc: DocumentMeta,
    password: string,
    onNotLoggedIn: () => void,
  ): Promise<boolean> {
    setError(null);
    setDownloading(true);

    try {
      // 1. Get current user
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) { onNotLoggedIn(); return false; }

      // 2. Fetch crypto meta from DB
      const { data: meta } = await supabase
        .from("user_crypto_meta")
        .select("salt, wrapped_mek")
        .eq("user_id", user.id)
        .single();

      if (!meta) {
        setError("Encryption keys not found.");
        return false;
      }

      // 3. Re-derive KEK from password and unwrap MEK
      //    This verifies the password — throws if wrong
      let mek: CryptoKey;
      try {
        const kek = await deriveKEK(password, meta.salt);
        mek = await unwrapMEK(meta.wrapped_mek, kek);
      } catch {
        setError("Incorrect password.");
        return false;
      }

      // 4. Get signed URL for the encrypted blob
      const { data: signedData, error: signErr } = await supabase.storage
        .from("documents")
        .createSignedUrl(doc.storagePath, 60);

      if (signErr || !signedData?.signedUrl) {
        setError("Could not generate download link.");
        return false;
      }

      // 5. Fetch encrypted blob
      const blobRes = await fetch(signedData.signedUrl);
      if (!blobRes.ok) { setError("Download failed."); return false; }
      const encryptedBlob = await blobRes.blob();

      // 6. Decrypt with the freshly unwrapped MEK
      let plainBlob: Blob;
      try {
        plainBlob = await decryptFile(encryptedBlob, mek, doc.originalMimeType);
      } catch (e: unknown) {
        if (e instanceof Error && e.name === "DECRYPTION_FAILED") {
          setError("Unable to decrypt this file. Please try logging out and back in.");
        } else {
          setError("Decryption failed.");
        }
        return false;
      }

      // 7. Trigger browser download
      const url = URL.createObjectURL(plainBlob);
      const a   = document.createElement("a");
      a.href     = url;
      a.download = doc.originalFilename;
      a.click();
      URL.revokeObjectURL(url);

      return true;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Download failed");
      return false;
    } finally {
      setDownloading(false);
    }
  }

  /**
   * Delete a document — removes the encrypted blob from Storage
   * and the metadata row from document_meta.
   */
  async function deleteDocument(
    doc: DocumentMeta,
    onNotLoggedIn: () => void,
  ): Promise<boolean> {
    setError(null);

    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) { onNotLoggedIn(); return false; }

      // 1. Delete encrypted blob from Storage
      const { error: storageErr } = await supabase.storage
        .from("documents")
        .remove([doc.storagePath]);

      if (storageErr) {
        // Non-fatal — blob may already be gone; proceed to clean up metadata
        console.warn("[deleteDocument] Storage remove error:", storageErr.message);
      }

      // 2. Delete metadata row — this is the source of truth for the UI list
      const { error: dbErr } = await supabase
        .from("document_meta")
        .delete()
        .eq("id", doc.id)
        .eq("user_id", user.id);   // RLS double-check

      if (dbErr) {
        setError("Failed to delete document record.");
        return false;
      }

      return true;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Delete failed");
      return false;
    }
  }

  return { listDocuments, download, deleteDocument, downloading, error };
}
