# Auth App - Authentication Service

Comprehensive authentication and authorization service for the PAN application platform.

## Overview

Auth App provides:
- User registration and login
- JWT token management
- Password hashing and verification
- Email verification
- Multi-factor authentication (MFA)
- Session management
- Role-based access control (RBAC)

## Project Structure

```
auth-app/
├── backend/
│   ├── main.py                 # Flask application
│   ├── models.py               # Data models
│   ├── middleware/
│   │   ├── verifyToken.js     # Token verification
│   │   └── rateLimiter.js     # Rate limiting
│   ├── routes/
│   │   ├── auth.js            # Auth routes
│   │   ├── users.js           # User routes
│   │   └── sessions.js        # Session routes
│   ├── utils/
│   │   ├── encryption.js      # Password encryption
│   │   ├── jwt.js             # JWT handling
│   │   └── email.js           # Email sending
│   ├── .env                    # Configuration
│   ├── requirements.txt        # Python dependencies
│   └── package.json            # Node dependencies
└── README.md                   # This file
```

## Features

- **Secure Authentication**: JWT-based authentication
- **Password Security**: Bcrypt hashing with salt
- **Email Verification**: Verify user email addresses
- **Session Management**: Track user sessions
- **Rate Limiting**: Prevent brute force attacks
- **Token Refresh**: Automatic token rotation
- **User Roles**: Support for multiple user roles
- **Audit Logging**: Log all authentication events

## Installation

```bash
# Backend setup
cd auth-app/backend

# Python setup
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Or Node.js setup
npm install

# Configure environment
cp .env.example .env
```

## Configuration

### Environment Variables (.env)

```
JWT_SECRET=your_jwt_secret_key
JWT_EXPIRY=24h
BCRYPT_ROUNDS=10
EMAIL_SERVICE=sendgrid  # or smtp
EMAIL_FROM=noreply@app.com
EMAIL_API_KEY=your_email_service_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## API Endpoints

### Authentication

#### POST /api/auth/signup
Register a new user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123",
  "name": "User Name"
}
```

**Response:**
```json
{
  "status": "success",
  "user_id": "user-123",
  "email": "user@example.com",
  "message": "Verification email sent"
}
```

#### POST /api/auth/login
User login.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```

**Response:**
```json
{
  "status": "success",
  "auth_id": "auth-token-xyz",
  "token": "jwt_token_here",
  "expires_in": 86400,
  "user": {
    "id": "user-123",
    "email": "user@example.com",
    "name": "User Name",
    "roles": ["user"]
  }
}
```

#### POST /api/auth/logout
Logout user and invalidate session.

**Response:**
```json
{
  "status": "success",
  "message": "Logged out successfully"
}
```

#### POST /api/auth/refresh-token
Refresh expired access token.

**Request:**
```json
{
  "refresh_token": "refresh_token_here"
}
```

**Response:**
```json
{
  "status": "success",
  "token": "new_jwt_token",
  "expires_in": 86400
}
```

### User Management

#### GET /api/users/profile
Get current user profile.

**Response:**
```json
{
  "status": "success",
  "user": {
    "id": "user-123",
    "email": "user@example.com",
    "name": "User Name",
    "phone": "9876543210",
    "created_at": "2024-01-15T10:30:00Z",
    "roles": ["user"],
    "settings": {}
  }
}
```

#### PUT /api/users/profile
Update user profile.

**Request:**
```json
{
  "name": "New Name",
  "phone": "9876543210",
  "settings": {}
}
```

#### POST /api/users/change-password
Change user password.

**Request:**
```json
{
  "old_password": "CurrentPassword123",
  "new_password": "NewPassword123"
}
```

#### POST /api/auth/forgot-password
Request password reset.

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Password reset link sent to email"
}
```

#### POST /api/auth/reset-password
Reset password with token.

**Request:**
```json
{
  "token": "reset_token_here",
  "password": "NewPassword123"
}
```

### Email Verification

#### POST /api/auth/verify-email
Verify user email address.

**Request:**
```json
{
  "token": "verification_token_here"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Email verified successfully"
}
```

#### POST /api/auth/resend-verification
Resend verification email.

**Request:**
```json
{
  "email": "user@example.com"
}
```

### Multi-Factor Authentication

#### POST /api/auth/setup-mfa
Enable multi-factor authentication.

**Response:**
```json
{
  "status": "success",
  "secret": "JBSWY3DPEBLW64TMMQ",
  "qr_code": "data:image/png;base64,...",
  "message": "Scan QR code with authenticator app"
}
```

#### POST /api/auth/verify-mfa
Verify MFA code.

**Request:**
```json
{
  "code": "123456"
}
```

## Security Features

### Password Hashing

```python
from utils.encryption import hash_password, verify_password

# Hash password
hashed = hash_password("PlainTextPassword")

# Verify password
is_valid = verify_password("PlainTextPassword", hashed)
```

### JWT Token Management

```python
from utils.jwt import create_token, verify_token, decode_token

# Create token
token = create_token(
    user_id="user-123",
    email="user@example.com",
    expires_in=86400  # 24 hours
)

# Verify token
is_valid = verify_token(token)

# Decode token
payload = decode_token(token)
```

### Rate Limiting

```python
from middleware.rateLimiter import rate_limit

# Limit 5 requests per minute per IP
@app.post("/api/auth/login")
@rate_limit(requests=5, window=60)
def login():
    pass
```

### Token Verification Middleware

```python
from middleware.verifyToken import verify_token_middleware

# Protect routes
@app.get("/api/users/profile")
@verify_token_middleware
def get_profile(user_payload):
    user_id = user_payload["sub"]  # Subject (user ID) from token
    return get_user(user_id)
```

## User Roles & Permissions

### Available Roles

- `user` - Regular user (default)
- `admin` - Administrator
- `moderator` - Moderator
- `agent` - Support agent

### Role-Based Access Control

```python
from middleware.rbac import require_role

@app.get("/api/admin/dashboard")
@require_role(["admin"])
def admin_dashboard():
    return get_dashboard_data()
```

## Session Management

### Session Storage

Sessions stored in Supabase with:
- Session ID
- User ID
- Token
- Created at
- Expires at
- IP address
- User agent

### Session Tracking

```python
from models.session import Session

# Create session
session = Session.create(
    user_id="user-123",
    token="jwt_token",
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0..."
)

# Get active sessions
sessions = Session.get_active_by_user(user_id)

# Revoke session
Session.revoke(session_id)
```

## Email Verification Flow

1. User signs up
2. Email verification link sent
3. User clicks link in email
4. Token verified on backend
5. Email marked as verified
6. User can fully use account

## Password Reset Flow

1. User requests password reset
2. Reset link sent to email
3. User clicks link
4. Enters new password
5. Token verified
6. Password updated
7. Session invalidated

## Error Handling

### Common Errors

```
400 Bad Request
- Invalid email format
- Weak password
- Missing required fields

401 Unauthorized
- Invalid credentials
- Invalid token
- Token expired

403 Forbidden
- Insufficient permissions
- Account not verified

409 Conflict
- User already exists
- Email already registered

429 Too Many Requests
- Rate limit exceeded
- Too many login attempts
```

## Testing

```bash
# Run unit tests
pytest tests/

# Run specific test
pytest tests/test_auth.py

# Run with coverage
pytest --cov=. tests/
```

## Integration with Backend

### Flask Integration

```python
from auth_app.models import User
from auth_app.middleware import verify_token

@app.post("/api/verify")
@verify_token
def verify_documents(auth_id):
    # auth_id from verified token
    user = User.get_by_auth_id(auth_id)
    if not user:
        return {"error": "User not found"}, 404
    
    # Process document
    return process_upload(user)
```

## Best Practices

1. **Never log passwords**: Never log or display passwords
2. **Use HTTPS**: Always use HTTPS in production
3. **Token expiry**: Set reasonable token expiration times
4. **Refresh tokens**: Use refresh tokens for long sessions
5. **Rate limiting**: Implement rate limiting on auth endpoints
6. **Email verification**: Verify email before full account access
7. **Session timeout**: Implement session timeouts
8. **Audit logging**: Log all authentication events

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Login fails with "Invalid credentials" | Wrong password | Verify password |
| Token verification fails | Expired token | Refresh token |
| Email verification not working | Wrong email | Check email configuration |
| Rate limit exceeded | Too many attempts | Wait before retrying |
| User already exists | Email already registered | Use different email |

## Dependencies

Key packages:
- `flask` - Web framework
- `pyjwt` - JWT token handling
- `bcrypt` - Password hashing
- `supabase-py` - Database
- `sendgrid` - Email service (optional)
- `qrcode` - QR code generation

## Future Enhancements

- [ ] Social login (Google, Facebook)
- [ ] Biometric authentication
- [ ] Hardware security keys
- [ ] IP-based device tracking
- [ ] Anomaly detection
- [ ] Account recovery options

## License

Proprietary and confidential.

## Support

For issues or questions, contact the development team.
