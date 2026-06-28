# image_quality.py - Image Quality Assessment

## Purpose
Analyzes image quality and provides scoring to ensure uploaded documents meet minimum quality standards for successful extraction and verification.

## Key Functions

### process_document(file_bytes, filename)
Main function for image quality assessment.
- **Input**: Document bytes and filename
- **Output**: Quality score (0.0-1.0) and detailed assessment
- **Returns**:
  ```json
  {
    "status": "success|error",
    "quality_score": 0.85,
    "quality_details": "Assessment details",
    "issues": ["blur", "low_contrast"]
  }
  ```

## Quality Metrics

### Brightness Assessment
- Checks average pixel brightness
- Range: 0 (very dark) to 255 (very bright)
- Acceptable range: 40-240
- Low brightness: Hard to read
- High brightness: Overexposed/washed out

### Blur Detection
- Uses Laplacian variance method
- Detects focus quality
- Threshold: Variance > 60 (clear), < 60 (blurry)
- Skipped for signatures (inherently low variance)

### Contrast Analysis
- Measures difference between light and dark areas
- High contrast improves readability
- Low contrast makes text harder to read

### Resolution Check
- Verifies minimum resolution
- Minimum: 150x150 pixels
- Recommends higher for better quality

### Noise Assessment
- Detects random noise in image
- Indicates scanning/compression artifacts
- Affects recognition accuracy

## Quality Score Calculation

```
Quality Score = (
  brightness_score (0-1) * 0.25 +
  focus_score (0-1) * 0.35 +
  contrast_score (0-1) * 0.25 +
  resolution_score (0-1) * 0.15
)
```

## Quality Levels

| Score | Level | Action |
|-------|-------|--------|
| 0.9-1.0 | Excellent | Proceed directly |
| 0.75-0.89 | Good | Process with caution |
| 0.6-0.74 | Fair | May work but quality warning |
| < 0.6 | Poor | Return error, request reupload |

## Issue Detection

Returns list of detected problems:
- "blurry" - Image is out of focus
- "low_brightness" - Image is too dark
- "high_brightness" - Image is overexposed
- "low_contrast" - Text not clearly distinguished
- "low_resolution" - Image too small/pixelated
- "excessive_noise" - Scanner artifacts present
- "skewed" - Document not straight

## Recommendations

Provides user-friendly suggestions:
- "Improve lighting for clearer document"
- "Ensure document is in focus"
- "Center document in frame"
- "Use plain background"
- "Retake in daylight or good lighting"

## Integration

Used by:
- `app.py` - Quality check on all uploads
- Returns early if quality < 0.6
- Prevents processing of poor quality images

## Technical Implementation

### Libraries Used
- OpenCV (cv2) - Image processing
- NumPy - Numerical calculations
- PIL/Pillow - Image handling

### Image Processing Pipeline
1. Read image file
2. Convert to grayscale
3. Calculate metrics
4. Aggregate scores
5. Generate report

## File Format Support
- JPG/JPEG - Standard format
- PNG - Lossless format
- PDF - Document format (skips quality check)
- WebP - Modern format

## Performance
- Processing time: < 200ms per image
- Efficient computation using NumPy
- Minimal memory footprint

## Thresholds
- Blur variance threshold: 60
- Brightness lower bound: 40
- Brightness upper bound: 240
- Minimum resolution: 150x150 pixels
- Quality score threshold: 0.6

## Notes
- Quality assessment is preliminary
- Does not guarantee successful extraction
- Combined with VLM confidence scoring
- Helps reduce failed extraction attempts
- Provides user feedback for re-uploads
