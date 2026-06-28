# PAN Application Platform

A comprehensive multi-document verification system for Indian PAN (Permanent Account Number) applications with support for Aadhaar card extraction, validation, and multi-document processing.

## Project Overview

This platform provides:
- **Document Extraction**: AI-powered extraction from Aadhaar cards and other Indian documents
- **Data Validation**: Real-time field validation and cross-document verification
- **Multi-Document Processing**: ORCHESTRA system for correlating data across multiple documents
- **User Consent Workflow**: Guided workflow for users to review and confirm extracted data
- **Voice Integration**: Voice-enabled interface for accessibility
- **Secure Storage**: Supabase integration for secure document storage

## Project Structure

```
integ/
├── frontend/              # React.js frontend application
├── pan_verification/      # Core extraction and verification backend
├── pan-rag/              # Document retrieval and processing
├── voice-agent/          # Voice input/output service
├── auth-app/             # Authentication service
├── Orchestra/            # Multi-document processing system
├── supabase/             # Database configuration
├── .venv/                # Python virtual environment
└── README.md             # This file
```

## Key Folders

### [Frontend](./frontend/README.md)
React-based web application for user interface, document upload, and data review.

### [PAN Verification](./pan_verification/README.md)
Core backend service for document extraction, field validation, and data processing.

### [PAN RAG](./pan-rag/README.md)
Document retrieval and question-answering system using retrieval-augmented generation.

### [Voice Agent](./voice-agent/README.md)
Voice interface for speech-to-text input and text-to-speech output.

### [Auth App](./auth-app/README.md)
Authentication and authorization service with token management.

### [ORCHESTRA](./Orchestra/README.md)
Multi-document processor for correlating data across 9 different document types.

### [Supabase](./supabase/README.md)
Database schema, migrations, and configuration documentation.

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Supabase account
- NVIDIA API key for vision model

### Setup Backend

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
cd pan_verification
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run server
python app.py  # Server runs on http://localhost:5000
```

### Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your API endpoint

# Start development server
npm run dev  # Server runs on http://localhost:5173
```

## API Endpoints

### Document Processing
- `POST /api/verify` - Upload document for extraction and verification
- `POST /api/preview` - Preview extracted data without saving
- `POST /api/confirm_save` - Save user-verified document data

### Document Retrieval
- `POST /api/get_docs` - Get all documents for user
- `POST /api/get_person_docs` - Get documents for specific person

### Multi-Document Processing (ORCHESTRA)
- `POST /api/multi_documents/verify` - Process multiple documents
- `POST /api/multi_documents/confirm` - Save multi-document results

### Authentication
- `POST /api/signup` - Create new account
- `POST /api/login` - User login

## Data Flow

### Single Document Workflow
1. **Upload** → User uploads Aadhaar document
2. **Extract** → AI extracts fields with confidence scores
3. **Validate** → System validates field formats
4. **Review** → User reviews extracted data
5. **Confirm** → User confirms and data is saved

### Multi-Document Workflow
1. **Upload** → User uploads multiple documents (Aadhaar, Ration Card, Address Proof, etc.)
2. **Extract** → ORCHESTRA extracts from each document
3. **Validate** → Cross-document validation and conflict detection
4. **Merge** → Intelligent merging of data across documents
5. **Review** → User reviews merged and validated data
6. **Confirm** → User confirms and all documents are saved

## Technology Stack

### Frontend
- **React.js** - UI framework
- **Vite** - Build tool
- **Supabase** - Authentication client

### Backend
- **Flask** - Web framework
- **Pydantic** - Data validation
- **OpenCV** - Image processing
- **NVIDIA Vision Model** - Document extraction

### Database
- **Supabase** - PostgreSQL-based backend-as-a-service

### Voice
- **WebRTC** - Audio capture
- **TTS/STT APIs** - Voice processing

## Environment Variables

### Backend (.env)
```
NVIDIA_META_90B=your_nvidia_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
FLASK_ENV=development
```

### Frontend (.env)
```
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_anon_key
VITE_API_BASE_URL=http://localhost:5000
```

## Documentation

- [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) - Production deployment guide
- [ORCHESTRA_FOLDER_PURPOSE.md](./ORCHESTRA_FOLDER_PURPOSE.md) - Multi-document system overview
- [ORCHESTRA_QUICK_REFERENCE.md](./ORCHESTRA_QUICK_REFERENCE.md) - ORCHESTRA API reference

## Features

### ✅ Completed
- Document type detection
- Aadhaar field extraction (30+ fields)
- Real-time validation
- Multi-field display with icons and color-coding
- User confirmation workflow
- Data persistence to Supabase
- Profile photo validation
- Cross-document validation framework

### 🔄 In Progress
- Multi-document merging refinement
- Conflict resolution UI
- Additional document type support

### 📋 Planned
- Mobile app
- Advanced analytics
- Batch processing
- Document tamper detection
- OCR for handwritten documents

## Testing

### Unit Tests
```bash
cd pan_verification
pytest tests/
```

### Integration Tests
```bash
# Test document extraction
python -m pytest tests/integration/test_extraction.py

# Test multi-document processing
python -m pytest tests/integration/test_orchestra.py
```

## Security

- Environment variables never committed
- API keys stored securely
- HTTPS enforced in production
- CORS properly configured
- Input validation on all endpoints
- Rate limiting enabled
- Database backups automated

## Support & Troubleshooting

### Common Issues

**Q: "NVIDIA API key not found"**
A: Set `NVIDIA_META_90B` in your `.env` file. Get it from https://build.nvidia.com

**Q: "Supabase connection failed"**
A: Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct in `.env`

**Q: "Image quality too low"**
A: Upload a clearer, well-lit image of the document

**Q: "Field extraction incomplete"**
A: The document may be partially visible or obscured. Try uploading a clearer image

## License

This project is proprietary and confidential.

## Contributors

Development team working on PAN application platform.

## Contact

For issues or questions, please refer to project documentation or contact the development team.
