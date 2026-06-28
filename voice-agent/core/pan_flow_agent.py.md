# pan_flow_agent.py - PAN Application Flow

## Purpose
Specialized agent for managing the PAN application workflow through voice interface. Guides users through the complete application process from start to submission.

## Key Workflows

### Complete Application Flow
```
START
  ↓
UPLOAD_DOCUMENTS - Collect required documents
  ├─ Aadhaar
  ├─ Photo
  ├─ Signature
  └─ Address Proof
  ↓
EXTRACT_DATA - Extract information from documents
  ↓
REVIEW_DATA - User reviews extracted information
  ├─ Correct errors
  ├─ Fill missing fields
  └─ Confirm accuracy
  ↓
VERIFY_INFO - Cross-verify information
  ↓
SUBMIT - Submit application
  ↓
CONFIRMATION - Provide reference number
  ↓
END
```

## Main Classes

### PANFlowAgent
Primary orchestrator for PAN application process.

**Initialization**:
```python
agent = PANFlowAgent(
    user_id="user-123",
    language="en-IN"
)
```

**Key Methods**:
- `start_application()` - Initialize new application
- `guide_document_upload()` - Walk through document upload
- `manage_data_review()` - Help review extracted data
- `handle_corrections()` - Process user corrections
- `verify_information()` - Cross-verify information
- `submit_application()` - Submit for processing
- `get_status()` - Check application status

## Document Management

### Required Documents
```python
required_documents = {
    "aadhaar": {
        "description": "Aadhaar card",
        "required": True,
        "fields": ["name", "dob", "address"]
    },
    "photo": {
        "description": "Passport-style photo",
        "required": True,
        "constraints": ["face visible", "plain background"]
    },
    "signature": {
        "description": "Signature",
        "required": True,
        "constraints": ["handwritten", "clear"]
    }
}
```

### Upload Guidance
- Clear instructions for each document
- Tips for good quality
- Automatic validation
- Retry on quality failure

## Data Review Process

### Extracted Fields
```python
extracted_fields = {
    "name": "John Doe",
    "father_name": "Father Name",
    "dob": "01/01/1990",
    "address": "123 Main St",
    "phone": "9876543210",
    "gender": "Male"
}
```

### Review Steps
1. Present each field via voice
2. Ask for confirmation
3. Allow corrections
4. Fill missing fields
5. Confirm all data

## Correction Handling

### Correction Flow
```
User: "My phone number is wrong"
Agent: "What's your correct phone number?"
User: "9876543210"
Agent: "Confirming: 9-8-7-6-5-4-3-2-1-0. Correct?"
User: "Yes"
Agent: "Updated. Continue review?"
```

## Information Verification

### Cross-Verification
- Compare multiple document sources
- Identify inconsistencies
- Request clarification
- Resolve conflicts

### Validation Rules
```python
validations = {
    "name": "Match across documents?",
    "dob": "Consistent date of birth?",
    "address": "Same permanent address?",
    "phone": "Valid format? (10 digits)"
}
```

## Submission Process

### Pre-Submission Checks
1. All required documents uploaded
2. All extracted data confirmed
3. Validations passed
4. User agrees to terms
5. Final confirmation

### Submission Steps
```python
def submit_application(self):
    # Perform final validation
    if not self.validate_all_data():
        self.ask_user_to_fix()
        return
    
    # Call backend API
    result = self.backend.submit(self.data)
    
    # Provide confirmation
    self.provide_confirmation(result)
```

## State Machine

### States
```
INITIALIZED → AWAITING_UPLOAD → UPLOADING
  → DATA_EXTRACTED → REVIEWING → VERIFIED
  → SUBMITTING → SUBMITTED → COMPLETED
```

### State Transitions
```python
state_transitions = {
    "INITIALIZED": ["AWAITING_UPLOAD"],
    "AWAITING_UPLOAD": ["UPLOADING"],
    "UPLOADING": ["DATA_EXTRACTED", "UPLOAD_FAILED"],
    "DATA_EXTRACTED": ["REVIEWING", "EXTRACTION_FAILED"],
    "REVIEWING": ["VERIFIED", "NEEDS_CORRECTION"],
    "VERIFIED": ["SUBMITTING"],
    "SUBMITTING": ["SUBMITTED", "SUBMISSION_FAILED"],
    "SUBMITTED": ["COMPLETED"]
}
```

## Error Recovery

### Common Issues
- **Document Upload Failed**: Retry or try different image
- **Data Extraction Failed**: Provide manual input
- **Validation Failed**: Show errors and request correction
- **Submission Failed**: Save progress and retry

### Recovery Strategies
```python
def handle_document_upload_failure(self):
    # Ask user to try again
    self.speak("Document upload failed. Let's try again.")
    # Provide tips
    self.speak("Make sure:")
    self.speak("- Document is clearly visible")
    self.speak("- Good lighting")
    self.speak("- Entire document in frame")
```

## Progress Tracking

### Application Progress
```python
progress = {
    "overall": 45,  # Percentage
    "documents": 60,  # Documents uploaded
    "data_review": 30,  # Data confirmation
    "verification": 0,  # Verification status
    "submission": 0  # Submission status
}
```

### Resume Capability
- Save application state
- Allow resume later
- Restore previous data
- Continue from last step

## Guidance System

### Context-Specific Help
- Tips for current step
- Common mistakes
- Best practices
- Estimated time remaining

### Interactive Guidance
```
Current step: Photo Upload
Tips:
- Face should be front and center
- Eyes clearly visible
- No glasses or head gear
- Plain white or light background
- Good lighting
```

## Integration

### With Backend API
```python
# Upload document
response = api.upload_document(
    auth_id=self.user_id,
    document_type="aadhaar",
    document_bytes=image_bytes
)

# Submit application
response = api.submit_application(
    auth_id=self.user_id,
    application_data=self.extracted_data
)
```

### With Voice Services
```
User Voice Input → STT → Intent Extract
  → Application Logic → Response Generate → TTS → Audio Output
```

## Configuration

### Application Settings
```python
settings = {
    "language": "en-IN",
    "required_documents": ["aadhaar", "photo", "signature"],
    "timeout_minutes": 30,
    "allow_offline_mode": False,
    "auto_save_interval": 300  # seconds
}
```

## Performance

### Timing
- Document upload: 5-30 seconds
- Data extraction: 2-5 seconds
- Review process: 2-5 minutes
- Total application: 5-15 minutes

## Monitoring

### Application Metrics
```python
metrics = {
    "applications_started": count,
    "applications_completed": count,
    "completion_rate": percentage,
    "average_duration": time,
    "failure_rate": percentage,
    "most_common_errors": list
}
```

## Best Practices

### User Guidance
- Clear, step-by-step instructions
- Anticipated questions answered
- Visual examples provided
- Progress indication shown

### Error Handling
- Graceful error messages
- Recovery suggestions
- Retry options
- Escalation path

### Data Protection
- Secure transmission
- Encryption at rest
- Audit trail maintained
- GDPR compliant

## Future Enhancements

- [ ] Multi-language guidance
- [ ] Video tutorials integration
- [ ] AI-powered quality checks
- [ ] Predictive error detection
- [ ] Personalized recommendations

## Dependencies
- `core.agent` - Base agent
- `core.voice_receptionist` - Voice interface
- `api_client` - Backend API
- `state_machine` - State management

## Notes
- Stateful across interactions
- Supports save and resume
- Error recovery built-in
- Extensible workflow
- User-centric design
