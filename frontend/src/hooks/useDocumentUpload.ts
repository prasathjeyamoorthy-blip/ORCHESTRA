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
      // 1. Encrypt the file in the browser
      const encryptedBlob = await encryptFile(file, mek);

      // 2. Build storage path
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) { onNotLoggedIn(); return null; }

      const uuid        = crypto.randomUUID();
      const storagePath = `${user.id}/${uuid}-encrypted`;

      // 3. Upload encrypted blob to private bucket
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

      // 4. Save metadata directly to DB (RLS ensures user_id matches)
      const { data: meta, error: metaErr } = await supabase
        .from("document_meta")
        .insert({
          user_id:            user.id,
          storage_path:       storagePath,
          original_filename:  file.name,
          original_mime_type: file.type || "application/octet-stream",
          file_size_bytes:    file.size,
        })
        .select("id")
        .single();

      if (metaErr) {
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
