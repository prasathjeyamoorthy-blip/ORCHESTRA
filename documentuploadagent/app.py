from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import os
import tempfile
import json
from pathlib import Path
from dotenv import load_dotenv

from helpers import run_vlm, AADHAAR_PROMPT
from pan_verification_upd import (
    AadhaarData, PhotoData,
    AADHAAR_PROMPT as VERIFY_AADHAAR_PROMPT,
    PHOTO_PROMPT,
    basic_file_check,
    image_quality_check,
    validate_aadhaar_fields,
    validate_photo_fields,
)

load_dotenv()

app = Flask(__name__)
CORS(app)

NVIDIA_KEY = os.getenv('NVIDIA_META_11B')
if not NVIDIA_KEY:
    print("⚠️  Set NVIDIA_META_11B in .env — get it from https://build.nvidia.com")


# ── helpers ──────────────────────────────────────────────────

def save_upload(file_obj) -> tuple[str, str]:
    """Save uploaded file to a temp path, return (tmp_path, ext)."""
    ext = Path(file_obj.filename).suffix.lower() or '.jpg'
    fd, tmp_path = tempfile.mkstemp(suffix=ext)
    os.close(fd)
    file_obj.save(tmp_path)
    return tmp_path, ext


def cleanup(path: str):
    try:
        if path and os.path.exists(path):
            os.unlink(path)
    except Exception:
        pass


# ── /api/upload ───────────────────────────────────────────────

@app.route('/api/upload', methods=['POST'])
def upload_document():
    """
    Accepts multipart/form-data:
      - file      : the document file
      - doc_type  : 'aadhaar' | 'driving_license' | 'photograph'
      - session_id: (optional) session identifier
    Returns JSON with extracted data + validation results.
    """
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'error': 'No file provided'}), 400

    doc_type = request.form.get('doc_type', '').lower()
    session_id = request.form.get('session_id', 'anonymous')
    file_obj = request.files['file']

    if file_obj.filename == '':
        return jsonify({'status': 'error', 'error': 'Empty filename'}), 400

    tmp_path = None
    try:
        tmp_path, _ = save_upload(file_obj)

        # ── Technical checks ──
        ok, msg = basic_file_check(tmp_path, doc_type.capitalize())
        if not ok:
            return jsonify({'status': 'error', 'error': msg}), 422

        ok, msg = image_quality_check(tmp_path, doc_type.capitalize())
        if not ok:
            return jsonify({'status': 'error', 'error': msg}), 422

        # ── Route by doc_type ──
        if doc_type == 'aadhaar':
            return _handle_aadhaar(tmp_path, session_id)

        elif doc_type == 'photograph':
            return _handle_photo(tmp_path, session_id)

        elif doc_type == 'driving_license':
            return _handle_driving_license(tmp_path, session_id)

        else:
            return jsonify({'status': 'error', 'error': f'Unknown doc_type: {doc_type}'}), 400

    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500
    finally:
        cleanup(tmp_path)


# ── per-document handlers ─────────────────────────────────────

def _handle_aadhaar(tmp_path: str, session_id: str):
    raw = run_vlm(VERIFY_AADHAAR_PROMPT, tmp_path)
    data = AadhaarData(**raw)
    errors = validate_aadhaar_fields(data)

    extracted = data.model_dump()
    return jsonify({
        'status': 'success' if not errors else 'partial',
        'doc_type': 'aadhaar',
        'session_id': session_id,
        'extracted': extracted,
        'validation_errors': errors,
        'verified': len(errors) == 0,
        'message': (
            '✅ Aadhaar extracted and verified successfully'
            if not errors
            else f'⚠️ Aadhaar extracted with {len(errors)} issue(s)'
        ),
        'summary': {
            'aadhaar_number': data.aadhaar_number,
            'name': data.name,
            'dob': data.dob,
            'gender': data.gender,
            'state': data.state,
            'confidence': data.confidence,
        }
    })


def _handle_photo(tmp_path: str, session_id: str):
    raw = run_vlm(PHOTO_PROMPT, tmp_path)
    data = PhotoData(**raw)
    errors = validate_photo_fields(data)

    return jsonify({
        'status': 'success' if not errors else 'partial',
        'doc_type': 'photograph',
        'session_id': session_id,
        'extracted': data.model_dump(),
        'validation_errors': errors,
        'verified': len(errors) == 0,
        'message': (
            '✅ Photograph verified successfully'
            if not errors
            else f'⚠️ Photograph has {len(errors)} issue(s)'
        ),
        'summary': {
            'has_face': data.has_face,
            'face_centered': data.face_centered,
            'plain_background': data.plain_background,
            'confidence': data.confidence,
        }
    })


def _handle_driving_license(tmp_path: str, session_id: str):
    DL_PROMPT = """
Extract these fields from this Indian Driving License image as JSON:
{
  "document_type": "driving_license" or "unknown",
  "is_legible": true or false,
  "dl_number": "DL number as printed",
  "name": "Full name",
  "dob": "DD/MM/YYYY or null",
  "validity": "validity date or null",
  "state": "issuing state",
  "address": "address if visible or null",
  "confidence": "high/medium/low",
  "issues": []
}
Return ONLY raw JSON. Null for missing fields.
"""
    raw = run_vlm(DL_PROMPT, tmp_path)
    errors = []
    if not raw.get('name'):
        errors.append('Could not extract name from Driving License')
    if raw.get('document_type', '').lower() != 'driving_license':
        errors.append(f"Document does not appear to be a Driving License (detected: {raw.get('document_type')})")

    return jsonify({
        'status': 'success' if not errors else 'partial',
        'doc_type': 'driving_license',
        'session_id': session_id,
        'extracted': raw,
        'validation_errors': errors,
        'verified': len(errors) == 0,
        'message': (
            '✅ Driving License extracted successfully'
            if not errors
            else f'⚠️ Driving License extracted with {len(errors)} issue(s)'
        ),
        'summary': {
            'dl_number': raw.get('dl_number'),
            'name': raw.get('name'),
            'dob': raw.get('dob'),
            'state': raw.get('state'),
            'confidence': raw.get('confidence'),
        }
    })


# ── legacy /api/verify (kept for compatibility) ───────────────

@app.route('/api/verify', methods=['POST'])
def verify_documents():
    if 'aadhaar' not in request.files:
        return jsonify({'status': 'error', 'error': 'No aadhaar file'}), 400
    file_obj = request.files['aadhaar']
    tmp_path = None
    try:
        tmp_path, _ = save_upload(file_obj)
        result = run_vlm(AADHAAR_PROMPT, tmp_path)
        return jsonify({'status': 'success', 'aadhaar_data': result})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500
    finally:
        cleanup(tmp_path)


if __name__ == '__main__':
    print("🚀 Document Upload Agent ready: http://localhost:5001")
    app.run(debug=True, port=5001, host='0.0.0.0')
