# PAN/Aadhaar Document Verifier 🚀

## Quick Start (Windows)

1. **Setup Environment**
```bash
cd c:/pan_verification
myenv\\Scripts\\activate
pip install -r req.txt
```

2. **API Keys** (Required for cloud AI)
```
cp .env.example .env
# Edit .env with your GEMINI_API_KEY from https://aistudio.google.com/app/apikey
```

3. **Flask Web App**
```bash
python app.py
# Open http://localhost:5000
```

4. **CLI Verification**
```bash
python "pan_verification (1).py" aadhar_card.jpeg PHOTO.jpg signature.jpeg
```

## Features
- ✅ Aadhaar OCR: Number, Name (split), Father details, Mobile, State/City, Gender/DOB
- ✅ Photo validation: Face detection, specs check
- ✅ Signature verification: Handwritten, clear
- 🔄 Gemini AI (free) + NVIDIA NIM fallback
- 📱 Web UI + CLI
- 🔒 Technical checks: Blur, brightness, size

## Local Ollama Alternative
```bash
# Install Ollama + llava model
ollama pull llava:7b
# Set LOCAL_VLM=ollama in .env
```

## Files
- `app.py` - Flask server
- `helpers.py` - VLM engine (Gemini primary)
- `pan_verification*.py` - CLI pipelines
- `templates/index.html` - Upload UI

**Test with provided JPEGs!**

