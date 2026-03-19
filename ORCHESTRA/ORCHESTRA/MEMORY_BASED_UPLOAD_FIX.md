# Memory-Based File Upload Fix

## Problem
The "Add..." button was triggering the Windows file browser dialog, requiring manual file selection from local storage. This interrupted the automation flow.

## Solution
Modified the file upload logic to load files into memory BEFORE clicking the "Add..." button, preventing the file browser dialog from appearing.

## Implementation Details

### New Upload Flow

#### 1. Photo Upload
```
1. Select "Photo" from dropdown
2. Find hidden file input element
3. Set file directly using set_input_files() - loads into browser memory
4. Click "Add..." button - no dialog appears, file already loaded
5. Clean up temporary converted files from RAM
```

#### 2. Self-Declaration Upload
```
1. Download blank form from portal
2. Wait for user to sign and re-upload
3. Select "Self-Declaration of Applicant" from dropdown
4. Set signed file to hidden input - loads into memory
5. Click "Add..." button - file already attached
6. Clean up temporary converted files
```

#### 3. Address Proof Upload (Driving License)
```
1. Select "Current Address Proof" from dropdown
2. Set file to hidden input - loads into memory
3. Click "Add..." button
4. Fill document number when prompted
5. File uploads automatically (already in memory)
6. Clean up temporary converted files
```

## Key Changes

### Before
- Click "Add..." button first
- File browser dialog opens
- Manual file selection required
- Interrupts automation

### After
- Load file into memory first using `set_input_files()`
- Click "Add..." button
- No dialog appears (file already attached)
- Fully automated

## File Cleanup
- PDF files converted to images are stored temporarily
- After successful upload, temporary files are deleted from RAM
- Original files in `uploaded_documents/` folder remain intact
- Only conversion artifacts are cleaned up

## Technical Details

### Playwright Method Used
```python
file_input = page_form.locator("input[type='file']").last
file_input.set_input_files(file_path)  # Loads file into browser memory
```

This method:
- Finds the hidden file input element
- Sets the file directly without triggering the browser's file picker
- Keeps file in browser memory until upload completes
- Prevents the Windows file dialog from appearing

## Benefits
1. No manual intervention required
2. Files handled programmatically
3. Temporary files cleaned up automatically
4. Smooth automation flow
5. No file browser dialogs

## Storage Strategy
- Documents uploaded in frontend → saved to `ORCHESTRA/Playwright/uploaded_documents/`
- Playwright reads from this folder
- Converts PDFs to images in memory
- Uploads images to portal
- Cleans up temporary conversions
- Original files remain for future use
