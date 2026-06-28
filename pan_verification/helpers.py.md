# helpers.py - Extraction Helpers & Prompts

## Purpose
Contains all extraction prompts, VLM API calls, document type detection, and helper functions for processing documents. Defines the instructions for the NVIDIA vision model to extract specific information from documents.

## Key Components

### Prompts
- **AADHAAR_PROMPT** - Extracts 30+ fields from Aadhaar cards:
  - Name components (first, middle, last, full)
  - Father/Guardian information
  - Mother/Guardian information
  - Personal details (DOB, gender, phone, email)
  - Address breakdown (flat, building, road, locality, district, state, pincode)
  - Residential status and confidence scoring

- **PROFILE_PHOTO_PROMPT** - Validates profile photos for suitability
- **DOCUMENT_TYPE_PROMPT** - Detects document type and identifies human faces

### Main Functions

#### run_vlm(prompt, file_bytes, filename)
Calls NVIDIA Meta-Llama vision model API with prompt and document image.
- **Input**: Prompt text, image bytes, filename
- **Output**: Parsed JSON response from VLM
- **Error Handling**: Returns error message on API failure

#### detect_document_type(file_bytes, filename)
Identifies document type using VLM.
- **Returns**: 
  ```json
  {
    "document_type": "aadhaar_card|profile_photo|pan_card|...",
    "is_human_face": true/false,
    "confidence": "high|medium|low"
  }
  ```

#### validate_profile_photo(file_bytes, filename)
Validates if photo is suitable for government ID applications.
- **Checks**: Face presence, centering, eyes visible, background plain
- **Returns**: Validation results with suitability flag

### API Configuration
- Uses NVIDIA Build API with Meta/Llama-3.2-90B-Vision-Instruct model
- API key from environment variable: `NVIDIA_META_90B`
- Handles base64 image encoding for API transmission
- Implements error handling and retry logic

## Key Features
- Comprehensive extraction prompts optimized for Indian documents
- Support for multiple document types
- Quality assessment criteria
- Confidence scoring guidance
- Handling of masked/partial information
- Graceful error handling

## Integration
Used by:
- `app.py` - Document processing endpoints
- `pan_verification_upd.py` - Schema validation
- Multi-document processing workflows

## Environment Requirements
- `NVIDIA_META_90B` API key must be set
- Network access to NVIDIA Build API
- Image file must be readable

## Notes
- Prompts are carefully engineered for accurate extraction
- Vision model handles various image qualities and angles
- Returns raw JSON from model - parsed by caller
- No database operations in this module
