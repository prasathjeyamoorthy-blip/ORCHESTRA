# tts.py - Text-to-Speech Service

## Purpose
Converts text to natural-sounding audio using Google Cloud Text-to-Speech API. Supports multiple Indian languages, voices, and customizable speech parameters.

## Key Functions

### synthesize(text, language, voice_type, rate, pitch)
Convert text to audio file.
- **Input**: 
  - text: String to convert
  - language: Language code (e.g., "hi-IN")
  - voice_type: "male" or "female"
  - rate: Speech rate (0.25-4.0, default 1.0)
  - pitch: Pitch adjustment (-20 to 20, default 0)
- **Output**: Audio bytes (MP3 format)
- **Features**: Natural-sounding speech, emotional control

### stream_synthesize(text_chunks, language)
Stream synthesis for long texts.
- **Input**: List of text chunks
- **Yields**: Audio stream chunks
- **Usage**: Real-time audio playback

### batch_synthesize(texts, language, voice_type)
Process multiple texts efficiently.
- **Input**: List of texts
- **Output**: List of audio bytes
- **Optimization**: Batch API calls

### list_voices(language)
Get available voices for language.
- **Returns**: List of available voice options
- **Includes**: Gender, name, language variants

## Supported Languages

### Supported with Multiple Voices
- en-IN (English - India) - male, female
- hi-IN (Hindi) - male, female
- ta-IN (Tamil) - male, female
- te-IN (Telugu) - male, female
- kn-IN (Kannada) - male, female
- ml-IN (Malayalam) - male, female
- mr-IN (Marathi) - male, female
- gu-IN (Gujarati) - male, female

### Also Supported
- Bengali, Punjabi, Assamese, Odia, Urdu, Sanskrit

## Voice Options

### Voice Types
- **Male**: Deep, authoritative tone
- **Female**: Clear, friendly tone
- **Neutral**: Gender-neutral voice (if available)

### Voice Parameters
- **Speaking Rate**: 0.25 (slow) to 4.0 (fast)
- **Pitch**: -20 (low) to +20 (high)
- **Volume Gain**: -16 to +16 dB
- **Effects Profile**: Different audio environments

## Audio Output Formats
- MP3 - Default, compressed
- OGG - Alternative compressed format
- LINEAR16 - Uncompressed (larger files)
- MULAW - Telephony format

## Configuration

### Environment Variables
```
GOOGLE_CLOUD_PROJECT=your_project_id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
TTS_LANGUAGE=hi-IN
TTS_VOICE=female
```

### Client Setup
```python
from google.cloud import texttospeech_v1

client = texttospeech_v1.TextToSpeechClient()
```

## API Configuration

### SynthesisInput
```python
synthesis_input = texttospeech_v1.SynthesisInput(text=text)
```

### VoiceSelectionParams
```python
voice = texttospeech_v1.VoiceSelectionParams(
    language_code="hi-IN",
    name="hi-IN-Standard-A",  # Specific voice
    ssml_gender=texttospeech_v1.SsmlVoiceGender.FEMALE
)
```

### AudioConfig
```python
audio_config = texttospeech_v1.AudioConfig(
    audio_encoding=texttospeech_v1.AudioEncoding.MP3,
    speaking_rate=1.0,
    pitch=0.0,
    volume_gain_db=0.0
)
```

## Features

### Speech Customization
- Speaking rate from 0.25x to 4x
- Pitch adjustment from -20 to +20 semitones
- Volume gain from -16 to +16 dB
- Multiple voice options

### Advanced Features
- SSML support for fine-grained control
- Emphasis control (strong, moderate, reduced)
- Break insertion for pauses
- Character substitution

### Quality
- Natural sounding speech
- Proper pronunciation of Indian names
- Language-specific accent
- Emotional tone variations (where supported)

## Error Handling

### Common Errors
- `InvalidArgumentError` - Invalid text, language, or parameters
- `ResourceExhausted` - API quota exceeded
- `Unavailable` - Service temporarily unavailable
- `Unauthenticated` - Invalid credentials

### Error Recovery
```python
try:
    audio = tts.synthesize(text, language)
except google.api_core.exceptions.InvalidArgument:
    logger.error("Invalid text or language")
except google.api_core.exceptions.ResourceExhausted:
    logger.warning("API quota exceeded, retrying later")
```

## Performance

### Latency
- Single sentence: < 500ms
- Paragraph: 1-2 seconds
- Long text: Streaming for progressive playback

### Audio Quality
- Natural voice samples
- Clear pronunciation
- Proper intonation
- Good emotional expression

## Integration

### With Flask
```python
from flask import request, jsonify
from core.tts import TextToSpeech

tts = TextToSpeech()

@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    data = request.get_json()
    text = data['text']
    language = data.get('language', 'en-IN')
    
    audio = tts.synthesize(text, language)
    return audio, 200, {
        'Content-Type': 'audio/mp3',
        'Content-Disposition': 'attachment; filename="output.mp3"'
    }
```

### With Frontend
```javascript
// Play TTS audio
const response = await fetch('/api/tts', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({text: "नमस्ते", language: "hi-IN"})
});

const audioBlob = await response.blob();
const audio = new Audio(URL.createObjectURL(audioBlob));
audio.play();
```

## Best Practices

### Text Processing
- Keep sentences short (< 20 words)
- Use clear, simple language
- Avoid acronyms (spell out)
- Use punctuation for breaks

### Voice Selection
- Match voice to content context
- Maintain consistency
- Test with users
- Consider accessibility

### Performance
- Cache frequently used phrases
- Use streaming for long texts
- Implement rate limiting
- Monitor API usage

### Accessibility
- Always provide text alternative
- Use captions with audio
- Allow speed adjustment
- Support language selection

## SSML Support

Enhanced control using SSML:
```xml
<speak>
  <emphasis level="strong">Important</emphasis>
  information.
  <break time="500ms"/>
  Continue speaking.
</speak>
```

## Dependencies
- `google-cloud-texttospeech` - Google Cloud client
- `google-auth-oauthlib` - Authentication
- `grpcio` - gRPC communication

## Notes
- Requires Google Cloud account and credentials
- Billed per 1000 characters
- Caching results recommended
- Different voices have different capabilities
- Regional endpoints available
- SSML provides advanced control options
