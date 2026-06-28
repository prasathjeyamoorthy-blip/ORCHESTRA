# pan_verification_upd.py - Data Schemas & Validation

## Purpose
Defines Pydantic data models for all document types and implements comprehensive validation logic. Ensures type safety and data consistency throughout the application.

## Pydantic Schemas

### AadhaarData
Comprehensive schema for Aadhaar card extraction with 30+ fields:
- **Name Components**: name, first_name, middle_name, last_name
- **Father/Guardian**: father_name, father_first_name, father_middle_name, father_last_name
- **Mother/Guardian**: mother_name, mother_first_name, mother_middle_name, mother_last_name
- **Personal**: dob, gender, mobile_number, email_id, phone
- **Address**: flat_room_door, building_village, road_street_post, area_locality, district, state, pincode
- **Metadata**: aadhaar_number, document_type, is_legible, is_masked, confidence, issues

**Validation**:
- Optional fields default to None
- Confidence as required enum: "high", "medium", "low"
- Issues as optional list of problem descriptions

### PhotoData
Schema for profile photo validation:
- **Detection**: has_face, face_count, face_centered
- **Quality**: eyes_visible, plain_background, has_sunglasses, is_colored
- **Scoring**: confidence, issues

### SignatureData
Schema for signature validation:
- **Verification**: has_signature, is_handwritten, is_visible
- **Quality**: plain_background, is_cut_off
- **Scoring**: confidence, issues

## Validation Functions

### validate_aadhaar_fields(data)
Validates extracted Aadhaar data:
- Ensures name is present
- Validates DOB format (DD/MM/YYYY)
- Checks age is reasonable (0-120 years)
- Validates pincode (6 digits, not starting with 0)
- Verifies document type
- Returns list of validation errors

### validate_photo_fields(data)
Checks photo meets government standards:
- Face must be present and singular
- Eyes must be visible and open
- Background must be plain
- No sunglasses or dark glasses
- Must be color photo
- Returns list of validation errors

### validate_signature_fields(data)
Validates signature format:
- Signature must be handwritten
- Must be clearly visible
- Plain background required
- Cannot be cut off
- Returns validation errors

### cross_validate(aadhaar, photo, sig)
Performs cross-validation across all documents:
- Checks confidence levels
- Identifies inconsistencies
- Returns list of cross-validation issues

## Field Validation Details

### Mobile Number
- Pattern: `^[6-9][0-9]{9}$`
- Must be 10 digits starting with 6-9

### Aadhaar Number
- Pattern: `^([0-9]{12}|[Xx*]{8}[0-9]{4})$`
- Must be 12 digits or masked format

### Date of Birth
- Format: DD/MM/YYYY or YYYY-MM-DD
- Must be valid calendar date
- Cannot be future date
- Age validation: 0-120 years

### Pincode
- Pattern: `^[1-9]\d{5}$`
- Must be 6 digits
- Cannot start with 0

## Technical Checks

### basic_file_check(file_path, label)
Technical file validation:
- File exists
- Valid extension (.jpg, .jpeg, .png, .pdf)
- File size < 10MB
- File size > 20KB

### image_quality_check(file_path, label)
Image quality validation:
- Blur detection (Laplacian variance > 60)
- Brightness check (40-240 range)
- Resolution check (minimum 150x150px)
- Skips blur check for signatures

## Integration
- Used by `app.py` for request validation
- Provides type hints for IDE and type checkers
- Ensures consistent data format across API responses
- Facilitates error reporting and validation feedback

## Key Features
- Type-safe data handling with Pydantic
- Comprehensive validation with clear error messages
- Support for optional and required fields
- Confidence scoring for extraction quality
- Issue tracking for document problems
- Cross-document validation

## Notes
- All schemas use Optional[T] for potentially missing fields
- Country defaults to "India"
- Confidence is required field for all extraction results
- Issues list helps identify document quality problems
