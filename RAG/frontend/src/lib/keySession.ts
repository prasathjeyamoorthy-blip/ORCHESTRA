/**
 * src/lib/keySession.ts — In-memory MEK store
 *
 * The MEK lives ONLY in this module-level variable.
 * It is NEVER written to localStorage, sessionStorage, cookies, or IndexedDB.
 * It is lost on page refresh — user must log in again to restore it.
 *
 * TODO: [ ] Check DevTools: no MEK in localStorage / sessionStorage / network requests
 */

let _sessionKey: CryptoKey | null = null;

/** Store the unwrapped MEK in memory for this session. */
export function setSessionKey(key: CryptoKey): void {
  _sessionKey = key;
}

/** Retrieve the in-memory MEK. Returns null if not set (user not logged in). */
export function getSessionKey(): CryptoKey | null {
  return _sessionKey;
}

/** Wipe the MEK from memory. Call this BEFORE supabase.auth.signOut(). */
export function clearSessionKey(): void {
  _sessionKey = null;
}
