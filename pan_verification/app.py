from unittest import result
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import asyncio
import os
import tempfile
import json
import re
import time
from werkzeug.utils import secure_filename
from pathlib import Path
from dotenv import load_dotenv
from helpers import run_vlm, AADHAAR_PROMPT
from supa import get_or_create_person, save_document
from supabase import create_client
from re_check import validate_document, validate_aadhaar, validate_mobile, validate_dob, validate_gender
from image_quality import process_document

# Import ORCHESTRA functionality
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'ORCHESTRA', 'DocumentUploadAgent'))
try:
    import main as orchestra_main
    import extractor as orchestra_extractor
    import validator as orchestra_validator
    ORCHESTRA_AVAILABLE = True
    print("✅ ORCHESTRA integration loaded successfully")
except ImportError as e:
    ORCHESTRA_AVAILABLE = False
    print(f"⚠️ ORCHESTRA integration not available: {e}")

load_dotenv()

app = Flask(__name__, template_folder='templates')
CORS(app)

# Env check
NVIDIA_KEY = os.getenv('NVIDIA_META_90B')
if not NVIDIA_KEY:
    print("⚠️ Get NVIDIA_META_11B from https://build.nvidia.com -> NIM -> meta/llama-3.2-11b-vision-instruct")
    print("Add to .env and retry.")

@app.route('/fix-account')
def fix_account_page():
    """Serve the account fix page for users with foreign key constraint issues."""
    return render_template('fix_user_account.html')

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'status': 'error', 'error': 'Email and password required'}), 400
    
    url = "https://vnaeznlgijnarwqrwdtz.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZuYWV6bmxnaWpuYXJ3cXJ3ZHR6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY1Mjk4OTQsImV4cCI6MjA5MjEwNTg5NH0.kw8jhS-YErCJgDVkSDj6zBrJK3ytLnFS-2f0YR9D6hw"
    client = create_client(url, key)
    
    try:
        response = client.auth.sign_up({"email": email, "password": password})
        auth_id = response.user.id
        return jsonify({'status': 'success', 'auth_id': auth_id})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'status': 'error', 'error': 'Email and password required'}), 400
    
    url = "https://vnaeznlgijnarwqrwdtz.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZuYWV6bmxnaWpuYXJ3cXJ3ZHR6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY1Mjk4OTQsImV4cCI6MjA5MjEwNTg5NH0.kw8jhS-YErCJgDVkSDj6zBrJK3ytLnFS-2f0YR9D6hw"
    client = create_client(url, key)
    
    try:
        response = client.auth.sign_in_with_password({"email": email, "password": password})
        auth_id = response.user.id
        return jsonify({'status': 'success', 'auth_id': auth_id})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 400

@app.route('/api/get_docs', methods=['POST'])
def get_docs():
    data = request.get_json()
    auth_id = data.get('auth_id')
    
    if not auth_id:
        return jsonify({'status': 'error', 'error': 'auth_id required'}), 400
    
    from supa import get_documents_by_auth
    docs = get_documents_by_auth(auth_id)
    return jsonify({'status': 'success', 'documents': docs})


@app.route('/api/get_person_docs', methods=['POST'])
def get_person_docs():
    """Get documents for a specific person.

    Lookup can be done by:
    - person_name (legacy behavior; may contain name or mobile_number depending on UI)
    - phone_number (new; should be mobile_number)

    Backend uniqueness key is `mobile_number` in `persons`.
    """
    data = request.get_json() or {}
    auth_id = data.get('auth_id')
    person_name = data.get('person_name')
    phone_number = data.get('phone_number')

    if not auth_id:
        return jsonify({'status': 'error', 'error': 'auth_id required'}), 400

    if not person_name and not phone_number:
        return jsonify({'status': 'error', 'error': 'Provide name or phone_number'}), 400

    from supa import get_documents_by_name_or_phone

    docs = get_documents_by_name_or_phone(auth_id, person_name=person_name, phone_number=phone_number)
    return jsonify({'status': 'success', 'documents': docs})




@app.route('/api/update_document', methods=['POST'])
def update_document():
    """Update existing document or create new for a person.

    Lookup can be done by either:
    - person_name (legacy UI; treated as mobile_number previously in some places)
    - phone_number (new)

    If phone_number is provided, it will be used to identify/create the person.
    Otherwise, we fallback to extracting mobile_number from Aadhaar.
    """
    auth_id = request.form.get('auth_id')
    person_name = (request.form.get('person_name') or '').strip()
    phone_number = (request.form.get('phone_number') or '').strip()

    # Normalize phone_number to digits-only for DB lookup
    phone_number = ''.join(ch for ch in phone_number if ch.isdigit())


    if not auth_id:
        return jsonify({'status': 'error', 'error': 'auth_id required'}), 400
    if not person_name and not phone_number:
        return jsonify({'status': 'error', 'error': 'Provide person name or phone_number'}), 400

    if 'aadhaar' not in request.files:
        return jsonify({'status': 'error', 'error': 'No aadhaar file'}), 400


    aadhaar_file = request.files['aadhaar']
    filename = aadhaar_file.filename

    if filename == '':
        return jsonify({'status': 'error', 'error': 'No aadhaar file selected'}), 400

    ext = Path(filename).suffix[1:].lower()
    print(f"Update - Person: {person_name}, File: {filename}")

    try:
        file_bytes = aadhaar_file.read()
        
        # Process quality
        quality_result = process_document(file_bytes, filename)
        if quality_result["status"] == "error":
            return jsonify(quality_result), 400
        
        quality_score = quality_result["quality_score"]
        if quality_score < 0.6:
            return jsonify({
                'status': 'error',
                'quality_score': round(quality_score, 2),
                'message': f'Image quality too low (score: {round(quality_score, 2)}/1.0)'
            }), 400

        # Extract data
        result = run_vlm(AADHAAR_PROMPT, file_bytes, filename)
        
        # Get or create person
        from supa import get_or_create_person, delete_old_documents

        # If user provided phone_number, use it for lookup; otherwise use extracted mobile_number.
        mobile_number = phone_number or result.get("mobile_number")
        if not mobile_number:
            return jsonify({'status': 'error', 'error': 'phone_number/mobile_number not found'}), 400

        # Name can be provided by UI; fallback to extracted name (or existing person name).
        person_display_name = person_name or result.get("name")
        person_id = get_or_create_person(auth_id, mobile_number, person_display_name)

        # Delete old documents for this person
        delete_old_documents(person_id)

        
        # Save new document
        doc_id = save_document("aadhaar", result, auth_id, person_id)

        return jsonify({
            'status': 'success',
            'doc_id': doc_id,
            'message': f'Updated documents for {person_name}',
            'extracted': {
                'aadhar_number': result.get('aadhar_number', 'N/A'),
                'name': result.get('name', 'N/A')
            }
        })

    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500
from flask import request, jsonify
from pathlib import Path

@app.route('/api/verify', methods=['POST'])
def verify_documents():
    auth_id = request.form.get('auth_id')
    if not auth_id:
        return jsonify({'status': 'error', 'error': 'auth_id required. Signup first.'}), 400

    if 'aadhaar' not in request.files:
        return jsonify({'status': 'error', 'error': 'No aadhaar file'}), 400

    aadhaar_file = request.files['aadhaar']

    if aadhaar_file.filename == '':
        return jsonify({'status': 'error', 'error': 'No aadhaar file selected'}), 400

    filename = aadhaar_file.filename
    ext = Path(filename).suffix[1:].lower()

    print(f"Uploaded file: {filename} (ext: {ext})")

    try:
        # 🔥 READ FILE INTO MEMORY
        file_bytes = aadhaar_file.read()

        # 🔥 PROCESS QUALITY CHECK
        quality_result = process_document(file_bytes, filename)

        if quality_result["status"] == "error":
            return jsonify(quality_result), 400

        quality_score = quality_result["quality_score"]

        if quality_score < 0.6:
            return jsonify({
                'status': 'error',
                'quality_score': round(quality_score, 2),
                'message': f'Image quality too low (score: {round(quality_score, 2)}/1.0). Please upload a clearer image.',
                'quality_details': 'Improve lighting, focus, and resolution.'
            }), 400

        # 🔥 STEP 1: DETECT DOCUMENT TYPE FIRST
        from helpers import detect_document_type, validate_profile_photo
        
        print("🔍 Detecting document type...")
        doc_type_result = detect_document_type(file_bytes, filename)
        
        document_type = doc_type_result.get("document_type", "other_document")
        is_human_face = doc_type_result.get("is_human_face", False)
        
        print(f"📄 Detected document type: {document_type}")
        print(f"👤 Human face detected: {is_human_face}")

        # 🔥 STEP 2: HANDLE BASED ON DOCUMENT TYPE
        if document_type == "profile_photo":
            # For profile photos, only validate face quality - don't extract fields
            print("📸 Processing as profile photo - validating face quality...")
            
            photo_validation = validate_profile_photo(file_bytes, filename)
            
            return jsonify({
                'status': 'profile_photo_validated',
                'document_type': 'profile_photo',
                'photo_validation': photo_validation,
                'quality_score': round(quality_score, 2),
                'message': '📸 Profile photo processed - no field extraction needed',
                'is_suitable_for_pan': photo_validation.get('suitable_for_pan', False),
                'face_quality': photo_validation.get('face_quality', 'unknown')
            })
        
        elif document_type == "aadhaar_card":
            # For Aadhaar cards, proceed with field extraction
            print("🆔 Processing as Aadhaar card - extracting fields...")
            
            # 🔥 PASS IMAGE TO EXTRACTION MODEL
            result = run_vlm(AADHAAR_PROMPT, file_bytes, filename)
            print(f"📊 Raw extraction result: {json.dumps(result)}")

            # -----------------------------
            # VALIDATION
            # -----------------------------
            validation_input = {
                "aadhaar": result.get("aadhar_number", ""),
                "mobile": result.get("mobile_number", ""),
                "dob": result.get("dob", ""),
                "gender": result.get("gender", ""),
                "name": result.get("name", "")
            }

            validation_results = validate_document(validation_input)

            # -----------------------------
            # CHECK FOR MISSING REQUIRED FIELDS
            # -----------------------------
            required_fields = {
                "name": "Full Name",
                "father_name": "Father's Name", 
                "mobile_number": "Mobile Number",
                "dob": "Date of Birth",
                "gender": "Gender",
                "state": "State",
                "aadhar_number": "Aadhaar Number"
            }
            
            missing_fields = []
            extracted_fields = {}
            
            # Normalize result keys for robust lookup
            normalized_result = {str(k).lower().replace(' ', '').replace('_', ''): v for k, v in result.items()}
            
            for field_key, field_label in required_fields.items():
                # Try exact key first, then normalized key
                norm_key = field_key.lower().replace(' ', '').replace('_', '')
                value = result.get(field_key) or normalized_result.get(norm_key)
                
                # If still not found, try common variations for father_name
                if not value and field_key == "father_name":
                    value = result.get("Father Name") or result.get("father name") or result.get("Guardian Name") or result.get("guardian_name")
                
                # Aadhaar spelling variations (aadhar vs aadhaar)
                if not value and field_key == "aadhar_number":
                    value = result.get("aadhaar_number") or result.get("Aadhaar Number") or result.get("Aadhar Number")
                if not value or value in [None, "", "null", "N/A"]:
                    missing_fields.append({
                        "field": field_key,
                        "label": field_label,
                        "type": get_field_type(field_key),
                        "placeholder": get_field_placeholder(field_key),
                        "validation": get_field_validation(field_key)
                    })
                else:
                    extracted_fields[field_key] = value

            # -----------------------------
            # RETURN EXTRACTED DATA FOR USER VERIFICATION - DON'T AUTO-SAVE
            # -----------------------------
            status = 'missing_fields' if missing_fields else 'extracted_for_verification'
            
            return jsonify({
                'status': status,
                'document_type': 'aadhaar_card',
                'message': '📋 Data extracted successfully. Please review and confirm before saving.',
                'extracted_fields': extracted_fields,
                'missing_fields': missing_fields,
                'all_extracted_data': result,  # Complete raw extraction result
                'quality_score': round(quality_score, 2),
                'validation': validation_results,
                'doc_type_info': doc_type_result,
                'requires_user_confirmation': True,
                'next_step': 'Please review the extracted information, make any necessary corrections, and confirm to save.'
            })
        
        elif document_type in ["pan_card", "passport", "driving_license"]:
            # For other document types, return info but don't process yet
            return jsonify({
                'status': 'unsupported_document',
                'document_type': document_type,
                'message': f'Document type "{document_type}" detected but processing not implemented yet',
                'quality_score': round(quality_score, 2),
                'doc_type_info': doc_type_result,
                'suggestion': 'Please upload an Aadhaar card for field extraction or a profile photo for photo validation'
            }), 400
        
        else:
            # Unknown or unsupported document type
            return jsonify({
                'status': 'unknown_document',
                'document_type': document_type,
                'message': 'Could not identify document type. Please upload a clear Aadhaar card or profile photo.',
                'quality_score': round(quality_score, 2),
                'doc_type_info': doc_type_result,
                'is_human_face': is_human_face
            }), 400

    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

def get_field_type(field_key):
    """Return the HTML input type for each field."""
    field_types = {
        "name": "text",
        "father_name": "text", 
        "mobile_number": "tel",
        "dob": "date",
        "gender": "select",
        "state": "select",
        "aadhar_number": "text"
    }
    return field_types.get(field_key, "text")

def get_field_placeholder(field_key):
    """Return placeholder text for each field."""
    placeholders = {
        "name": "Enter full name as in Aadhaar",
        "father_name": "Enter father's full name",
        "mobile_number": "Enter 10-digit mobile number",
        "dob": "Select date of birth",
        "gender": "Select gender",
        "state": "Select state",
        "aadhar_number": "Enter 12-digit Aadhaar number"
    }
    return placeholders.get(field_key, f"Enter {field_key.replace('_', ' ')}")

def get_field_validation(field_key):
    """Return validation rules for each field."""
    validations = {
        "mobile_number": {"pattern": "^[6-9][0-9]{9}$", "message": "Enter valid 10-digit mobile number"},
        "aadhar_number": {"pattern": "^([0-9]{4}[ -]?[0-9]{4}[ -]?[0-9]{4}|[Xx*]{4}[ -]?[Xx*]{4}[ -]?[0-9]{4})$", "message": "Enter valid 12-digit Aadhaar number"},
        "dob": {"max": "2010-12-31", "message": "Date of birth should be before 2011"},
        "gender": {"options": ["Male", "Female", "Other"]},
        "state": {"options": ["Andhra Pradesh", "Assam", "Bihar", "Chhattisgarh", "Delhi", "Gujarat", 
                             "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
                             "Maharashtra", "Odisha", "Punjab", "Rajasthan", "Tamil Nadu", "Telangana", 
                             "Uttar Pradesh", "West Bengal", "Other"]}
    }
    return validations.get(field_key, {})


@app.route('/api/preview', methods=['POST'])
def preview_document():
    """Extract data but don't save - for user verification. Now with document type detection."""
    auth_id = request.form.get('auth_id')
    if not auth_id:
        return jsonify({'status': 'error', 'error': 'auth_id required'}), 400

    if 'aadhaar' not in request.files:
        return jsonify({'status': 'error', 'error': 'No aadhaar file'}), 400

    aadhaar_file = request.files['aadhaar']
    filename = aadhaar_file.filename

    if filename == '':
        return jsonify({'status': 'error', 'error': 'No file selected'}), 400

    try:
        file_bytes = aadhaar_file.read()
        
        # Quality check
        quality_result = process_document(file_bytes, filename)
        if quality_result["status"] == "error":
            return jsonify(quality_result), 400
        
        quality_score = quality_result["quality_score"]
        if quality_score < 0.6:
            return jsonify({
                'status': 'error',
                'quality_score': round(quality_score, 2),
                'message': f'Image quality too low (score: {round(quality_score, 2)}/1.0)'
            }), 400

        # 🔥 STEP 1: DETECT DOCUMENT TYPE
        from helpers import detect_document_type, validate_profile_photo
        
        doc_type_result = detect_document_type(file_bytes, filename)
        document_type = doc_type_result.get("document_type", "other_document")
        
        if document_type == "profile_photo":
            # For profile photos, validate face quality
            photo_validation = validate_profile_photo(file_bytes, filename)
            
            return jsonify({
                'status': 'success',
                'document_type': 'profile_photo',
                'photo_validation': photo_validation,
                'quality_score': round(quality_score, 2),
                'doc_type_info': doc_type_result
            })
        
        elif document_type == "aadhaar_card":
            # For Aadhaar, extract data
            result = run_vlm(AADHAAR_PROMPT, file_bytes, filename)
            
            return jsonify({
                'status': 'success',
                'document_type': 'aadhaar_card',
                'extracted_data': result,
                'quality_score': round(quality_score, 2),
                'doc_type_info': doc_type_result
            })
        
        else:
            # Other document types
            return jsonify({
                'status': 'unsupported_document',
                'document_type': document_type,
                'message': f'Document type "{document_type}" detected but processing not implemented',
                'quality_score': round(quality_score, 2),
                'doc_type_info': doc_type_result
            })

    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/api/validate_photo', methods=['POST'])
def validate_photo():
    """Dedicated endpoint for profile photo validation."""
    auth_id = request.form.get('auth_id')
    if not auth_id:
        return jsonify({'status': 'error', 'error': 'auth_id required'}), 400

    if 'photo' not in request.files:
        return jsonify({'status': 'error', 'error': 'No photo file'}), 400

    photo_file = request.files['photo']
    filename = photo_file.filename

    if filename == '':
        return jsonify({'status': 'error', 'error': 'No photo file selected'}), 400

    try:
        file_bytes = photo_file.read()
        
        # Quality check
        quality_result = process_document(file_bytes, filename)
        if quality_result["status"] == "error":
            return jsonify(quality_result), 400
        
        quality_score = quality_result["quality_score"]
        
        # Validate as profile photo
        from helpers import validate_profile_photo
        photo_validation = validate_profile_photo(file_bytes, filename)
        
        return jsonify({
            'status': 'success',
            'document_type': 'profile_photo',
            'photo_validation': photo_validation,
            'quality_score': round(quality_score, 2),
            'is_suitable_for_pan': photo_validation.get('suitable_for_pan', False),
            'face_quality': photo_validation.get('face_quality', 'unknown'),
            'issues': photo_validation.get('issues', []),
            'message': 'Profile photo validated successfully'
        })

    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/api/confirm_save', methods=['POST'])
def confirm_save():
    """Save document after user verification, corrections, and final confirmation."""
    
    # Handle both form data and JSON data
    if request.content_type and 'application/json' in request.content_type:
        data = request.get_json() or {}
        auth_id = data.get('auth_id')
        extracted_fields = data.get('extracted_fields', {})
        user_fields = data.get('user_fields', {})
    else:
        # Handle form data (legacy)
        auth_id = request.form.get('auth_id')
        extracted_fields = {}
        user_fields = {}
        
        # Get the user-confirmed/corrected data from form
        if request.form.get('confirmed_data'):
            user_fields = json.loads(request.form.get('confirmed_data'))
        else:
            # Get individual field values from form
            field_names = [
                'name', 'first_name', 'last_name', 'middle_name',
                'father_name', 'father_first_name', 'father_last_name', 'father_middle_name',
                'mobile_number', 'aadhar_number', 'dob', 'gender', 'state', 'city'
            ]
            
            for field in field_names:
                value = request.form.get(field)
                if value and value.strip():
                    user_fields[field] = value.strip()

    if not auth_id:
        return jsonify({'status': 'error', 'error': 'auth_id required'}), 400

    try:
        # Merge extracted fields with user corrections (user input takes priority)
        confirmed_data = {**extracted_fields, **user_fields}
        
        # Validate required fields are present
        required_fields = ["name", "father_name", "mobile_number", "dob", "gender", "state", "aadhar_number"]
        missing_required = []
        
        for field in required_fields:
            if not confirmed_data.get(field) or confirmed_data[field] in [None, "", "null", "N/A"]:
                missing_required.append(field.replace('_', ' ').title())
        
        if missing_required:
            return jsonify({
                'status': 'error',
                'error': f'Required fields missing: {", ".join(missing_required)}',
                'missing_fields': missing_required
            }), 400

        # Validate field formats
        validation_errors = []
        
        # Mobile number validation
        mobile = confirmed_data.get('mobile_number', '').replace(' ', '').replace('-', '')
        if not re.match(r'^[6-9][0-9]{9}$', mobile):
            validation_errors.append('Mobile number must be 10 digits starting with 6-9')
        
        # Aadhaar number validation
        aadhaar = confirmed_data.get('aadhar_number', '').replace(' ', '').replace('-', '')
        if not re.match(r'^([0-9]{12}|[Xx*]{8}[0-9]{4})$', aadhaar):
            validation_errors.append('Aadhaar number must be 12 digits')
        
        # Date validation (accept multiple formats)
        dob = confirmed_data.get('dob', '')
        if dob and not (re.match(r'^[\d]{1,2}/[\d]{1,2}/[\d]{4}$', dob) or re.match(r'^[\d]{4}-[\d]{1,2}-[\d]{1,2}$', dob)):
            validation_errors.append('Date of birth must be in DD/MM/YYYY or YYYY-MM-DD format')
        
        if validation_errors:
            return jsonify({
                'status': 'error',
                'error': 'Data validation failed',
                'validation_errors': validation_errors,
                'message': 'Please correct the highlighted fields and try again'
            }), 400

        # Clean and format the data
        confirmed_data['mobile_number'] = mobile
        confirmed_data['aadhar_number'] = aadhaar
        
        # Add metadata
        confirmed_data['user_verified'] = True
        confirmed_data['verification_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
        confirmed_data['confidence'] = 'user_verified'  # Override extraction confidence
        
        # Save to database
        from supa import get_or_create_person
        
        person_name = confirmed_data.get("name")
        mobile_number = confirmed_data.get("mobile_number")
        
        # Create or get person using mobile number as unique key
        person_id = get_or_create_person(auth_id, mobile_number, person_name)
        
        # Delete any existing documents for this person to avoid duplicates
        from supa import delete_old_documents
        delete_old_documents(person_id)
        
        # Save the user-confirmed document
        doc_id = save_document("aadhaar", confirmed_data, auth_id, person_id)
        
        return jsonify({
            'status': 'success',
            'doc_id': doc_id,
            'auth_id': auth_id,
            'person_id': person_id,
            'message': '✅ Document verified and saved successfully',
            'saved_data': {
                'name': confirmed_data.get('name'),
                'father_name': confirmed_data.get('father_name'),
                'aadhar_number': confirmed_data.get('aadhar_number'),
                'mobile_number': confirmed_data.get('mobile_number'),
                'dob': confirmed_data.get('dob'),
                'gender': confirmed_data.get('gender'),
                'state': confirmed_data.get('state')
            },
            'verification_status': 'user_confirmed',
            'next_steps': [
                'Document has been saved to your profile',
                'You can now proceed with your PAN application',
                'Use the saved information for form auto-fill'
            ]
        })
        
    except json.JSONDecodeError:
        return jsonify({'status': 'error', 'error': 'Invalid JSON data format'}), 400
    except Exception as e:
        error_message = str(e)
        
        # Check if it's the foreign key constraint error
        if "User account setup incomplete" in error_message:
            # Extract the SQL command from the error for the user
            sql_command = f"INSERT INTO users (id, email) VALUES ('{auth_id}', 'user-{auth_id[:8]}@temp.local') ON CONFLICT DO NOTHING;"
            
            return jsonify({
                'status': 'error',
                'error_type': 'user_account_setup',
                'error': 'Database setup required to save documents.',
                'message': '🔧 Your account needs a database record to save documents.',
                'fix_url': f'/fix-account?auth_id={auth_id}',
                'instructions': {
                    'title': 'Quick Fix Required',
                    'steps': [
                        '1. Open your Supabase Dashboard',
                        '2. Go to SQL Editor', 
                        '3. Run the provided SQL command',
                        '4. Return here and try uploading again'
                    ],
                    'sql_command': sql_command,
                    'alternative': 'Contact your administrator to run the SQL command for you'
                },
                'support_info': {
                    'error_code': f"FK-{auth_id[:8] if auth_id else 'unknown'}",
                    'description': 'Missing user record in database',
                    'fix_type': 'One-time SQL command execution required'
                },
                'user_friendly': True
            }), 500
        elif "foreign key constraint" in error_message.lower():
            return jsonify({
                'status': 'error', 
                'error_type': 'database_constraint',
                'error': 'Database constraint error. Please contact support.',
                'message': '⚠️ There is a database configuration issue preventing document saves.',
                'support_info': {
                    'error_code': f"FK-{auth_id[:8] if auth_id else 'unknown'}",
                    'description': 'Foreign key constraint violation',
                    'technical_details': error_message
                }
            }), 500
        else:
            return jsonify({'status': 'error', 'error': error_message}), 500

@app.route('/api/complete_missing_fields', methods=['POST'])
def complete_missing_fields():
    """Complete document verification with user-provided missing fields."""
    auth_id = request.form.get('auth_id')
    if not auth_id:
        return jsonify({'status': 'error', 'error': 'auth_id required'}), 400
    
    # Get extracted fields (as JSON string)
    extracted_fields_json = request.form.get('extracted_fields')
    if not extracted_fields_json:
        return jsonify({'status': 'error', 'error': 'extracted_fields required'}), 400
    
    try:
        extracted_fields = json.loads(extracted_fields_json)
    except json.JSONDecodeError:
        return jsonify({'status': 'error', 'error': 'Invalid extracted_fields JSON'}), 400
    
    # Get user-provided fields for missing data
    user_provided_fields = {}
    for key in ['name', 'father_name', 'mobile_number', 'dob', 'gender', 'state', 'aadhar_number']:
        value = request.form.get(key)
        if value and value.strip():
            user_provided_fields[key] = value.strip()
    
    # Merge extracted and user-provided fields (user input takes priority)
    complete_data = {**extracted_fields, **user_provided_fields}
    
    # Validate that all required fields are now present
    required_fields = ["name", "father_name", "mobile_number", "dob", "gender", "state", "aadhar_number"]
    still_missing = []
    
    for field in required_fields:
        if not complete_data.get(field) or complete_data[field] in [None, "", "null", "N/A"]:
            still_missing.append(field)
    
    if still_missing:
        return jsonify({
            'status': 'error',
            'error': f'Still missing required fields: {", ".join(still_missing)}'
        }), 400
    
    # Validate field formats
    validation_errors = []
    
    # Mobile number validation
    mobile = str(complete_data.get('mobile_number', '')).replace(' ', '').replace('-', '')
    if not re.match(r'^[6-9][0-9]{9}$', mobile):
        validation_errors.append('Mobile number must be a valid 10-digit number starting with 6-9')
    
    # Aadhaar number validation
    aadhaar = str(complete_data.get('aadhar_number', '')).replace(' ', '').replace('-', '')
    if not re.match(r'^([0-9]{12}|[Xx*]{8}[0-9]{4})$', aadhaar):
        validation_errors.append('Aadhaar number must be a valid 12-digit number')
    
    if validation_errors:
        return jsonify({
            'status': 'error',
            'error': 'Validation failed',
            'validation_errors': validation_errors
        }), 400
    
    try:
        # Save the complete document
        from supa import get_or_create_person
        
        person_name = complete_data.get("name")
        mobile_number = complete_data.get("mobile_number")
        
        # Create or get person
        person_id = get_or_create_person(auth_id, mobile_number, person_name)
        
        # Save complete document
        doc_id = save_document("aadhaar", complete_data, auth_id, person_id)
        
        return jsonify({
            'status': 'success',
            'doc_id': doc_id,
            'auth_id': auth_id,
            'aadhaar_data': complete_data,
            'message': '✅ Document completed and saved successfully',
            'completed_fields': list(user_provided_fields.keys()),
            'extracted': {
                'aadhar_number': complete_data.get('aadhar_number', 'N/A'),
                'name': complete_data.get('name', 'N/A'),
                'father_name': complete_data.get('father_name', 'N/A'),
                'state': complete_data.get('state', 'N/A'),
                'mobile_number': complete_data.get('mobile_number', 'N/A')
            }
        })
    except Exception as e:
        import traceback
        print(f"❌ Error in complete_missing_fields: {str(e)}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/api/multi_documents/verify', methods=['POST'])
def verify_multiple_documents():
    """ORCHESTRA: Process multiple documents simultaneously with cross-validation."""
    if not ORCHESTRA_AVAILABLE:
        return jsonify({
            'status': 'error',
            'error': 'Multi-document processing not available. ORCHESTRA module not loaded.'
        }), 503

    auth_id = request.form.get('auth_id')
    if not auth_id:
        return jsonify({'status': 'error', 'error': 'auth_id required'}), 400

    # Get uploaded files
    uploaded_files = {}
    temp_paths = {}
    
    # Supported document types
    doc_types = ['aadhaar', 'ration_card', 'address_proof', 'caste_certificate', 'pan_card']
    
    try:
        # Save uploaded files to temporary locations
        for doc_type in doc_types:
            if doc_type in request.files:
                file = request.files[doc_type]
                if file and file.filename:
                    # Create temp file
                    temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
                    os.close(temp_fd)
                    file.save(temp_path)
                    temp_paths[doc_type] = temp_path
                    uploaded_files[doc_type] = file.filename
                    print(f"📄 Saved {doc_type}: {file.filename} -> {temp_path}")

        if not temp_paths:
            return jsonify({
                'status': 'error', 
                'error': 'No valid documents uploaded. Please upload at least one document.'
            }), 400

        print(f"🔄 Processing {len(temp_paths)} documents with ORCHESTRA...")

        # Process with ORCHESTRA
        result = orchestra_main.process_documents(
            aadhaar_pdf=temp_paths.get('aadhaar'),
            ration_pdf=temp_paths.get('ration_card'),
            address_pdf=temp_paths.get('address_proof'),
            caste_pdf=temp_paths.get('caste_certificate')
        )

        print(f"📊 ORCHESTRA processing complete. Confidence: {result.get('confidence_score', 0)}")

        # Format response
        response = {
            'status': 'multi_documents_processed',
            'message': 'Multiple documents processed successfully with ORCHESTRA',
            'documents_processed': list(uploaded_files.keys()),
            'documents_count': len(uploaded_files),
            
            # ORCHESTRA results
            'combined_data': result.get('combined', {}),
            'individual_extractions': {
                'aadhaar': result.get('aadhaar_data', {}),
                'ration_card': result.get('ration_data', {}),
                'address_proof': result.get('address_data', {}),
                'caste_certificate': result.get('caste_data', {})
            },
            'validation': result.get('validation', {}),
            'confidence_score': result.get('confidence_score', 0),
            
            # For frontend compatibility
            'extracted_fields': result.get('combined', {}),
            'quality_score': result.get('confidence_score', 0),
            'document_type': 'multi_document_set',
            'requires_user_confirmation': True,
            'auth_id': auth_id
        }

        return jsonify(response)

    except Exception as e:
        error_msg = str(e)
        print(f"❌ ORCHESTRA processing error: {error_msg}")
        return jsonify({
            'status': 'error',
            'error': f'Multi-document processing failed: {error_msg}',
            'uploaded_files': list(uploaded_files.keys())
        }), 500

    finally:
        # Clean up temporary files
        for temp_path in temp_paths.values():
            try:
                os.unlink(temp_path)
            except:
                pass

@app.route('/api/multi_documents/confirm', methods=['POST'])
def confirm_multiple_documents():
    """ORCHESTRA: Save validated multi-document data."""
    if not ORCHESTRA_AVAILABLE:
        return jsonify({'status': 'error', 'error': 'ORCHESTRA not available'}), 503

    data = request.get_json()
    auth_id = data.get('auth_id')
    combined_data = data.get('combined_data', {})
    user_corrections = data.get('user_corrections', {})

    if not auth_id:
        return jsonify({'status': 'error', 'error': 'auth_id required'}), 400

    try:
        # Merge combined data with user corrections
        final_data = {**combined_data, **user_corrections}
        
        # Use mobile number or phone as unique identifier
        mobile_number = (final_data.get('phone_number') or 
                        final_data.get('mobile_number') or 
                        final_data.get('phone'))
        
        if not mobile_number:
            return jsonify({
                'status': 'error', 
                'error': 'No phone number found in extracted data'
            }), 400

        # Get person name
        person_name = (final_data.get('username') or 
                      final_data.get('name') or 
                      'Multi-Document User')

        # Create or get person
        person_id = get_or_create_person(auth_id, mobile_number, person_name)

        # Save as multi-document record
        final_data['document_type'] = 'multi_document_orchestra'
        final_data['processing_method'] = 'ORCHESTRA'
        final_data['user_verified'] = True
        final_data['verification_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
        
        doc_id = save_document("multi_document", final_data, auth_id, person_id)

        return jsonify({
            'status': 'success',
            'doc_id': doc_id,
            'person_id': person_id,
            'message': 'Multi-document data saved successfully',
            'saved_fields': len(final_data),
            'processing_method': 'ORCHESTRA'
        })

    except Exception as e:
        return jsonify({
            'status': 'error', 
            'error': f'Failed to save multi-document data: {str(e)}'
        }), 500


if __name__ == '__main__':
    print("🚀 PAN Verifier ready: http://localhost:5000")
    print("📁 Test with aadhar_card.jpeg")
    app.run(debug=True, port=5000, host='0.0.0.0')

