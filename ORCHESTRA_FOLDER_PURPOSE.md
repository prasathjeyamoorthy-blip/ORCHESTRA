# ORCHESTRA Folder Purpose

ORCHESTRA is a multi-document processing system designed to extract, validate, and correlate data from multiple Indian government documents.

## Overview

The ORCHESTRA folder contains modules for:
- Multi-document extraction and validation
- Cross-document data correlation
- Confidence scoring and data merging
- Handling of multiple document types

## Supported Document Types

ORCHESTRA can process:
1. **Aadhaar Card** - 12-digit unique identity number
2. **Ration Card** - Food subsidy identification
3. **Address Proof** - Residence verification
4. **Caste Certificate** - Community verification
5. **PAN Card** - Tax identification
6. **Voter ID** - Electoral registration
7. **Driving License** - Vehicle authorization
8. **Income Certificate** - Financial status
9. **Residence Certificate** - Domicile proof

## Key Features

- **Cross-Document Validation**: Compares data across multiple documents for consistency
- **Resolution-Based Merging**: Intelligently merges conflicting data from multiple sources
- **Confidence Scoring**: Provides confidence levels for extracted and merged data
- **Misclassification Handling**: Detects and handles document type misidentification
- **Error Recovery**: Gracefully handles extraction errors

## Integration Points

- Backend: `/api/multi_documents/verify` - Process multiple documents
- Backend: `/api/multi_documents/confirm` - Save multi-document results
- Frontend: `multi-document-upload.jsx` - Multi-document upload component

## Usage

See `ORCHESTRA_QUICK_REFERENCE.md` for quick start and API details.
