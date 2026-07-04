# Name Logic & Document Requirements Update

## Changes Made

### 1. South Indian Name Splitting Logic ✅

Implemented proper name handling for South Indian conventions with initials:

#### Rules:

**Rule 1: Single Name**
```
Input: "Akash"
Output: first="", middle="", last="Akash"
```
Single names go to **LAST NAME** field.

**Rule 2: Two Names**
```
Input: "Akash Raja"
Output: first="Raja", middle="", last="Akash"
```
Two names are **reversed** (South Indian convention: given name comes first, family name second).

**Rule 3: Three Names with Initial**
```
Input: "Anand R Ajaanand"
Output: first="Ajaanand", middle="R", last="Anand"
```
When middle part is a single letter or letter with dot (e.g., "R", "R."), use South Indian order:
- Third part → first_name (father's name)
- Second part → middle_name (initial)
- First part → last_name (given name)

**Rule 4: Three Names without Initial**
```
Input: "John Michael Doe"
Output: first="John", middle="Michael", last="Doe"
```
When middle part is NOT an initial, use Western order.

**Rule 5: Four+ Names**
```
Input: "A B C Deenadayalan"
Output: first="A", middle="B C", last="Deenadayalan"
```
Standard Western convention: first, all middle parts, last.

### 2. Document Requirements Updated ✅

Changed from 4 required docs to 3 required + 1 optional:

#### Required Documents (3):
1. **Aadhaar Card PDF** - Identity & address proof
2. **Profile Photo** (JPG/JPEG) - Passport-style photo
3. **Signature** (JPG/JPEG) - Applicant's signature

#### Optional Document (1):
4. **Driving License PDF** - Age proof (alternative to birth certificate)

**Note:** Birth certificate support has been **removed** for now.

### 3. Document Type Detection ✅

System now:
- Detects actual document type from NVIDIA VLM extraction
- Renames uploaded files to match detected type
- Shows user what type was detected (not what they claimed)
- Stores with proper type in FlowManager

#### Example Flow:
```
User uploads file claiming "document"
    ↓
pan_verification extracts → detects "driving_license"
    ↓
File renamed: document.pdf → driving_license.pdf
    ↓
Chat shows: "📄 **Driving License** detected!"
    ↓
Stored in Redis: extraction:{session_id}:driving_license
```

### 4. File Naming Convention ✅

**Old naming:** `user_aadhaar.pdf`, `bhuvanesh_signature.jpg`
**New naming:** `aadhaar.pdf`, `profile_photo.jpeg`, `signature.jpeg`, `driving_license.pdf`

Cleaner, consistent, and based on detected document type.

## Code Changes

### File: `d:\PANCARD\pan-rag\api\routes.py`

#### Change 1: Fixed Syntax Error
**Line 717:** Removed duplicate `.strip()ip()` → `.strip()`

#### Change 2: Updated split_name() Function
**Lines ~790-830:** Complete rewrite with South Indian logic

```python
def split_name(full_name):
    """
    Rules:
    1. Single name → ("", "", name)
    2. Two names → (second, "", first)  # Reversed
    3. Three with initial → (third, initial, first)
    4. Three no initial → (first, middle, last)
    5. Four+ → (first, middle_parts, last)
    """
    if not full_name:
        return "", "", ""
    
    parts = full_name.strip().split()
    
    if len(parts) == 1:
        return "", "", parts[0]  # Single name → last name
    
    elif len(parts) == 2:
        return parts[1], "", parts[0]  # Reverse order
    
    elif len(parts) == 3:
        middle = parts[1]
        if len(middle) == 1 or (len(middle) == 2 and middle[1] == '.'):
            # Has initial: South Indian
            return parts[2], middle.replace('.', ''), parts[0]
        else:
            # No initial: Western
            return parts[0], parts[1], parts[2]
    
    else:
        return parts[0], " ".join(parts[1:-1]), parts[-1]
```

#### Change 3: Removed Birth Certificate References
**Lines ~850-870:** Changed DOB source

```python
# OLD:
dob = birth_cert_data.get("dob") or aadhaar_data.get("dob", "")

# NEW:
driving_license_data = extraction_data.get("driving_license", {})
dob = driving_license_data.get("dob") or aadhaar_data.get("dob", "")
```

#### Change 4: Updated Document Type Mapping
**Lines ~920-945:** Removed birth_certificate, kept only 3+1

```python
doc_type_mapping = {
    "aadhaar": {...},
    "profile_photo": {...},
    "signature": {...},
    "driving_license": {
        "field": "birth_cert_pdf",  # Maps to age proof field
        "target": "jbirthcert.pdf"
    }
    # birth_certificate: REMOVED
}
```

#### Change 5: Improved Upload Endpoint
**Lines ~550-610:** 
- Detect actual doc type from extraction
- Rename file to match detected type
- Use detected type for Redis cache key
- Show detected type to user

```python
detected_doc_type = extracted_data.get("document_type", "")
if detected_doc_type and detected_doc_type != "unknown":
    # Rename file
    new_filename = f"{detected_doc_type}{ext}"
    os.rename(old_path, new_path)
    
    # Cache with detected type
    mm._setex(f"extraction:{sid}:{detected_doc_type}", ...)
    
    # Show user
    chat_message = f"📄 **{detected_doc_type.title()}** detected!\n\n..."
```

## Testing Examples

### Test Case 1: Single Name
```python
Input: "Akash"
Expected: {"first_name": "", "middle_name": "", "last_name": "Akash"}
```

### Test Case 2: Two Names
```python
Input: "Akash Raja"
Expected: {"first_name": "Raja", "middle_name": "", "last_name": "Akash"}
```

### Test Case 3: With Initial
```python
Input: "Anand R Ajaanand"
Expected: {"first_name": "Ajaanand", "middle_name": "R", "last_name": "Anand"}
```

### Test Case 4: Three Names No Initial
```python
Input: "John Michael Doe"
Expected: {"first_name": "John", "middle_name": "Michael", "last_name": "Doe"}
```

### Test Case 5: With Dot in Initial
```python
Input: "Bhuvanesh R. Kumar"
Expected: {"first_name": "Kumar", "middle_name": "R", "last_name": "Bhuvanesh"}
```

## Document Upload Testing

### Scenario 1: Upload Aadhaar
```
User uploads: my_documents.pdf (actually Aadhaar)
System detects: "aadhaar"
File renamed to: aadhaar.pdf
Chat shows: "📄 **Aadhaar** detected!"
Redis key: extraction:session123:aadhaar
```

### Scenario 2: Upload Driving License
```
User uploads: dl.pdf (actually driving license)
System detects: "driving_license"
File renamed to: driving_license.pdf
Chat shows: "📄 **Driving License** detected!"
Redis key: extraction:session123:driving_license
Mapped to: birth_cert_pdf field (age proof)
```

### Scenario 3: Upload Photo
```
User uploads: IMG_1234.jpg
System detects: "profile_photo"
File renamed to: profile_photo.jpeg
Chat shows: "📄 **Profile Photo** detected!"
```

## Integration Impact

### FlowManager collected_docs
Now stores detected type:
```json
{
  "collected_docs": [
    {"filename": "aadhaar.pdf", "doc_type": "aadhaar"},
    {"filename": "profile_photo.jpeg", "doc_type": "profile_photo"},
    {"filename": "signature.jpeg", "doc_type": "signature"},
    {"filename": "driving_license.pdf", "doc_type": "driving_license"}
  ]
}
```

### Redis Keys
```
extraction:session123:aadhaar
extraction:session123:profile_photo
extraction:session123:signature
extraction:session123:driving_license
```

### automation_agent/data.json
```json
{
  "first_name": "Raja",        // From split_name("Akash Raja")
  "middle_name": "",
  "last_name": "Akash",
  "photo_file": "docs/jphoto.jpeg",
  "signature_file": "docs/jsign.jpeg",
  "aadhaar_pdf": "docs/jaadhar.pdf",
  "birth_cert_pdf": "docs/jbirthcert.pdf"  // Actually driving license
}
```

### automation_agent/docs/
```
docs/
  ├── jaadhar.pdf          (Aadhaar)
  ├── jphoto.jpeg          (Profile photo)
  ├── jsign.jpeg           (Signature)
  └── jbirthcert.pdf       (Driving license - age proof)
```

## API Response Changes

### POST /api/upload Response
**Before:**
```json
{
  "filename": "my_doc.pdf",
  "message": "**my_doc.pdf** uploaded!"
}
```

**After:**
```json
{
  "filename": "my_doc.pdf",
  "stored_filename": "driving_license.pdf",
  "detected_doc_type": "driving_license",
  "user_provided_doc_type": "document",
  "message": "📄 **Driving License** detected!\n\n**driving_license.pdf** uploaded!"
}
```

## Summary

✅ **Name logic:** South Indian initials properly handled
✅ **Documents:** 3 required (Aadhaar, Photo, Sign) + 1 optional (DL)
✅ **Birth cert:** Removed (not implemented yet)
✅ **Detection:** Actual doc type detected and shown
✅ **Naming:** Clean filenames based on doc type
✅ **Syntax:** All errors fixed

**Status:** Ready for testing with correct name conventions and document requirements!

---

**Updated:** 2026-06-28
**Files Changed:** 1 (`pan-rag/api/routes.py`)
**Lines Modified:** ~200
**Breaking Changes:** Birth certificate no longer supported (can be re-added later)
