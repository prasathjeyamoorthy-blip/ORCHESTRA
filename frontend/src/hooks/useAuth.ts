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
import { apiPost } from "../utils/api";

type AuthUser = {
  id: string;
  email?: string;
  display_name?: string;
};

type AuthResponse = {
  user: AuthUser;
  session?: {
    access_token: string;
    refresh_token: string;
  };
};

export function useAuth() {
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  // ── Registration ────────────────────────────────────────────────
  async function register(email: string, password: string, displayName = ""): Promise<AuthUser | false> {
    setLoading(true);
    setError(null);

    try {
      const authData = await apiPost("/api/auth/signup", {
        email,
        password,
        display_name: displayName,
      }) as AuthResponse;

      if (!authData.user || !authData.session) {
        setError("Registration failed");
        return false;
      }

      const { error: sessionErr } = await supabase.auth.setSession(authData.session);
      if (sessionErr) {
        setError(sessionErr.message);
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
        .insert({ user_id: authData.user.id, salt, wrapped_mek: wrappedMEK });

      if (dbErr) {
        setError("Failed to initialise encryption: " + dbErr.message);
        return false;
      }

      // 5. Re-import MEK as extractable: false
      const rawMEK = await crypto.subtle.exportKey("raw", mek);
      const sessionMEK = await crypto.subtle.importKey(
        "raw", rawMEK,
        { name: "AES-GCM", length: 256 },
        false, ["encrypt", "decrypt"],
      );
      setSessionKey(sessionMEK);

      return authData.user;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Registration failed");
      return false;
    } finally {
      password = "";
      setLoading(false);
    }
  }

  // ── Login ───────────────────────────────────────────────────────
  async function login(email: string, password: string): Promise<AuthUser | false> {
    setLoading(true);
    setError(null);

    try {
      const authData = await apiPost("/api/auth/login", { email, password }) as AuthResponse;

      if (!authData.user || !authData.session) {
        setError("Login failed");
        return false;
      }

      const { error: sessionErr } = await supabase.auth.setSession(authData.session);
      if (sessionErr) {
        setError(sessionErr.message);
        return false;
      }

      // 2. Fetch crypto meta directly from DB (no Edge Function needed)
      const { data: meta, error: dbErr } = await supabase
        .from("user_crypto_meta")
        .select("salt, wrapped_mek")
        .eq("user_id", authData.user.id)
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
          .insert({ user_id: authData.user.id, salt, wrapped_mek: wrappedMEK });

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
        return authData.user;
      }

      if (dbErr) {
        setError("Could not load encryption keys. Please contact support.");
        return false;
      }

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
      return authData.user;
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
    await apiPost("/api/auth/logout", {}).catch(() => {});
  }

  return { register, login, logout, loading, error };
}
