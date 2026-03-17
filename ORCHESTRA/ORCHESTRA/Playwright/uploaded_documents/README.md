# Uploaded Documents Storage

This folder stores all documents uploaded through the frontend for use during automation.

## Purpose
- All documents uploaded by users in the frontend are automatically saved here
- The Playwright automation script reads files from this location
- Files are stored with absolute paths to ensure reliable access during automation

## Files Stored Here
- **Photo**: User's photograph (JPEG/PNG format)
- **Aadhaar Card**: Identity proof document
- **Ration Card**: Additional identity/address proof
- **Driving License**: Address proof document (converted to image if PDF)
- **Signed Self-Declaration**: User-signed self-declaration form

## Automation Flow
1. User uploads documents in frontend
2. DocumentUploadAgent saves files to this folder
3. Playwright automation reads files from here during portal submission
4. All file paths are absolute to prevent access issues

## Notes
- Files are automatically converted to image format if needed (PDF → JPEG)
- This folder is created automatically if it doesn't exist
- Old files are overwritten when new documents are uploaded with the same name
