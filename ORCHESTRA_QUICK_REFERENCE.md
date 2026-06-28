# ORCHESTRA Quick Reference

## Overview
ORCHESTRA is a multi-document processor in `pan_verification/ORCHESTRA/` that extracts data from 9 document types and provides cross-document validation.

## Main Components

### DocumentUploadAgent/main.py
- Entry point for multi-document processing
- Handles document routing and extraction

### DocumentUploadAgent/extractor.py
- Individual document extraction
- Format normalization

### DocumentUploadAgent/validator.py
- Cross-document validation
- Conflict detection and resolution

## API Endpoints

### 1. `/api/multi_documents/verify` (POST)
Upload multiple documents for extraction and validation.

**Request:**
```
POST /api/multi_documents/verify
Content-Type: multipart/form-data

Parameters:
- auth_id: User authentication ID
- documents: Array of files (Aadhaar, Ration Card, Address Proof, etc.)
- document_types: Array of document type names
```

**Response:**
```json
{
  "status": "success",
  "documents_processed": 3,
  "extracted_data": {
    "aadhaar": { ... },
    "ration_card": { ... },
    "address_proof": { ... }
  },
  "merged_data": { ... },
  "validation_results": {
    "consistency_score": 0.95,
    "conflicts": [],
    "warnings": []
  }
}
```

### 2. `/api/multi_documents/confirm` (POST)
Save multi-document processing results.

**Request:**
```
POST /api/multi_documents/confirm
Content-Type: application/json

{
  "auth_id": "user-id",
  "merged_data": { ... },
  "document_sources": {
    "name": "aadhaar",
    "dob": "ration_card"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "person_id": "person-123",
  "doc_ids": ["doc-1", "doc-2", "doc-3"],
  "message": "Multi-document verification complete"
}
```

## Supported Document Types

| Type | Code | Extraction Fields |
|------|------|-------------------|
| Aadhaar | `aadhaar` | Name, DOB, Gender, Address, etc. |
| Ration Card | `ration_card` | Name, Family, Ration Number |
| Address Proof | `address_proof` | Address, Landlord, Tenure |
| Caste Certificate | `caste_certificate` | Name, Caste, DOB |
| PAN Card | `pan_card` | Name, PAN Number, DOB |
| Voter ID | `voter_id` | Name, Voter Number, Address |
| Driving License | `driving_license` | Name, DL Number, DOB, Address |
| Income Certificate | `income_certificate` | Name, Income, DOB, Address |
| Residence Certificate | `residence_certificate` | Name, Address, Tenure |

## Data Merging Strategy

ORCHESTRA uses this priority order for conflicting data:

1. **Primary Document** (User specified as most reliable)
2. **High Confidence Matches** (Score > 0.9)
3. **Consensus Data** (2 or more documents agree)
4. **Secondary Sources** (Score > 0.7)
5. **User Input** (For ambiguous fields)

## Confidence Scoring

- **0.95-1.0**: Exact match across documents
- **0.85-0.94**: Strong confidence, minor variations
- **0.75-0.84**: Moderate confidence, acceptable
- **0.60-0.74**: Low confidence, may need review
- **< 0.60**: Very low, typically requires user verification

## Error Handling

Errors are handled gracefully:
- Missing documents: Continues with available data
- Extraction failures: Reports with fallback to manual data
- Validation conflicts: Returns all options for user selection
- Format mismatches: Auto-converts to standard format

## Integration Example

```python
from ORCHESTRA.DocumentUploadAgent import main as orchestra

# Process multiple documents
result = orchestra.process_documents(
    auth_id="user-123",
    documents=[aadhaar_bytes, ration_bytes, address_bytes],
    document_types=["aadhaar", "ration_card", "address_proof"]
)

# Access merged and validated data
merged_data = result["merged_data"]
validation_results = result["validation_results"]
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Document not recognized | Wrong document type | Verify document type code matches actual document |
| Extraction failures | Low image quality | Reupload clearer images |
| High conflict score | Inconsistent data | Review documents for accuracy |
| Missing fields | Document type doesn't contain field | Check supported fields for document type |

## Next Steps

1. Enable multi-document upload in frontend
2. Test with actual Aadhaar + Address Proof combination
3. Fine-tune merging rules based on real data
4. Add UI for conflict resolution
