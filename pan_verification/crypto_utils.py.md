# crypto_utils.py - Encryption & Security Utilities

## Purpose
Provides cryptographic functions for secure data handling including password hashing, encryption/decryption, and secure token generation.

## Key Functions

### hash_password(password)
Securely hash a password using bcrypt.
- **Algorithm**: Bcrypt with salt rounds
- **Input**: Plain text password
- **Output**: Secure hash string
- **Usage**: Store hashed password in database
- **Security**: One-way hashing, cannot be reversed

### verify_password(password, password_hash)
Verify password against stored hash.
- **Input**: Plain text password and stored hash
- **Output**: Boolean (match/no match)
- **Usage**: Login verification
- **Timing**: Constant time comparison (prevents timing attacks)

### encrypt_data(data, key)
Encrypt sensitive data using AES.
- **Algorithm**: AES-256-GCM
- **Input**: Data string and encryption key
- **Output**: Encrypted bytes (ciphertext + IV + tag)
- **Usage**: Encrypt PII before storage

### decrypt_data(encrypted_data, key)
Decrypt previously encrypted data.
- **Input**: Encrypted bytes and decryption key
- **Output**: Original plain text data
- **Throws**: ValueError if decryption fails (tampered data)

### generate_token(length)
Generate secure random token.
- **Input**: Token length (default 32)
- **Output**: URL-safe random token
- **Usage**: Session tokens, password reset tokens
- **Security**: Uses cryptographically secure random

### generate_jwt_token(payload, secret, expires_in)
Generate JWT token for session management.
- **Payload**: Dictionary with user data
- **Secret**: Secret key for signing
- **Expires_in**: Token expiration time (seconds)
- **Returns**: Signed JWT token string

### verify_jwt_token(token, secret)
Verify and decode JWT token.
- **Input**: JWT token and secret
- **Returns**: Decoded payload
- **Throws**: jwt.InvalidTokenError if invalid/expired
- **Verification**: Signature and expiration check

## Security Features

### Password Security
- Bcrypt with configurable rounds (default 10)
- Automatic salt generation
- Protection against rainbow table attacks
- Resistance to GPU/ASIC attacks

### Encryption Security
- AES-256-GCM for authenticated encryption
- Generates new IV for each encryption
- Authentication tag prevents tampering
- Key derivation from master secret

### Token Security
- Cryptographically secure random generation
- URL-safe base64 encoding
- Sufficient entropy for uniqueness

### JWT Security
- HMAC signature verification
- Expiration time validation
- Token revocation support (optional)
- Prevents tampering and forgery

## Usage Examples

### Password Hashing
```python
from crypto_utils import hash_password, verify_password

# During registration
password_hash = hash_password(user_password)
# Store password_hash in database

# During login
if verify_password(user_input_password, stored_hash):
    # Password correct
    authenticate_user()
```

### Data Encryption
```python
from crypto_utils import encrypt_data, decrypt_data

# Encrypt sensitive data
encryption_key = os.getenv('ENCRYPTION_KEY')
encrypted = encrypt_data(user_phone, encryption_key)
# Store encrypted in database

# Decrypt when needed
phone = decrypt_data(encrypted, encryption_key)
```

### Token Generation
```python
from crypto_utils import generate_token, generate_jwt_token

# Session token
session_token = generate_token(32)

# JWT token
jwt_payload = {"user_id": "123", "email": "user@example.com"}
jwt_token = generate_jwt_token(jwt_payload, secret, expires_in=86400)
```

## Configuration

### Environment Variables
- `ENCRYPTION_KEY` - Master key for data encryption
- `JWT_SECRET` - Secret for JWT signing
- `BCRYPT_ROUNDS` - Rounds for password hashing (default 10)

### Constants
- `ENCRYPTION_ALGORITHM` - AES-256-GCM
- `JWT_ALGORITHM` - HS256 (HMAC-SHA256)
- `TOKEN_ALPHABET` - URL-safe characters

## Security Considerations

### Password Storage
- Never store plain text passwords
- Use strong hashing (never MD5, SHA1, SHA256 alone)
- Implement rate limiting on login attempts

### Key Management
- Store keys securely (environment variables)
- Rotate keys periodically
- Use separate keys for different purposes
- Never commit keys to version control

### Token Management
- Set reasonable expiration times
- Implement token refresh mechanism
- Validate signature and expiration
- Implement token revocation

### Data Encryption
- Encrypt PII before storage
- Use authenticated encryption (GCM mode)
- Detect tampering/corruption
- Ensure IV is unique per encryption

## Integration Points
- Used by `app.py` for authentication
- Password storage in user registration
- JWT token generation for sessions
- Encryption of sensitive user data

## Performance
- Password hashing: 100-200ms (intentionally slow)
- Encryption/decryption: < 10ms
- Token generation: < 1ms
- JWT operations: < 5ms

## Dependencies
- `bcrypt` - Password hashing
- `cryptography` - AES encryption
- `pyjwt` - JWT handling
- `secrets` - Secure random generation

## Compliance
- Supports FIPS 140-2 compliant algorithms
- Meets OWASP password hashing guidelines
- Implements industry-standard cryptography
- Suitable for HIPAA/PCI-DSS compliance

## Notes
- Always use HTTPS for token transmission
- Implement CSRF protection for web apps
- Secure token storage in browsers/clients
- Regular security audits recommended
