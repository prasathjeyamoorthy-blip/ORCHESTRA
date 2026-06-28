# stt.py - Speech-to-Text Service

## Purpose
Handles conversion of audio files and audio streams to text using Google Cloud Speech-to-Text API. Supports multiple Indian languages with real-time transcription capabilities.

## Key Functions

### transcribe(audio_path, language)
Transcribe a single audio file to text.
- **Input**: Path to audio file, language code (e.g., "en-IN", "hi-IN")
- **Output**: Transcription result with transcript and confidence
- **Format**: Returns dictionary with:
  ```python
  {
    "transcript": "Transcribed text",
    "confidence": 0.95,
    "language": "en-IN",
    "duration_ms": 5000,
    "alternatives": [...]
  }
  ```

### stream_transcribe(language, interim=True)
Real-time streaming transcription from microphone or audio stream.
- **Language**: Language code for transcription
- **Interim**: Include interim results during processing
- **Yields**: Progressive transcription results
- **Streaming**: Low-latency real-time transcription

### batch_transcribe(audio_paths, language)
Process multiple audio files efficiently.
- **Input**: List of audio file paths
- **Returns**: List of transcription results
- **Optimization**: Batch API calls for efficiency

### detect_language(audio_bytes)
Automatically detect language from audio.
- **Input**: Audio data
- **Returns**: Language code with confidence
- **Usage**: Auto-detect when language unknown

## Supported Languages

### Tier 1 - Full Support
- en-IN (English - India)
- hi-IN (Hindi)
- ta-IN (Tamil)
- te-IN (Telugu)
- kn-IN (Kannada)
- ml-IN (Malayalam)
- mr-IN (Marathi)
- gu-IN (Gujarati)

### Tier 2 - Supported
- bn-IN (Bengali)
- pa-IN (Punjabi)
- as-IN (Assamese)
- or-IN (Odia)
- ur-IN (Urdu)
- sa-IN (Sanskrit)

## Audio Format Support
- WAV - Uncompressed audio (recommended)
- MP3 - Compressed audio
- FLAC - Lossless compression
- OGG - Vorbis codec
- AMR - Adaptive Multi-Rate (phones)

## Audio Specifications
- **Sample Rate**: 16000 Hz (16 kHz) recommended
- **Channels**: Mono (1 channel)
- **Bit Depth**: 16-bit
- **Format**: PCM encoding

## Configuration

### Environment Variables
```
GOOGLE_CLOUD_PROJECT=your_project_id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

### Client Setup
```python
from google.cloud import speech_v1
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
)
client = speech_v1.SpeechClient(credentials=credentials)
```

## API Configuration

### RecognitionConfig
```python
config = speech_v1.RecognitionConfig(
    encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
    sample_rate_hertz=16000,
    language_code="en-IN",
    enable_automatic_punctuation=True,
    use_enhanced=True,  # Enhanced model
)
```

## Features

### Confidence Scoring
- Returns confidence (0.0-1.0) for each transcription
- Higher values indicate more confident transcription
- Used to assess transcription quality

### Alternative Transcriptions
- Provides up to N alternative transcriptions
- Helps with ambiguous audio
- Useful for context-dependent transcription

### Punctuation
- Automatic punctuation insertion
- Improves readability
- Can be disabled if needed

### Noise Handling
- Robust to background noise
- Speaker diarization available
- Filters out non-speech sounds

## Error Handling

### Common Errors
- `InvalidArgumentError` - Invalid audio format or language
- `DeadlineExceeded` - Processing timeout
- `NotFound` - Audio file not found
- `PermissionDenied` - API credentials issue

### Error Recovery
```python
try:
    result = stt.transcribe(audio_path, language)
except google.api_core.exceptions.InvalidArgument:
    # Check audio format and language code
    logger.error("Invalid audio or language")
except google.api_core.exceptions.DeadlineExceeded:
    # Retry with smaller audio chunk
    logger.warning("Processing timeout, retrying")
```

## Performance

### Latency
- File transcription: 500ms - 2 seconds
- Streaming: < 500ms (real-time)
- Batch processing: Proportional to total duration

### Accuracy
- Clean audio: 95%+ accuracy
- Noisy environment: 85%+ accuracy
- Accented speech: 90%+ accuracy

## Integration

### With Flask
```python
from flask import request, jsonify
from core.stt import SpeechToText

stt = SpeechToText()

@app.route('/api/stt', methods=['POST'])
def speech_to_text():
    audio_file = request.files['audio']
    language = request.args.get('language', 'en-IN')
    
    result = stt.transcribe(audio_file.read(), language)
    return jsonify(result)
```

### With Frontend
```javascript
// Send audio to backend
fetch('/api/stt?language=hi-IN', {
  method: 'POST',
  body: audioBlob,
  headers: {'Content-Type': 'audio/wav'}
})
.then(r => r.json())
.then(data => console.log(data.transcript))
```

## Best Practices

### Audio Recording
- Record in quiet environment
- Use standard microphone
- Maintain clear speech
- Avoid overlapping speakers

### Language Selection
- Use appropriate language code
- Consider dialect variations
- Test with sample audio
- Provide language picker to users

### Error Handling
- Implement retry logic
- Provide fallback text input
- Show confidence scores
- Validate transcription quality

### Cost Optimization
- Use streaming for real-time
- Batch process when possible
- Cache common results
- Monitor API usage

## Dependencies
- `google-cloud-speech` - Google Cloud client
- `google-auth-oauthlib` - Authentication
- `grpcio` - gRPC communication
- `librosa` - Audio processing (optional)

## Notes
- Requires Google Cloud account and service account credentials
- Billed per 15-second audio blocks
- Streaming has different pricing model
- Enhanced model provides better accuracy (higher cost)
- Regional endpoints available for reduced latency
