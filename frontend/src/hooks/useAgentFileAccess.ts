/**
 * useAgentFileAccess — Password-gated file decryption for agent use
 *
 * When the agent needs to process a file (extraction, verification, etc.),
 * the user must authorize with their password first.
 * The agent NEVER receives the encrypted blob — only the decrypted bytes
 * after the user explicitly consents.
 */

import { useState } from "react";
import { supabase } from "../lib/supabase";
import { deriveKEK, unwrapMEK, decryptFile } from "../lib/crypto";

export interface AgentFileRequest {
  /** The original File object the user attached */
  file: File;
  /** doc_type hint for the agent (aadhaar, driving_license, photograph, etc.) */
  docType: string;
  /** Optional message text accompanying the file */
  message?: string;
  /** Session ID for the RAG pipeline */
  sessionId?: string;
}

export interface AgentFileResult {
  /** Agent's response message */
  agentMessage: string;
  /** Whether the agent processed the file successfully */
  success: boolean;
  /** Full raw JSON response from the agent */
  data?: any;
}

export function useAgentFileAccess() {
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(null);

  /**
   * Verify password, decrypt the file, then send plaintext to the agent.
   * Returns the agent's response, or null if password was wrong.
   */
  async function authorizeAndSend(
    request: AgentFileRequest,
    password: string,
  ): Promise<AgentFileResult | null> {
    setError(null);
    setLoading(true);

    try {
      // 1. Get current user
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) { setError("Not logged in."); return null; }

      // 2. Fetch crypto meta
      const { data: meta } = await supabase
        .from("user_crypto_meta")
        .select("salt, wrapped_mek")
        .eq("user_id", user.id)
        .single();

      if (!meta) { setError("Encryption keys not found."); return null; }

      // 3. Re-derive KEK from password and unwrap MEK
      //    Throws if password is wrong — agent access denied
      let mek: CryptoKey;
      try {
        const kek = await deriveKEK(password, meta.salt);
        mek = await unwrapMEK(meta.wrapped_mek, kek);
      } catch {
        setError("Incorrect password. Agent access denied.");
        return null;
      }

      // 4. Decrypt the file in the browser
      //    The agent only ever receives the plaintext — never the encrypted blob
      let plainBlob: Blob;
      try {
        // If the file came from Supabase storage (already encrypted), decrypt it
        // If it's a freshly attached file (not yet encrypted), use it directly
        const isEncrypted = request.file.name.endsWith("-encrypted") ||
                            request.file.type === "application/octet-stream";

        if (isEncrypted) {
          plainBlob = await decryptFile(request.file, mek, "application/octet-stream");
        } else {
          // Fresh file — not yet encrypted, send as-is to agent
          plainBlob = request.file;
        }
      } catch {
        setError("Failed to decrypt file for agent processing.");
        return null;
      }

      // 5. Send decrypted plaintext to the RAG agent
      const form = new FormData();
      form.append("file", plainBlob, request.file.name);
      form.append("doc_type", request.docType);
      if (request.sessionId) form.append("session_id", request.sessionId);
      if (request.message)   form.append("message",    request.message);
      if (user?.id)          form.append("user_id",    user.id);

      // Only call RAG if we have a session — otherwise just confirm encrypted storage
      if (!request.sessionId) {
        return {
          agentMessage: `🔒 **${request.file.name}** encrypted and stored securely. Start a chat session to have the assistant process it.`,
          success: true,
        };
      }

      const res = await fetch("/api/upload", { method: "POST", body: form });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setError(err.message ?? "Agent processing failed.");
        return { agentMessage: err.message ?? "Processing failed.", success: false };
      }

      const data = await res.json();
      return {
        agentMessage: data.message ?? `✅ ${request.file.name} processed.`,
        success: true,
        data,
      };
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Agent access failed");
      return null;
    } finally {
      setLoading(false);
    }
  }

  return { authorizeAndSend, loading, error };
}
