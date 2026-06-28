# Pan Verification Backend

Core backend service for document extraction, validation, and multi-document processing using AI vision models.

## Overview

The pan_verification service provides:
- Document type detection
- Field extraction from documents
- Real-time field validation
- Quality scoring
- Multi-document processing via ORCHESTRA
- Secure document storage

## Project Structure

```
pan_verification/
├── app.py                       # Main Flask application
├── helpers.py                   # Extraction and utility functions
├── pan_verification_upd.py      # Pydantic schemas and validation
├── supa.py                      # Supabase integration
├── image_quality.py             # Image quality assessment
├── re_check.py                  # Regex-based validation
├── ORCHESTRA/                   # Multi-document processing
│   ├── DocumentUploadAgent/
│   │   ├── main.py             # Entry point
│   │   ├── extractor.py        # Document extraction
│   │   └── validator.py        # Cross-document validation
│   └── ...
├── middleware/                  # Express middleware (if used)
├── routes/                      # API route handlers
├── utils/                       # Utility functions
├── requirements.txt             # Python dependencies
├── .env                         # Environment configuration
└── README.md                    # This file
```

## Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Run server
python app.py
```

## Configuration

### Environment Variables (.env)

```
NVIDIA_META_90B=your_nvidia_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
FLASK_ENV=development
FLASK_DEBUG=True
```

Get NVIDIA API key from: https://build.nvidia.com

## API Endpoints

### Document Processing

#### POST /api/verify
Upload document for extraction and verification.

**Request:**
```
Content-Type: multipart/form-data
Parameters:
- auth_id: User authentication ID
- aadhaar: Document file (JPG, PNG, PDF)
```

**Response:**
```json
{
  "status": "missing_fields|extracted_for_verification|profile_photo_validated",
  "document_type": "aadhaar_card|profile_photo|unknown",
  "extracted_fields": {
    "name": "John Doe",
    "father_name": "Father Name",
    "mobile_number": "9876543210",
    "dob": "01/01/1990",
    "gender": "Male",
    "state": "Tamil Nadu",
    "aadhar_number": "XXXX XXXX 1234"
  },
  "missing_fields": [
    {
      "field": "phone",
      "label": "Phone Number",
      "type": "tel",
      "placeholder": "Enter phone number",
      "validation": {...}
    }
  ],
  "all_extracted_data": {
    "aadhaar_number": "...",
    "name": "...",
    "first_name": "...",
    "phone": "...",
    "... 30+ fields total ...": "..."
  },
  "quality_score": 0.95,
  "confidence": "high|medium|low"
}
```

#### POST /api/preview
Preview extracted data without saving.

**Request:**
```
Content-Type: multipart/form-data
Parameters:
- auth_id: User authentication ID
- aadhaar: Document file
```

**Response:**
```json
{
  "status": "success",
  "document_type": "aadhaar_card",
  "extracted_data": {...},
  "quality_score": 0.95
}
```

#### POST /api/confirm_save
Save user-verified and confirmed document data.

**Request:**
```
Content-Type: application/json

{
  "auth_id": "user-id",
  "extracted_fields": {...},
  "user_fields": {...}
}
```

**Response:**
```json
{
  "status": "success",
  "doc_id": "doc-123",
  "person_id": "person-456",
  "message": "Document verified and saved successfully",
  "saved_data": {...}
}
```

### Document Retrieval

#### POST /api/get_docs
Get all documents for authenticated user.

#### POST /api/get_person_docs
Get documents for specific person by name or phone.

#### POST /api/update_document
Update existing document for a person.

### Multi-Document Processing (ORCHESTRA)

#### POST /api/multi_documents/verify
Process multiple documents with cross-validation.

#### POST /api/multi_documents/confirm
Save multi-document processing results.

## Extraction Workflows

### Single Document (Aadhaar Card)

1. **File Check** - Validates file type and size
2. **Quality Assessment** - Checks image quality (brightness, blur, resolution)
3. **Type Detection** - Identifies document type
4. **Field Extraction** - Uses NVIDIA Vision Model to extract 30+ fields
5. **Validation** - Validates each field format
6. **Response** - Returns extracted data and missing fields

### Multi-Document (ORCHESTRA)

1. **Individual Extraction** - Extract from each document
2. **Type Validation** - Verify document types
3. **Cross-Validation** - Compare data across documents
4. **Conflict Detection** - Identify inconsistencies
5. **Data Merging** - Intelligently merge data with priority rules
6. **Confidence Scoring** - Assign confidence to merged data
7. **Response** - Return merged and validated data

## Pydantic Schemas

### AadhaarData
Represents extracted Aadhaar card data with 30+ fields:
- Name components (first, middle, last, full)
- Father/Guardian info
- Mother/Guardian info
- Personal details (DOB, gender, phone)
- Address components (flat, building, road, locality, district, state, pincode)
- Status (residential, masked, legible)
- Confidence and issues

### PhotoData
Represents profile photo validation:
- Face presence and count
- Face centering and visibility
- Photo quality assessment
- Suitability for PAN

### SignatureData
Represents signature validation:
- Signature presence and handwriting
- Visibility and background
- Cut-off detection
- Confidence scoring

## Validation Rules

### Mobile Number
- Must be 10 digits
- Must start with 6-9
- Pattern: `^[6-9][0-9]{9}$`

### Aadhaar Number
- Must be 12 digits (or masked with XXXX XXXX NNNN)
- Pattern: `^([0-9]{12}|[Xx*]{8}[0-9]{4})$`

### Date of Birth
- Format: DD/MM/YYYY or YYYY-MM-DD
- Must be valid date
- Must be before current date
- Age validation: 0-120 years

### Pincode
- Must be 6 digits
- Cannot start with 0
- Pattern: `^[1-9]\d{5}$`

### Gender
- Enum: Male, Female, Transgender, Other

## Extraction Prompts

### AADHAAR_PROMPT
Advanced prompt that instructs the NVIDIA Vision Model to extract 30+ fields including:
- Name with first/middle/last split
- Father's name with component split
- Mother's name (if present) with component split
- Phone/mobile number
- Residential status
- Detailed address breakdown
- Location information (district, state, pincode, country)
- Confidence scoring and issue detection

See `helpers.py` for full prompt configuration.

## Error Handling

### Client Errors (4xx)
- 400: Missing required fields, invalid file type, low image quality
- 401: Authentication required or invalid auth_id
- 404: Resource not found

### Server Errors (5xx)
- 500: Extraction failure, database error, API service error

All errors return:
```json
{
  "status": "error",
  "error": "Error message",
  "error_type": "specific_error_type",
  "message": "User-friendly message"
}
```

## Security

- Environment variables never logged
- API keys stored securely
- Input validation on all endpoints
- File type and size restrictions
- CORS properly configured
- Rate limiting recommended

## Dependencies

Key Python packages:
- `flask` - Web framework
- `flask-cors` - CORS support
- `pydantic` - Data validation
- `opencv-python` - Image processing
- `pillow` - Image handling
- `requests` - HTTP client
- `supabase-py` - Supabase integration
- `dotenv` - Environment variables

## Testing

```bash
# Run unit tests
pytest tests/

# Run specific test
pytest tests/test_extraction.py

# Run with coverage
pytest --cov=. tests/
```

## Development

### Adding New Document Types

1. Create schema in `pan_verification_upd.py`
2. Create extraction prompt in `helpers.py`
3. Add validation rules in `re_check.py`
4. Add handling in `app.py` `/api/verify` endpoint
5. Create tests for new type

### Debugging Extraction

Enable debug output:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Tips

- Cache NVIDIA model connection
- Batch process multiple documents
- Compress images before transmission
- Use CDN for static assets
- Enable database query caching

## Troubleshooting

**NVIDIA API not responding**
- Verify API key is valid
- Check network connectivity
- Check NVIDIA service status

**Image quality scoring too low**
- Increase lighting
- Improve image focus
- Use higher resolution
- Ensure document is clearly visible

**Extraction returning null fields**
- Document may be partially obscured
- Try higher quality image
- Ensure document type is correct

**Supabase connection failed**
- Verify URL and key in .env
- Check network connectivity
- Verify database tables exist

## Performance Metrics

- Average extraction time: 2-3 seconds per document
- Image quality check: < 100ms
- Field validation: < 50ms per field
- Multi-document processing (3 docs): 6-10 seconds

## License

Proprietary and confidential.

## Support

For issues or questions, refer to troubleshooting section or contact development team.
