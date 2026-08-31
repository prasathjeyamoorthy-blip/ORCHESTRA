/**
 * Client-Side Zero-Knowledge Encryption using PBKDF2-Derived AES-256-GCM Key.
 *
 * The encryption key is derived inside the browser using PBKDF2(PIN + PhoneSalt).
 * The PIN and derived Key are NEVER sent to backend servers or Supabase.
 * Any browser or device entering the same PIN can derive the exact key and decrypt records!
 */

const PIN_CACHE_KEY = "zk_user_pin_";

function arrayBufferToBase64(buffer) {
  let binary = "";
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}

function base64ToArrayBuffer(base64) {
  const binaryString = window.atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
}

export function getUserPin(phoneNumber) {
  const phoneClean = (phoneNumber || "default").replace(/\+/g, "").replace(/\s/g, "").slice(-10);
  return sessionStorage.getItem(`${PIN_CACHE_KEY}${phoneClean}`) || "000000";
}

export function setUserPin(phoneNumber, pin) {
  const phoneClean = (phoneNumber || "default").replace(/\+/g, "").replace(/\s/g, "").slice(-10);
  sessionStorage.setItem(`${PIN_CACHE_KEY}${phoneClean}`, pin || "000000");
}

const KEY_MEMORY_CACHE = new Map();

/**
 * Derive a 256-bit AES-GCM Key deterministically from (Phone + PIN).
 * Uses in-memory caching to execute PBKDF2 (100,000 iterations) ONCE per session.
 */
export async function deriveUserKey(phoneNumber, pin = null) {
  const phoneClean = (phoneNumber || "default").replace(/\+/g, "").replace(/\s/g, "").slice(-10);
  const userPin = pin || getUserPin(phoneClean);
  const cacheKey = `${phoneClean}_${userPin}`;

  if (KEY_MEMORY_CACHE.has(cacheKey)) {
    return KEY_MEMORY_CACHE.get(cacheKey);
  }

  const enc = new TextEncoder();
  const pinKey = await window.crypto.subtle.importKey(
    "raw",
    enc.encode(userPin),
    { name: "PBKDF2" },
    false,
    ["deriveKey"]
  );

  const salt = enc.encode(`TNEGA_ZK_SALT_${phoneClean}`);

  const derivedKey = await window.crypto.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations: 100000, hash: "SHA-256" },
    pinKey,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"]
  );

  KEY_MEMORY_CACHE.set(cacheKey, derivedKey);
  return derivedKey;
}

/**
 * Encrypt payload in client browser using PBKDF2-derived AES-GCM key.
 * Format: ZK_PBKDF2_v1:<iv_b64>:<ciphertext_b64>
 */
export async function encryptPayloadZK(text, phoneNumber, pin = null) {
  if (!text) return "";
  try {
    const key = await deriveUserKey(phoneNumber, pin);
    const iv = window.crypto.getRandomValues(new Uint8Array(12));
    const encoded = new TextEncoder().encode(text);
    const ciphertext = await window.crypto.subtle.encrypt(
      { name: "AES-GCM", iv },
      key,
      encoded
    );
    return `ZK_PBKDF2_v1:${arrayBufferToBase64(iv)}:${arrayBufferToBase64(ciphertext)}`;
  } catch (err) {
    console.error("[ZK Encrypt Error]", err);
    return text;
  }
}

/**
 * Decrypt payload in client browser using PBKDF2-derived AES-GCM key.
 */
export async function decryptPayload(payload, phoneNumber = "default", pin = null) {
  if (!payload || typeof payload !== "string") return payload;

  // Handle new PBKDF2 format
  if (payload.startsWith("ZK_PBKDF2_v1:")) {
    try {
      const parts = payload.split(":");
      if (parts.length < 3) return payload;

      const key = await deriveUserKey(phoneNumber, pin);
      const iv = base64ToArrayBuffer(parts[1]);
      const ciphertext = base64ToArrayBuffer(parts[2]);

      const decryptedBuf = await window.crypto.subtle.decrypt(
        { name: "AES-GCM", iv: new Uint8Array(iv), tagLength: 128 },
        key,
        ciphertext
      );
      return new TextDecoder().decode(decryptedBuf);
    } catch (err) {
      console.warn("[ZK Decrypt Error - Possibly wrong PIN]", err);
      return "[Encrypted Message - Locked]";
    }
  }

  return payload;
}

/**
 * Encrypt a file's binary ArrayBuffer using PBKDF2-derived AES-256-GCM.
 * Output ArrayBuffer format: ZK_DOC_v1 (9 bytes) + IV (12 bytes) + AES-GCM Ciphertext
 */
export async function encryptDocumentBytesZK(fileArrayBuffer, phoneNumber = "default", pin = null) {
  if (!fileArrayBuffer) return fileArrayBuffer;
  try {
    const key = await deriveUserKey(phoneNumber, pin);
    const iv = window.crypto.getRandomValues(new Uint8Array(12));
    const ciphertext = await window.crypto.subtle.encrypt(
      { name: "AES-GCM", iv },
      key,
      fileArrayBuffer
    );
    const header = new TextEncoder().encode("ZK_DOC_v1");
    const result = new Uint8Array(header.byteLength + iv.byteLength + ciphertext.byteLength);
    result.set(header, 0);
    result.set(iv, header.byteLength);
    result.set(new Uint8Array(ciphertext), header.byteLength + iv.byteLength);
    return result.buffer;
  } catch (err) {
    console.error("[ZK Document Encrypt Error]", err);
    return fileArrayBuffer;
  }
}

/**
 * Decrypt a Zero-Knowledge encrypted binary document ArrayBuffer.
 */
export async function decryptDocumentBytesZK(encryptedArrayBuffer, phoneNumber = "default", pin = null) {
  if (!encryptedArrayBuffer) return encryptedArrayBuffer;
  try {
    const data = new Uint8Array(encryptedArrayBuffer);
    if (data.byteLength < 21) return encryptedArrayBuffer;

    const headerStr = new TextDecoder().decode(data.subarray(0, 9));
    if (headerStr !== "ZK_DOC_v1") {
      // Not encrypted in ZK_DOC_v1 format, return as-is
      return encryptedArrayBuffer;
    }

    const iv = data.subarray(9, 21);
    const ciphertext = data.subarray(21);
    const key = await deriveUserKey(phoneNumber, pin);

    const decrypted = await window.crypto.subtle.decrypt(
      { name: "AES-GCM", iv, tagLength: 128 },
      key,
      ciphertext
    );
    return decrypted;
  } catch (err) {
    console.error("[ZK Document Decrypt Error - Wrong PIN or corrupted payload]", err);
    throw new Error("Invalid 6-digit PIN or decryption key.");
  }
}


