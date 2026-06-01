import { useState } from "react";
import { supabase } from "../lib/supabase";
import { deriveKEK, rewrapMEK, unwrapMEK } from "../lib/crypto";
import { setSessionKey } from "../lib/keySession";

export function useChangePassword() {
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function changePassword(currentPassword: string, newPassword: string): Promise<boolean> {
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) { setError("Not logged in."); return false; }

      // 1. Fetch crypto meta from DB
      const { data: meta, error: dbErr } = await supabase
        .from("user_crypto_meta")
        .select("salt, wrapped_mek")
        .eq("user_id", user.id)
        .single();

      if (dbErr || !meta) { setError("Could not load encryption keys."); return false; }

      // 2. Derive old + new KEK (same salt)
      const oldKEK = await deriveKEK(currentPassword, meta.salt);
      const newKEK = await deriveKEK(newPassword,     meta.salt);

      // 3. Re-wrap MEK — throws if current password wrong
      let newWrappedMEK: string;
      try {
        newWrappedMEK = await rewrapMEK(meta.wrapped_mek, oldKEK, newKEK);
      } catch {
        setError("Current password is incorrect.");
        return false;
      }

      // 4. Update wrapped MEK in DB
      const { error: updateErr } = await supabase
        .from("user_crypto_meta")
        .update({ wrapped_mek: newWrappedMEK, updated_at: new Date().toISOString() })
        .eq("user_id", user.id);

      if (updateErr) { setError("Failed to update encryption key."); return false; }

      // 5. Update Supabase auth password
      const { error: authErr } = await supabase.auth.updateUser({ password: newPassword });
      if (authErr) { setError("Auth password update failed: " + authErr.message); return false; }

      // 6. Refresh session MEK
      const freshKEK = await deriveKEK(newPassword, meta.salt);
      const freshMEK = await unwrapMEK(newWrappedMEK, freshKEK);
      setSessionKey(freshMEK);

      setSuccess(true);
      return true;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Password change failed");
      return false;
    } finally {
      currentPassword = "";
      newPassword     = "";
      setLoading(false);
    }
  }

  return { changePassword, loading, error, success };
}
