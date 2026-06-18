from unittest import result
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import asyncio
import os
import tempfile
import json
from werkzeug.utils import secure_filename
from pathlib import Path
from dotenv import load_dotenv
from helpers import run_vlm, AADHAAR_PROMPT
from supa import get_or_create_person, save_document
from supabase import create_client
from re_check import validate_document
from image_quality import process_document

load_dotenv()

app = Flask(__name__, template_folder='templates')
CORS(app)

# Env check
NVIDIA_KEY = os.getenv('NVIDIA_META_90B')
if not NVIDIA_KEY:
    print("⚠️ Get NVIDIA_META_11B from https://build.nvidia.com -> NIM -> meta/llama-3.2-11b-vision-instruct")
    print("Add to .env and retry.")

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

    Backend uniqueness key is `mobile_number`.

    UI may still send the field as `person_name`.
    If so, we treat it as a mobile number for lookup.
    """
    data = request.get_json()
    auth_id = data.get('auth_id')
    person_name = data.get('person_name')

    if not auth_id:
        return jsonify({'status': 'error', 'error': 'auth_id required'}), 400
    if not person_name:
        return jsonify({'status': 'error', 'error': 'person_name (mobile_number) required'}), 400

    from supa import get_documents_by_person

    # `get_documents_by_person` expects a name for backward compatibility.
    # We updated it to use mobile_number as unique key.
    docs = get_documents_by_person(auth_id, person_name)
    return jsonify({'status': 'success', 'documents': docs})



@app.route('/api/update_document', methods=['POST'])
def update_document():
    """Update existing document or create new for a person."""
    auth_id = request.form.get('auth_id')
    person_name = request.form.get('person_name')
    
    if not auth_id:
        return jsonify({'status': 'error', 'error': 'auth_id required'}), 400
    if not person_name:
        return jsonify({'status': 'error', 'error': 'person_name required'}), 400

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
        
        # Get or create person using mobile_number (unique key)
        from supa import get_or_create_person, delete_old_documents
        mobile_number = result.get("mobile_number")
        if not mobile_number:
            return jsonify({'status': 'error', 'error': 'mobile_number not found in Aadhaar extraction'}), 400
        person_id = get_or_create_person(auth_id, mobile_number, person_name)

        
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

    print(f"Uploaded Aadhaar: {filename} (ext: {ext})")

    try:
        # 🔥 READ FILE INTO MEMORY
        file_bytes = aadhaar_file.read()

        # 🔥 PROCESS (NO TEMP FILE)
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

        # 🔥 PASS IMAGE TO YOUR MODEL (modify run_vlm to accept bytes if needed)
        result = run_vlm(AADHAAR_PROMPT, file_bytes,filename)

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
        # SAVE
        # -----------------------------
        from supa import get_or_create_person

        person_name = result.get("name", "Unknown")
        mobile_number = result.get("mobile_number")
        if not mobile_number:
            return jsonify({'status': 'error', 'error': 'mobile_number not found in Aadhaar extraction'}), 400

        # 🔥 Get or create person (mobile_number is unique key)
        person_id = get_or_create_person(auth_id, mobile_number, person_name)

        # 🔥 Save document linked to person
        doc_id = save_document("aadhaar", result, auth_id, person_id)


        return jsonify({
            'status': 'success',
            'doc_id': doc_id,
            'auth_id': auth_id,
            'aadhaar_data': result,
            'quality_score': round(quality_score, 2),
            'validation': validation_results,
            'message': '✅ Aadhaar extracted and saved successfully',
            'extracted': {
                'aadhar_number': result.get('aadhar_number', 'N/A'),
                'name': result.get('name', 'N/A'),
                'father_name': result.get('father_name', 'N/A'),
                'state': result.get('state', 'N/A'),
                'confidence': result.get('confidence', 'N/A')
            }
        })

    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/api/preview', methods=['POST'])
def preview_document():
    """Extract data but don't save - for user verification."""
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

        # Extract data
        result = run_vlm(AADHAAR_PROMPT, file_bytes, filename)

        return jsonify({
            'status': 'success',
            'extracted_data': result,
            'quality_score': round(quality_score, 2)
        })

    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/api/confirm_save', methods=['POST'])
def confirm_save():
    """Save document after user verification and edits."""
    auth_id = request.form.get('auth_id')
    person_name = request.form.get('person_name')
    extracted_data = request.form.get('extracted_data')
    
    if not auth_id:
        return jsonify({'status': 'error', 'error': 'auth_id required'}), 400
    if not person_name:
        return jsonify({'status': 'error', 'error': 'person_name required'}), 400
    if not extracted_data:
        return jsonify({'status': 'error', 'error': 'extracted_data required'}), 400

    try:
        # Parse the extracted data (sent as JSON string)
        result = json.loads(extracted_data)
        
        # Get or create person (mobile_number is unique key)
        from supa import get_or_create_person
        mobile_number = result.get("mobile_number")
        if not mobile_number:
            return jsonify({'status': 'error', 'error': 'mobile_number not found in extracted_data'}), 400

        person_id = get_or_create_person(auth_id, mobile_number, person_name)

        
        # Save document
        doc_id = save_document("aadhaar", result, auth_id, person_id)

        return jsonify({
            'status': 'success',
            'doc_id': doc_id,
            'message': '✅ Document saved successfully'
        })

    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 PAN Verifier ready: http://localhost:5000")
    print("📁 Test with aadhar_card.jpeg")
    app.run(debug=True, port=5000, host='0.0.0.0')

