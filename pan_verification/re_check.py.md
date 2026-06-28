# re_check.py - Regex-Based Validation

## Purpose
Provides regex-based validation functions for extracted field values. Ensures data matches expected patterns before database storage and user presentation.

## Core Validation Functions

### validate_document(input_dict)
Main validation entry point for document data.
- **Input**: Dictionary with aadhaar, mobile, dob, gender, name
- **Returns**: Validation result object with pass/fail status
- **Validates**: All required fields with appropriate patterns

### validate_aadhaar(aadhaar_number)
Validates Aadhaar number format.
- **Pattern**: `^([0-9]{12}|[Xx*]{8}[0-9]{4})$`
- **Accepts**: 12-digit number or masked format (XXXX XXXX 1234)
- **Returns**: Boolean (valid/invalid)

### validate_mobile(mobile_number)
Validates mobile number format.
- **Pattern**: `^[6-9][0-9]{9}$`
- **Requires**: 10 digits starting with 6, 7, 8, or 9
- **Returns**: Boolean (valid/invalid)

### validate_dob(date_of_birth)
Validates date of birth format and logic.
- **Accepts**: DD/MM/YYYY or DD-MM-YYYY format
- **Checks**: Valid calendar date
- **Verifies**: Age is reasonable (typically 18-100)
- **Returns**: Boolean (valid/invalid)

### validate_gender(gender_value)
Validates gender field value.
- **Accepts**: Male, Female, Transgender, Other
- **Case-Insensitive**: Handles variations
- **Returns**: Boolean (valid/invalid)

### validate_state(state_name)
Validates state/union territory name.
- **Accepts**: All Indian states and UTs
- **Returns**: Boolean (valid/invalid)

## Validation Patterns

### Phone Number
```
Pattern: ^[6-9][0-9]{9}$
Example: 9876543210
```

### Aadhaar Number
```
Pattern: ^([0-9]{12}|[Xx*]{8}[0-9]{4})$
Examples: 
- 123456789012 (full)
- XXXX XXXX 1234 (masked)
```

### Date of Birth
```
Accepted: DD/MM/YYYY or DD-MM-YYYY
Example: 15/01/1990
Validation: Proper date, reasonable age
```

### Email Address
```
Pattern: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$
Example: user@example.com
```

### Pincode
```
Pattern: ^[1-9]\d{5}$
Example: 600001
Note: First digit cannot be 0
```

## Error Messages

Provides clear feedback:
- "Invalid Aadhaar format" - Not 12 digits
- "Invalid mobile number" - Wrong format or length
- "Invalid date of birth" - Bad format or logic
- "Invalid gender" - Unknown value
- "Invalid state" - Not in list
- "Invalid email" - Not proper format

## Integration

Used by:
- `app.py` - Field validation before save
- `pan_verification_upd.py` - Secondary validation
- Document verification workflows

## Data Types Validated

- **Aadhaar Number**: String (12 digits or masked)
- **Mobile Number**: String (10 digits, starts 6-9)
- **Date of Birth**: String (DD/MM/YYYY format)
- **Gender**: Enum string
- **State**: Enum string
- **Email**: String (email format)
- **Pincode**: String (6 digits)
- **Name**: String (alphanumeric + spaces)

## Validation Results

Returns structured validation results:
```python
{
  "is_valid": true/false,
  "errors": [],  # List of validation errors
  "warnings": [],  # Non-critical issues
  "corrected_values": {}  # Auto-corrected values if applicable
}
```

## Special Cases

### Name Validation
- Accepts: Letters, spaces, hyphens, apostrophes
- Minimum length: 3 characters
- Maximum length: 100 characters

### Address Fields
- Allow: Alphanumeric, spaces, hyphens, commas, periods
- Support: Indian address conventions

### Numbers
- Aadhaar: Numeric or masked
- Mobile: Numeric with specific pattern
- Pincode: 6 numeric digits

## Performance
- Regex compilation: < 1ms
- Pattern matching: < 5ms per field
- Suitable for real-time validation

## Notes
- Regex patterns compiled for efficiency
- Case-insensitive comparisons where appropriate
- Handles variations in input format
- Provides both pass/fail and detailed feedback
- Used for both real-time and batch validation
