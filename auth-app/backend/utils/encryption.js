// utils/encryption.js
// Server-side encryption utilities for document security
const crypto = require('crypto');

const ALGORITHM = 'aes-256-gcm';
const KEY_LENGTH = 32; // 256 bits
const IV_LENGTH = 16;  // 128 bits
const SALT_LENGTH = 32;
const TAG_LENGTH = 16;

/**
 * Generate a random encryption key
 * @returns {Buffer} 32-byte encryption key
 */
function generateKey() {
  return crypto.randomBytes(KEY_LENGTH);
}

/**
 * Generate a random salt for key derivation
 * @returns {Buffer} 32-byte salt
 */
function generateSalt() {
  return crypto.randomBytes(SALT_LENGTH);
}

/**
 * Derive an encryption key from a password and salt using PBKDF2
 * @param {string} password - User password or OTP
 * @param {Buffer} salt - Salt for key derivation
 * @returns {Buffer} Derived encryption key
 */
function deriveKey(password, salt) {
  return crypto.pbkdf2Sync(password, salt, 100000, KEY_LENGTH, 'sha256');
}

/**
 * Encrypt data using AES-256-GCM
 * @param {Buffer} data - Data to encrypt
 * @param {Buffer} key - Encryption key
 * @returns {Object} { encrypted: Buffer, iv: Buffer, tag: Buffer }
 */
function encrypt(data, key) {
  const iv = crypto.randomBytes(IV_LENGTH);
  const cipher = crypto.createCipheriv(ALGORITHM, key, iv);
  
  const encrypted = Buffer.concat([
    cipher.update(data),
    cipher.final()
  ]);
  
  const tag = cipher.getAuthTag();
  
  return { encrypted, iv, tag };
}

/**
 * Decrypt data using AES-256-GCM
 * @param {Buffer} encrypted - Encrypted data
 * @param {Buffer} key - Decryption key
 * @param {Buffer} iv - Initialization vector
 * @param {Buffer} tag - Authentication tag
 * @returns {Buffer} Decrypted data
 */
function decrypt(encrypted, key, iv, tag) {
  const decipher = crypto.createDecipheriv(ALGORITHM, key, iv);
  decipher.setAuthTag(tag);
  
  return Buffer.concat([
    decipher.update(encrypted),
    decipher.final()
  ]);
}

/**
 * Encrypt a file buffer with a user-specific key
 * @param {Buffer} fileBuffer - File data to encrypt
 * @param {string} userSecret - User's secret (password or derived key)
 * @param {Buffer} salt - Salt for key derivation (optional, will generate if not provided)
 * @returns {Object} { encryptedData: Buffer, iv: string, tag: string, salt: string }
 */
function encryptFile(fileBuffer, userSecret, salt = null) {
  if (!salt) {
    salt = generateSalt();
  }
  
  const key = deriveKey(userSecret, salt);
  const { encrypted, iv, tag } = encrypt(fileBuffer, key);
  
  return {
    encryptedData: encrypted,
    iv: iv.toString('base64'),
    tag: tag.toString('base64'),
    salt: salt.toString('base64')
  };
}

/**
 * Decrypt a file buffer with a user-specific key
 * @param {Buffer} encryptedData - Encrypted file data
 * @param {string} userSecret - User's secret (password or derived key)
 * @param {string} ivBase64 - IV in base64
 * @param {string} tagBase64 - Auth tag in base64
 * @param {string} saltBase64 - Salt in base64
 * @returns {Buffer} Decrypted file data
 */
function decryptFile(encryptedData, userSecret, ivBase64, tagBase64, saltBase64) {
  const salt = Buffer.from(saltBase64, 'base64');
  const iv = Buffer.from(ivBase64, 'base64');
  const tag = Buffer.from(tagBase64, 'base64');
  
  const key = deriveKey(userSecret, salt);
  
  return decrypt(encryptedData, key, iv, tag);
}

/**
 * Encrypt file metadata (filename, etc.) for additional privacy
 * @param {string} metadata - Metadata to encrypt
 * @param {Buffer} key - Encryption key
 * @returns {Object} { encrypted: string, iv: string, tag: string }
 */
function encryptMetadata(metadata, key) {
  const { encrypted, iv, tag } = encrypt(Buffer.from(metadata, 'utf8'), key);
  
  return {
    encrypted: encrypted.toString('base64'),
    iv: iv.toString('base64'),
    tag: tag.toString('base64')
  };
}

/**
 * Decrypt file metadata
 * @param {string} encryptedBase64 - Encrypted metadata in base64
 * @param {Buffer} key - Decryption key
 * @param {string} ivBase64 - IV in base64
 * @param {string} tagBase64 - Auth tag in base64
 * @returns {string} Decrypted metadata
 */
function decryptMetadata(encryptedBase64, key, ivBase64, tagBase64) {
  const encrypted = Buffer.from(encryptedBase64, 'base64');
  const iv = Buffer.from(ivBase64, 'base64');
  const tag = Buffer.from(tagBase64, 'base64');
  
  const decrypted = decrypt(encrypted, key, iv, tag);
  return decrypted.toString('utf8');
}

module.exports = {
  generateKey,
  generateSalt,
  deriveKey,
  encrypt,
  decrypt,
  encryptFile,
  decryptFile,
  encryptMetadata,
  decryptMetadata,
  ALGORITHM,
  KEY_LENGTH,
  IV_LENGTH,
  SALT_LENGTH,
  TAG_LENGTH
};
