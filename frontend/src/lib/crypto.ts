/**
 * src/lib/crypto.ts — Zero-knowledge hybrid encryption layer
 *
 * CRYPTO SPEC:
 *   Key derivation : PBKDF2 + SHA-256, 310,000 iterations
 *   MEK            : AES-256-GCM, randomly generated once per user
 *   Key wrapping   : MEK encrypted with KEK (derived from password + salt)
 *   File encryption: AES-256-GCM, 12-byte random IV prepended to ciphertext
 *   Stored blob    : [12-byte IV][ciphertext]
 *
 * TESTING CHECKLIST:
 *   TODO: [ ] Register → upload file → logout → login → file decrypts successfully
 *   TODO: [ ] Change password → logout → login with NEW password → file still decrypts
 *   TODO: [ ] Login with wrong password → unwrapMEK fails → graceful error shown
 *   TODO: [ ] Check DevTools: no MEK or password in localStorage / sessionStorage / network requests
 *   TODO: [ ] Bucket file opened directly → unreadable binary gibberish
 *   TODO: [ ] Another user's JWT → RLS blocks access with 403
 */

const PBKDF2_ITERATIONS = 310_000;
const PBKDF2_HASH       = "SHA-256";
const AES_ALGO          = "AES-GCM";
const AES_KEY_LENGTH    = 256;
const IV_BYTES          = 12;
const SALT_BYTES        = 16;

// ── Helpers ───────────────────────────────────────────────────────────────────

function randomBytes(n: number): Uint8Array {
  // Never use Math.random() — always crypto.getRandomValues()
  const buf = new Uint8Array(n);
  crypto.getRandomValues(buf);
  return buf;
}

function toBase64(buf: ArrayBuffer | Uint8Array): string {
  const bytes = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  let binary  = "";
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

function fromBase64(b64: string): Uint8Array {
  const binary = atob(b64);
  const bytes  = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

// ── Salt ──────────────────────────────────────────────────────────────────────

/** Generate a random 16-byte salt (non-secret, stored in Supabase). */
export function generateSalt(): string {
  return toBase64(randomBytes(SALT_BYTES));
}

// ── MEK — Master Encryption Key ───────────────────────────────────────────────

/**
 * Generate a random 256-bit MEK.
 * extractable: true here ONLY so it can be wrapped (exported) immediately.
 * After wrapping, re-import as extractable: false via unwrapMEK.
 */
export async function generateMEK(): Promise<CryptoKey> {
  return crypto.subtle.generateKey(
    { name: AES_ALGO, length: AES_KEY_LENGTH },
    true,   // extractable: true — needed for wrapKey export step only
    ["encrypt", "decrypt"],
  );
}

// ── KEK — Key Encryption Key (derived from password, never stored) ────────────

/**
 * Derive a KEK from the user's password + salt using PBKDF2.
 * The KEK is used only for wrapping/unwrapping the MEK — never for file encryption.
 */
export async function deriveKEK(password: string, saltBase64: string): Promise<CryptoKey> {
  const enc      = new TextEncoder();
  const keyMat   = await crypto.subtle.importKey(
    "raw",
    enc.encode(password),
    "PBKDF2",
    false,
    ["deriveKey"],
  );

  return crypto.subtle.deriveKey(
    {
      name:       "PBKDF2",
      salt:       fromBase64(saltBase64),
      iterations: PBKDF2_ITERATIONS,
      hash:       PBKDF2_HASH,
    },
    keyMat,
    { name: AES_ALGO, length: AES_KEY_LENGTH },
    false,   // KEK is never extractable
    ["wrapKey", "unwrapKey"],
  );
}

// ── MEK wrapping / unwrapping ─────────────────────────────────────────────────

/**
 * Wrap (encrypt) the MEK with the KEK.
 * Returns base64 of [12-byte wrap IV][wrapped MEK ciphertext].
 */
export async function wrapMEK(mek: CryptoKey, kek: CryptoKey): Promise<string> {
  const wrapIV = randomBytes(IV_BYTES);

  const wrappedMEK = await crypto.subtle.wrapKey(
    "raw",
    mek,
    kek,
    { name: AES_ALGO, iv: wrapIV },
  );

  // Prepend IV to wrapped blob: [12-byte IV][ciphertext]
  const combined = new Uint8Array(IV_BYTES + wrappedMEK.byteLength);
  combined.set(wrapIV, 0);
  combined.set(new Uint8Array(wrappedMEK), IV_BYTES);

  return toBase64(combined);
}

/**
 * Unwrap (decrypt) the MEK using the KEK.
 * Returns MEK as extractable: false — safe to keep in session memory.
 * Throws if the KEK is wrong (wrong password).
 */
export async function unwrapMEK(wrappedBase64: string, kek: CryptoKey): Promise<CryptoKey> {
  const combined  = fromBase64(wrappedBase64);
  const wrapIV    = combined.slice(0, IV_BYTES);
  const wrappedMEK = combined.slice(IV_BYTES);

  return crypto.subtle.unwrapKey(
    "raw",
    wrappedMEK,
    kek,
    { name: AES_ALGO, iv: wrapIV },
    { name: AES_ALGO, length: AES_KEY_LENGTH },
    false,   // extractable: false — MEK never leaves memory as raw bytes
    ["encrypt", "decrypt"],
  );
}

// ── File encryption / decryption ──────────────────────────────────────────────

/**
 * Encrypt a File with the MEK.
 * Returns a Blob with format: [12-byte IV][AES-GCM ciphertext].
 */
export async function encryptFile(file: File, mek: CryptoKey): Promise<Blob> {
  const iv        = randomBytes(IV_BYTES);
  const plaintext = await file.arrayBuffer();

  const ciphertext = await crypto.subtle.encrypt(
    { name: AES_ALGO, iv },
    mek,
    plaintext,
  );

  // Prepend IV: [12-byte IV][ciphertext]
  const combined = new Uint8Array(IV_BYTES + ciphertext.byteLength);
  combined.set(iv, 0);
  combined.set(new Uint8Array(ciphertext), IV_BYTES);

  return new Blob([combined], { type: "application/octet-stream" });
}

/**
 * Decrypt an encrypted blob with the MEK.
 * Expects format: [12-byte IV][AES-GCM ciphertext].
 * Returns a Blob with the original mimeType.
 * Throws DECRYPTION_FAILED if the MEK is wrong or blob is corrupt.
 */
export async function decryptFile(
  encryptedBlob: Blob,
  mek: CryptoKey,
  mimeType: string,
): Promise<Blob> {
  const buf      = await encryptedBlob.arrayBuffer();
  const combined = new Uint8Array(buf);
  const iv       = combined.slice(0, IV_BYTES);
  const ciphertext = combined.slice(IV_BYTES);

  let plaintext: ArrayBuffer;
  try {
    plaintext = await crypto.subtle.decrypt(
      { name: AES_ALGO, iv },
      mek,
      ciphertext,
    );
  } catch {
    const err = new Error("Unable to decrypt this file. Please try logging out and back in.");
    err.name  = "DECRYPTION_FAILED";
    throw err;
  }

  return new Blob([plaintext], { type: mimeType });
}

// ── Password change — re-wrap MEK with new KEK ────────────────────────────────

/**
 * Unwrap MEK with oldKEK, then re-wrap with newKEK.
 * Salt stays the same. MEK stays the same. All existing files remain decryptable.
 * Throws if oldKEK is wrong (current password is incorrect).
 */
export async function rewrapMEK(
  wrappedBase64: string,
  oldKEK: CryptoKey,
  newKEK: CryptoKey,
): Promise<string> {
  // Unwrap with old KEK — throws if wrong password
  const mek = await unwrapMEK(wrappedBase64, oldKEK);

  // Re-import as extractable: true so wrapKey can export it
  const rawMEK = await crypto.subtle.exportKey("raw", mek);
  const extractableMEK = await crypto.subtle.importKey(
    "raw",
    rawMEK,
    { name: AES_ALGO, length: AES_KEY_LENGTH },
    true,
    ["encrypt", "decrypt"],
  );

  // Re-wrap with new KEK
  return wrapMEK(extractableMEK, newKEK);
}
