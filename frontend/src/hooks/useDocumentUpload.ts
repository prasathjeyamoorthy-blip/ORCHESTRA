import { useState } from "react";
import { supabase } from "../lib/supabase";
import { encryptFile } from "../lib/crypto";
import { getSessionKey } from "../lib/keySession";

export interface UploadedDocument {
  id: string;
  storagePath: string;
  originalFilename: string;
  originalMimeType: string;
  fileSizeBytes: number;
}

const MAX_DOCUMENTS = 4;

/** Compute a SHA-256 hex digest of the file's raw bytes in the browser */
async function computeFileHash(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest("SHA-256", buffer);
  return Array.from(new Uint8Array(hashBuffer))
    .map(b => b.toString(16).padStart(2, "0"))
    .join("");
}

export function useDocumentUpload() {
  const [uploading, setUploading] = useState(false);
  const [error,     setError]     = useState<string | null>(null);

  async function upload(
    file: File,
    onNotLoggedIn: () => void,
  ): Promise<UploadedDocument | null> {
    setError(null);

    const mek = getSessionKey();
    if (!mek) { onNotLoggedIn(); return null; }

    setUploading(true);
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) { onNotLoggedIn(); return null; }

      // ── 1. Check document count limit ────────────────────────
      const { count } = await supabase
        .from("document_meta")
        .select("id", { count: "exact", head: true })
        .eq("user_id", user.id);

      if ((count ?? 0) >= MAX_DOCUMENTS) {
        setError(`Maximum ${MAX_DOCUMENTS} documents allowed. Delete an existing document first.`);
        return null;
      }

      // ── 2. Compute hash of original file bytes ────────────────
      const fileHash = await computeFileHash(file);

      // ── 3. Check for duplicate by hash ───────────────────────
      const { data: existing } = await supabase
        .from("document_meta")
        .select("id, original_filename")
        .eq("user_id", user.id)
        .eq("file_hash", fileHash)
        .limit(1);

      if (existing && existing.length > 0) {
        setError(
          `This document is already stored (${existing[0].original_filename}). ` +
          `Duplicate uploads are not allowed.`
        );
        return null;
      }

      // ── 4. Encrypt the file in the browser ───────────────────
      const encryptedBlob = await encryptFile(file, mek);

      // ── 5. Build storage path and upload ─────────────────────
      const uuid        = crypto.randomUUID();
      const storagePath = `${user.id}/${uuid}-encrypted`;

      const { error: uploadErr } = await supabase.storage
        .from("documents")
        .upload(storagePath, encryptedBlob, {
          contentType: "application/octet-stream",
          upsert:      false,
        });

      if (uploadErr) {
        setError("Upload failed: " + uploadErr.message);
        return null;
      }

      // ── 6. Save metadata with hash ───────────────────────────
      const { data: meta, error: metaErr } = await supabase
        .from("document_meta")
        .insert({
          user_id:            user.id,
          storage_path:       storagePath,
          original_filename:  file.name,
          original_mime_type: file.type || "application/octet-stream",
          file_size_bytes:    file.size,
          file_hash:          fileHash,
        })
        .select("id")
        .single();

      if (metaErr) {
        // Clean up uploaded blob if metadata save fails
        await supabase.storage.from("documents").remove([storagePath]);
        setError("Metadata save failed: " + metaErr.message);
        return null;
      }

      return {
        id:               meta.id,
        storagePath,
        originalFilename: file.name,
        originalMimeType: file.type,
        fileSizeBytes:    file.size,
      };
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed");
      return null;
    } finally {
      setUploading(false);
    }
  }

  return { upload, uploading, error };
}
