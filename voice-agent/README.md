# Voice Agent - Speech Processing Service

Voice input/output service providing speech-to-text (STT) and text-to-speech (TTS) capabilities for the PAN application.

## Overview

Voice Agent enables:
- Speech-to-text conversion
- Text-to-speech synthesis
- Multi-language support (Indian languages)
- Voice command processing
- Audio quality assessment
- Real-time transcription

## Project Structure

```
voice-agent/
├── core/                       # Core voice processing
│   ├── stt.py                 # Speech-to-text
│   ├── tts.py                 # Text-to-speech
│   ├── audio_processor.py     # Audio handling
│   └── language.py            # Language support
├── server.py                  # Server and routes
├── main_simple.py             # Simple entry point
├── requirements.txt           # Dependencies
└── README.md                  # This file
```

## Features

- **Multiple Languages**: Support for 22 Indian languages
- **Real-time Processing**: Immediate transcription and synthesis
- **Quality Assessment**: Audio quality scoring
- **Error Handling**: Graceful degradation
- **Caching**: Reduce API calls with result caching
- **Streaming**: Real-time audio streaming support

## Supported Languages

### Tier 1 (Fully Supported)
- English (en-IN)
- Hindi (hi-IN)
- Tamil (ta-IN)
- Telugu (te-IN)
- Kannada (kn-IN)
- Malayalam (ml-IN)
- Marathi (mr-IN)
- Gujarati (gu-IN)

### Tier 2 (Supported)
- Bengali (bn-IN)
- Punjabi (pa-IN)
- Assamese (as-IN)
- Odia (or-IN)
- Urdu (ur-IN)
- Sanskrit (sa-IN)

## Installation

```bash
cd voice-agent
pip install -r requirements.txt
```

## Configuration

### Environment Variables

```
GOOGLE_CLOUD_PROJECT=your_project_id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
STT_LANGUAGE=hi-IN
TTS_LANGUAGE=hi-IN
```

## API Endpoints

### Speech-to-Text

```
POST /api/stt
Content-Type: audio/wav or audio/mp3

Binary audio data in body

Response:
{
  "status": "success",
  "transcript": "User's spoken text",
  "language": "hi-IN",
  "confidence": 0.95,
  "duration_ms": 2500,
  "alternatives": [
    {
      "transcript": "Alternative transcription",
      "confidence": 0.87
    }
  ]
}
```

### Text-to-Speech

```
POST /api/tts
Content-Type: application/json

{
  "text": "नमस्ते, आपका स्वागत है",
  "language": "hi-IN",
  "voice": "female",
  "rate": 1.0,
  "pitch": 0.0
}

Response: Audio file (binary)
Content-Type: audio/mp3
```

### Audio Quality Assessment

```
POST /api/assess_audio
Content-Type: audio/wav

Binary audio data

Response:
{
  "quality_score": 0.85,
  "noise_level": 0.2,
  "clarity": 0.9,
  "background_noise": false,
  "suggestion": "Audio quality is good"
}
```

### Language Detection

```
POST /api/detect_language
Content-Type: audio/wav

Binary audio data

Response:
{
  "detected_language": "hi-IN",
  "language_name": "Hindi",
  "confidence": 0.98,
  "alternatives": [
    {
      "language": "en-IN",
      "confidence": 0.01
    }
  ]
}
```

## Usage Examples

### Basic Speech-to-Text

```python
from core.stt import SpeechToText

stt = SpeechToText()

# Convert audio file to text
result = stt.transcribe(
    audio_path="audio.wav",
    language="hi-IN"
)

print(result["transcript"])
print(f"Confidence: {result['confidence']}")
```

### Real-time Transcription

```python
from core.stt import SpeechToText

stt = SpeechToText()

# Stream-based transcription
transcript = ""
for chunk in stt.stream_transcribe(
    language="en-IN",
    interim=True
):
    if chunk["is_final"]:
        transcript += chunk["transcript"]
        print(f"Final: {chunk['transcript']}")
    else:
        print(f"Interim: {chunk['transcript']}")
```

### Text-to-Speech

```python
from core.tts import TextToSpeech

tts = TextToSpeech()

# Synthesize speech
audio_bytes = tts.synthesize(
    text="Welcome to PAN application",
    language="en-IN",
    voice_type="female",
    rate=1.0
)

# Save or play audio
with open("output.mp3", "wb") as f:
    f.write(audio_bytes)
```

### Multi-Language Support

```python
from core.language import LanguageManager

lang_mgr = LanguageManager()

# Detect language
detected = lang_mgr.detect("बधाई हो")

# Get supported languages
languages = lang_mgr.get_supported_languages()

# Get language info
info = lang_mgr.get_language_info("hi-IN")
print(f"Language: {info['name']}")
print(f"Script: {info['script']}")
```

## Core Components

### SpeechToText (stt.py)
Converts audio to text using Google Cloud Speech-to-Text API.

**Methods:**
- `transcribe(audio_path, language)` - Convert audio file to text
- `stream_transcribe(language, interim)` - Real-time streaming transcription
- `batch_transcribe(audio_paths, language)` - Process multiple files
- `get_alternatives(audio, language, max_alternatives)` - Get alternative transcriptions

### TextToSpeech (tts.py)
Converts text to audio using Google Cloud Text-to-Speech API.

**Methods:**
- `synthesize(text, language, voice_type)` - Generate speech audio
- `stream_synthesize(text_chunks, language)` - Stream synthesis
- `batch_synthesize(texts, language)` - Generate multiple audio files
- `apply_effects(audio_bytes, effects)` - Apply audio effects

### AudioProcessor (audio_processor.py)
Handles audio format conversion and quality assessment.

**Methods:**
- `convert_format(input, input_format, output_format)` - Convert audio format
- `assess_quality(audio_bytes)` - Evaluate audio quality
- `denoise(audio_bytes)` - Remove background noise
- `normalize_volume(audio_bytes)` - Normalize audio levels

### LanguageManager (language.py)
Manages language-specific configurations.

**Methods:**
- `detect(text)` - Detect language of text
- `get_supported_languages()` - List all supported languages
- `get_language_info(lang_code)` - Get language metadata
- `validate_language(lang_code)` - Check if language is supported

## Audio Quality Scoring

Quality Score Calculation:
```
Quality = (
  clarity_score * 0.5 +
  signal_to_noise_ratio * 0.3 +
  frequency_balance * 0.2
)
```

**Interpretation:**
- 0.9-1.0: Excellent quality
- 0.75-0.89: Good quality
- 0.60-0.74: Acceptable quality
- < 0.60: Poor quality, recommend re-recording

## Error Handling

### Common Errors

```python
from core.stt import SpeechToTextError

try:
    result = stt.transcribe(audio_path)
except SpeechToTextError.AudioError as e:
    print(f"Audio processing failed: {e}")
except SpeechToTextError.LanguageError as e:
    print(f"Unsupported language: {e}")
except SpeechToTextError.APIError as e:
    print(f"API error: {e}")
```

## Integration with Backend

### Flask Integration

```python
from flask import request, jsonify
from core.stt import SpeechToText
from core.tts import TextToSpeech

stt = SpeechToText()
tts = TextToSpeech()

@app.route('/api/stt', methods=['POST'])
def speech_to_text():
    audio = request.data
    language = request.args.get('language', 'en-IN')
    
    result = stt.transcribe(
        audio_bytes=audio,
        language=language
    )
    
    return jsonify(result)

@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    data = request.get_json()
    
    audio = tts.synthesize(
        text=data['text'],
        language=data.get('language', 'en-IN'),
        voice_type=data.get('voice', 'neutral')
    )
    
    return audio, 200, {'Content-Type': 'audio/mp3'}
```

## Performance

- **STT Latency**: 500ms - 2s per audio
- **TTS Latency**: 200ms - 1s per text
- **Quality Assessment**: < 100ms
- **Language Detection**: < 200ms

## Optimization Tips

1. **Pre-record Guidance**: Guide users on recording quality
2. **Audio Compression**: Compress audio before transmission
3. **Caching**: Cache common phrases in TTS
4. **Batch Processing**: Process multiple audios in batch
5. **Selective Enhancement**: Only enhance noisy audio

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Low transcription accuracy | Poor audio quality | Record in quiet environment |
| Unsupported language | Language not in list | Use supported language codes |
| Slow processing | Large audio file | Use shorter clips or compression |
| Accent issues | Non-native speaker | Speak clearly and slowly |
| TTS sounds robotic | Wrong voice settings | Adjust pitch and rate |

## Best Practices

1. **Audio Recording**: Use 16kHz, 16-bit mono audio
2. **Language Selection**: Let user choose language or auto-detect
3. **Error Feedback**: Show user-friendly error messages
4. **Testing**: Test with various accents and background noise
5. **Fallback**: Provide text input option alongside voice

## Future Enhancements

- [ ] Speaker identification
- [ ] Emotion detection in speech
- [ ] Custom vocabulary/phrases
- [ ] Real-time translation
- [ ] Voice biometrics
- [ ] Accent adaptation
- [ ] Dialect support

## Dependencies

Key packages:
- `google-cloud-speech` - Speech-to-text API
- `google-cloud-texttospeech` - Text-to-speech API
- `librosa` - Audio processing
- `numpy` - Numerical operations
- `flask` - Web framework (if running as service)

## License

Proprietary and confidential.

## Support

For issues or questions, contact the development team.
