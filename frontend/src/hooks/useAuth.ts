import { useState } from "react";
import { supabase } from "../lib/supabase";
import {
  generateSalt,
  generateMEK,
  deriveKEK,
  wrapMEK,
  unwrapMEK,
} from "../lib/crypto";
import { setSessionKey, clearSessionKey } from "../lib/keySession";

export function useAuth() {
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  // ── Registration ────────────────────────────────────────────────
  async function register(email: string, password: string): Promise<boolean> {
    setLoading(true);
    setError(null);

    try {
      // 1. Create Supabase auth user
      const { data: authData, error: authErr } = await supabase.auth.signUp({ email, password });
      if (authErr || !authData.session) {
        setError(authErr?.message ?? "Registration failed");
        return false;
      }

      // 2. Generate MEK and salt
      const mek  = await generateMEK();
      const salt = generateSalt();

      // 3. Derive KEK and wrap MEK
      const kek        = await deriveKEK(password, salt);
      const wrappedMEK = await wrapMEK(mek, kek);

      // 4. Store directly in Supabase table (RLS ensures only this user can write)
      const { error: dbErr } = await supabase
        .from("user_crypto_meta")
        .insert({ user_id: authData.user!.id, salt, wrapped_mek: wrappedMEK });

      if (dbErr) {
        setError("Failed to initialise encryption: " + dbErr.message);
        return false;
      }

      // 5. Sync session cookies with Express backend
      try {
        await fetch('/api/auth/sync-session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            access_token:  authData.session!.access_token,
            refresh_token: authData.session!.refresh_token,
          }),
        });
      } catch { /* backend may not be running */ }

      // 5. Re-import MEK as extractable: false
      const rawMEK = await crypto.subtle.exportKey("raw", mek);
      const sessionMEK = await crypto.subtle.importKey(
        "raw", rawMEK,
        { name: "AES-GCM", length: 256 },
        false, ["encrypt", "decrypt"],
      );
      setSessionKey(sessionMEK);

      return true;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Registration failed");
      return false;
    } finally {
      password = "";
      setLoading(false);
    }
  }

  // ── Login ───────────────────────────────────────────────────────
  async function login(email: string, password: string): Promise<boolean> {
    setLoading(true);
    setError(null);

    try {
      // 1. Authenticate
      const { data: authData, error: authErr } = await supabase.auth.signInWithPassword({ email, password });
      if (authErr || !authData.session) {
        setError(authErr?.message ?? "Login failed");
        return false;
      }

      // 2. Fetch crypto meta directly from DB (no Edge Function needed)
      const { data: meta, error: dbErr } = await supabase
        .from("user_crypto_meta")
        .select("salt, wrapped_mek")
        .eq("user_id", authData.user!.id)
        .maybeSingle();   // returns null instead of 406 when no row exists

      // No crypto meta — this user registered before encryption was set up.
      // Generate and store it now so they're enrolled going forward.
      if (!meta) {
        const mek  = await generateMEK();
        const salt = generateSalt();
        const kek  = await deriveKEK(password, salt);
        const wrappedMEK = await wrapMEK(mek, kek);

        const { error: insertErr } = await supabase
          .from("user_crypto_meta")
          .insert({ user_id: authData.user!.id, salt, wrapped_mek: wrappedMEK });

        if (insertErr) {
          setError("Failed to initialise encryption: " + insertErr.message);
          return false;
        }

        const rawMEK = await crypto.subtle.exportKey("raw", mek);
        const sessionMEK = await crypto.subtle.importKey(
          "raw", rawMEK,
          { name: "AES-GCM", length: 256 },
          false, ["encrypt", "decrypt"],
        );
        setSessionKey(sessionMEK);
        return true;
      }

      if (dbErr) {
        setError("Could not load encryption keys. Please contact support.");
        return false;
      }

      // 3. Sync session cookies with Express backend so /api/chat/* routes work
      //    The backend reads httpOnly cookies — we pass the Supabase tokens to set them
      try {
        await fetch('/api/auth/sync-session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            access_token:  authData.session.access_token,
            refresh_token: authData.session.refresh_token,
          }),
        });
      } catch { /* backend may not be running — chat features will be unavailable */ }

      // 4. Derive KEK and unwrap MEK
      const kek = await deriveKEK(password, meta.salt);
      let mek: CryptoKey;
      try {
        mek = await unwrapMEK(meta.wrapped_mek, kek);
      } catch {
        setError("Incorrect password.");
        return false;
      }

      setSessionKey(mek);
      return true;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Login failed");
      return false;
    } finally {
      password = "";
      setLoading(false);
    }
  }

  // ── Logout ──────────────────────────────────────────────────────
  async function logout(): Promise<void> {
    clearSessionKey();
    await supabase.auth.signOut();
  }

  return { register, login, logout, loading, error };
}
