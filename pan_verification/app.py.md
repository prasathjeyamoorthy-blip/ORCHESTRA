# app.py - Main Flask Application

## Purpose
Core Flask application serving as the main API server for the PAN verification platform. Handles all HTTP requests, routing, and API endpoints for document processing, user authentication, and data management.

## Key Responsibilities
- Initialize Flask app with CORS configuration
- Define all API routes and endpoints
- Handle file uploads and document processing
- Manage user authentication and document retrieval
- Integrate with Supabase for database operations
- Integrate with ORCHESTRA for multi-document processing
- Provide error handling and response formatting

## Main Endpoints

### Authentication
- `POST /api/signup` - User registration
- `POST /api/login` - User login

### Document Processing
- `POST /api/verify` - Upload and verify document (primary endpoint)
- `POST /api/preview` - Preview extracted data without saving
- `POST /api/confirm_save` - Save user-verified data
- `POST /api/validate_photo` - Validate profile photo
- `POST /api/update_document` - Update existing document

### Document Retrieval
- `POST /api/get_docs` - Get all documents for user
- `POST /api/get_person_docs` - Get documents for specific person

### Multi-Document Processing (ORCHESTRA)
- `POST /api/multi_documents/verify` - Process multiple documents
- `POST /api/multi_documents/confirm` - Save multi-document results

## Key Functions

### verify_documents()
Main document verification endpoint. Handles:
- Document type detection
- Image quality assessment
- Field extraction using VLM
- Validation of extracted fields
- Missing fields identification
- Return formatted response with extraction results

### confirm_save()
Saves user-verified and corrected document data. Features:
- Data validation and formatting
- Conflict resolution
- Database storage
- User feedback and confirmation

### get_person_docs()
Retrieves documents for a person by name or phone number.

## Dependencies
- Flask - Web framework
- Flask-CORS - Cross-origin support
- Werkzeug - File handling
- Supabase client - Database operations
- ORCHESTRA modules - Multi-document processing

## Configuration
- CORS enabled for cross-origin requests
- Environment variables loaded from .env file
- NVIDIA API key required for vision model
- Supabase credentials required

## Error Handling
- Returns appropriate HTTP status codes (400, 401, 404, 500)
- Provides descriptive error messages to clients
- Logs errors for debugging
- Graceful degradation for partial failures

## Integration Points
- `helpers.py` - Document extraction
- `supa.py` - Database operations
- `image_quality.py` - Quality assessment
- `re_check.py` - Field validation
- `ORCHESTRA/` - Multi-document processing

## Notes
- All file uploads are validated for type and size
- Quality score < 0.6 returns error
- ORCHESTRA integration loads conditionally
- Session management handled via auth_id parameter
