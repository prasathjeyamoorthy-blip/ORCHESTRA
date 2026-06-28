# ORCHESTRA - Multi-Document Processing System

Advanced multi-document processor for extracting, validating, and correlating data from multiple Indian government documents.

## Overview

ORCHESTRA is a specialized system designed to:
- Extract data from 9 different document types
- Validate extracted data against business rules
- Correlate and cross-validate data across documents
- Intelligently merge conflicting information
- Provide confidence scores for merged data
- Handle document misclassification gracefully

## Supported Documents

1. **Aadhaar Card** - 12-digit unique identity
2. **Ration Card** - Food subsidy identification
3. **Address Proof** - Residence verification
4. **Caste Certificate** - Community status
5. **PAN Card** - Tax identification
6. **Voter ID** - Electoral registration
7. **Driving License** - Vehicle authorization
8. **Income Certificate** - Financial status
9. **Residence Certificate** - Domicile proof

## Project Structure

```
Orchestra/
├── DocumentUploadAgent/
│   ├── main.py              # Entry point and orchestration
│   ├── extractor.py         # Individual document extraction
│   ├── validator.py         # Cross-document validation
│   ├── merger.py            # Data merging logic
│   └── config.py            # Configuration and rules
└── README.md               # This file
```

## Key Features

### 1. Document Extraction
- Individual extraction from each document
- Format normalization
- Confidence scoring per field
- Extraction error handling

### 2. Cross-Document Validation
- Consistency checking across documents
- Conflict identification
- Data quality assessment
- Error reporting

### 3. Intelligent Data Merging
- Priority-based merging
- Consensus detection
- Confidence-weighted decisions
- User override support

### 4. Error Handling
- Graceful degradation
- Fallback options
- Detailed error reporting
- Recovery suggestions

## API Usage

### Main Entry Point

```python
from Orchestra.DocumentUploadAgent import main as orchestra

# Process multiple documents
result = orchestra.process_documents(
    auth_id="user-123",
    documents=[aadhaar_bytes, ration_bytes, address_bytes],
    document_types=["aadhaar", "ration_card", "address_proof"],
    primary_document="aadhaar"  # Optional: specify most reliable source
)
```

## Response Structure

```json
{
  "status": "success|partial|failed",
  "documents_processed": 3,
  "extracted_data": {
    "aadhaar": {
      "name": "John Doe",
      "dob": "01/01/1990",
      "confidence": 0.95
    },
    "ration_card": {
      "name": "John Doe",
      "family_head": "Father Name",
      "confidence": 0.87
    },
    "address_proof": {
      "address": "123 Main St",
      "tenant_name": "John Doe",
      "confidence": 0.92
    }
  },
  "merged_data": {
    "name": "John Doe",
    "dob": "01/01/1990",
    "address": "123 Main St",
    "phone": "9876543210"
  },
  "validation_results": {
    "consistency_score": 0.94,
    "conflicts": [],
    "warnings": [],
    "data_sources": {
      "name": "aadhaar",
      "dob": "aadhaar",
      "address": "address_proof",
      "phone": "aadhaar"
    }
  }
}
```

## Data Merging Strategy

### Priority Levels

1. **Tier 1 (Highest Priority)**
   - Primary document (if specified)
   - Score > 0.95 (nearly perfect)

2. **Tier 2**
   - Consensus data (2+ documents agree)
   - Score 0.85-0.94

3. **Tier 3**
   - High confidence individual source
   - Score 0.75-0.84

4. **Tier 4**
   - Acceptable confidence
   - Score 0.60-0.74

5. **Tier 5 (Lowest Priority)**
   - Low confidence sources
   - Score < 0.60
   - Requires user confirmation

### Conflict Resolution

When documents disagree:

```
Decision Tree:
├─ All documents agree → Use value (confidence 0.95+)
├─ 2+ documents agree → Use consensus value (confidence 0.85+)
├─ Primary document has highest confidence → Use primary (confidence 0.80+)
├─ One source significantly higher confidence → Use highest (confidence 0.75+)
└─ Ambiguous → Request user confirmation (confidence 0.50-0.74)
```

## Confidence Scoring

### Score Ranges

| Range | Meaning | Action |
|-------|---------|--------|
| 0.95-1.00 | Excellent - Exact match | Use directly |
| 0.85-0.94 | Good - Minor variations | Use with caution |
| 0.75-0.84 | Acceptable - Some variance | Review if critical |
| 0.60-0.74 | Low confidence - Needs review | Flag for user |
| < 0.60 | Very low - Unreliable | Requires confirmation |

### Confidence Calculation

```
Field Confidence = (
  extraction_confidence * 0.6 +
  validation_score * 0.3 +
  cross_document_agreement * 0.1
)
```

## Configuration

### Extraction Rules

Define per-document extraction patterns:

```python
EXTRACTION_RULES = {
    "aadhaar": {
        "name": {"pattern": "^[A-Za-z\\s]{3,50}$", "required": True},
        "dob": {"pattern": "^\\d{1,2}/\\d{1,2}/\\d{4}$", "required": True},
        "phone": {"pattern": "^[6-9][0-9]{9}$", "required": False}
    },
    "ration_card": {
        "name": {"required": True},
        "family_head": {"required": True}
    }
}
```

### Validation Rules

Define cross-document validation:

```python
VALIDATION_RULES = {
    "name_match": {
        "threshold": 0.85,  # 85% string similarity required
        "documents": ["aadhaar", "ration_card", "address_proof"]
    },
    "dob_match": {
        "threshold": 1.0,  # Exact match required
        "documents": ["aadhaar", "income_certificate"]
    }
}
```

## Usage Examples

### Basic Multi-Document Processing

```python
from Orchestra.DocumentUploadAgent import main

# Process three documents
result = main.process_documents(
    auth_id="user-123",
    documents=[
        aadhaar_file_bytes,
        ration_card_file_bytes,
        address_proof_file_bytes
    ],
    document_types=["aadhaar", "ration_card", "address_proof"]
)

if result["status"] == "success":
    merged_data = result["merged_data"]
    print(f"Name: {merged_data['name']}")
    print(f"Address: {merged_data['address']}")
else:
    print(f"Processing failed: {result['errors']}")
```

### With Primary Document Specification

```python
# Specify Aadhaar as most reliable source
result = main.process_documents(
    auth_id="user-123",
    documents=[aadhaar_bytes, ration_bytes],
    document_types=["aadhaar", "ration_card"],
    primary_document="aadhaar",
    confidence_threshold=0.75  # Only use data with 75%+ confidence
)
```

### Handling Conflicts

```python
result = main.process_documents(...)

if result["validation_results"]["conflicts"]:
    conflicts = result["validation_results"]["conflicts"]
    for conflict in conflicts:
        print(f"Field: {conflict['field']}")
        print(f"Document A: {conflict['value_a']} (score: {conflict['score_a']})")
        print(f"Document B: {conflict['value_b']} (score: {conflict['score_b']})")
        # Request user input for resolution
```

## Error Handling

### Common Errors

```python
try:
    result = main.process_documents(...)
except main.ExtractionError as e:
    print(f"Extraction failed: {e.document_type} - {e.message}")
except main.ValidationError as e:
    print(f"Validation failed: {e.field} - {e.message}")
except main.MergingError as e:
    print(f"Merging failed: {e.conflicts}")
```

### Error Recovery

- **Extraction failures**: Continue with remaining documents
- **Validation errors**: Flag field as unverified
- **Merge conflicts**: Return multiple options
- **Type misidentification**: Try alternative document types

## Performance

- **2 documents**: 4-6 seconds
- **3 documents**: 6-9 seconds
- **4 documents**: 8-12 seconds

Factors affecting performance:
- Image quality and size
- Document complexity
- Number of fields
- Validation rule complexity

## Integration with Backend

### Flask Integration

```python
from Orchestra.DocumentUploadAgent import main as orchestra

@app.route('/api/multi_documents/verify', methods=['POST'])
def verify_multi_documents():
    auth_id = request.form.get('auth_id')
    files = request.files.getlist('documents')
    doc_types = request.form.getlist('document_types')
    
    # Read file bytes
    file_bytes = [f.read() for f in files]
    
    # Process with ORCHESTRA
    result = orchestra.process_documents(
        auth_id=auth_id,
        documents=file_bytes,
        document_types=doc_types
    )
    
    return jsonify(result)
```

## Extending ORCHESTRA

### Add New Document Type

1. **Create Extractor**
   - Add extraction logic in `extractor.py`
   - Define field mappings

2. **Create Validator**
   - Add validation rules in `validator.py`
   - Define field constraints

3. **Update Configuration**
   - Add to `EXTRACTION_RULES`
   - Add to `VALIDATION_RULES`
   - Define priority and confidence thresholds

4. **Test**
   - Add unit tests
   - Test with real documents
   - Validate merging logic

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Low confidence scores | Poor image quality | Reupload clearer documents |
| Extraction failures | Unsupported format | Ensure document format is supported |
| High conflict rates | Outdated/incorrect info | Verify source document accuracy |
| Slow processing | Large file sizes | Compress images before upload |
| Merge errors | Complex rule conflicts | Review validation rules |

## Best Practices

1. **Document Order**: Place most reliable document first
2. **Image Quality**: Use clear, well-lit images
3. **Document Verification**: Verify all source documents are valid
4. **Confidence Threshold**: Set appropriate thresholds for your use case
5. **Error Handling**: Always handle partial failures gracefully
6. **Logging**: Enable detailed logging for debugging

## Future Enhancements

- [ ] Support for more document types
- [ ] ML-based confidence scoring
- [ ] Real-time conflict resolution UI
- [ ] Document tamper detection
- [ ] Handwritten field support
- [ ] Multi-language support
- [ ] OCR for non-standard documents

## License

Proprietary and confidential.

## Support

For issues or questions, contact the development team.
