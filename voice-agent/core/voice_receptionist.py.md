# voice_receptionist.py - Voice Interface Coordinator

## Purpose
Coordinates the voice interface by managing interactions between speech recognition, text processing, and speech synthesis. Acts as the main orchestrator for voice-based conversations.

## Key Functions

### process_voice_input(audio_bytes, language)
Main entry point for voice input processing.
- **Input**: Audio bytes and language code
- **Output**: Processed text and extracted intent
- **Flow**: STT → Intent parsing → Response generation

### generate_voice_response(text, language, voice_type)
Generate spoken response from text.
- **Input**: Response text, language, voice preference
- **Output**: Audio bytes
- **Features**: Supports custom voice parameters

### handle_conversation(audio_bytes, language, context)
Full conversation handling with context.
- **Maintains**: Conversation history
- **Context**: Previous interactions
- **Returns**: Text and audio response

## Conversation Flow

1. **Receive Audio** - Capture voice input
2. **Transcribe** - Convert to text via STT
3. **Parse Intent** - Understand user request
4. **Generate Response** - Prepare answer
5. **Synthesize** - Convert to speech via TTS
6. **Stream Audio** - Play to user

## Intent Recognition

### Supported Intents
- `upload_document` - User wants to upload document
- `get_status` - Check application status
- `view_data` - See extracted data
- `modify_data` - Edit extracted information
- `submit_application` - Submit for verification
- `help` - Request assistance
- `cancel` - Cancel current operation

### Intent Extraction
```python
intent = extract_intent(text)
# Returns: {"intent": "upload_document", "confidence": 0.95}
```

## State Management

### Conversation States
- `greeting` - Initial greeting
- `listening` - Waiting for user input
- `processing` - Processing request
- `speaking` - Playing response
- `confirming` - Asking for confirmation

### Context Tracking
```python
context = {
    "user_id": "user-123",
    "language": "en-IN",
    "state": "listening",
    "history": [],  # Previous exchanges
    "data": {}  # Extracted information
}
```

## Response Generation

### Template-Based Responses
Predefined responses for common intents:

```python
responses = {
    "upload_document": "Sure! Please upload your document.",
    "get_status": "Your status is: {status}",
    "help": "I can help you with document upload, status check, etc."
}
```

### Dynamic Responses
Generated responses for specific contexts:
- Confirmation messages with extracted data
- Error explanations with suggestions
- Guided instructions for next steps

## Integration

### With STT Service
```python
from core.stt import SpeechToText
from core.voice_receptionist import VoiceReceptionist

stt = SpeechToText()
receptionist = VoiceReceptionist()

audio_bytes = get_user_audio()
transcript = stt.transcribe(audio_bytes, "en-IN")
response = receptionist.generate_response(transcript)
```

### With TTS Service
```python
from core.tts import TextToSpeech

tts = TextToSpeech()
response_audio = tts.synthesize(response, "en-IN")
play_audio(response_audio)
```

## Configuration

### Environment Variables
```
VOICE_LANGUAGE=en-IN
VOICE_TYPE=female
VOICE_TIMEOUT=30s
VOICE_CONFIDENCE_THRESHOLD=0.7
```

### Settings
- Default language
- Voice preferences
- Response timeout
- Confidence thresholds

## Error Handling

### Recovery Strategies
- **Unclear Input**: Ask for clarification
- **Connection Loss**: Offer retry
- **Timeout**: Provide default response
- **API Error**: Fallback to text interface

### User Feedback
- Confirmation of understood intent
- Request for missing information
- Error explanations
- Suggestions for next steps

## Features

### Natural Conversation
- Contextual responses
- Conversational tone
- Proper language variants
- Accent-appropriate voices

### Multi-Language Support
- Automatic language detection
- Language-specific responses
- Proper pronunciation
- Cultural appropriateness

### Accessibility
- Clear spoken instructions
- Confirmations for critical actions
- Ability to switch to text mode
- Adjustable speech rate

## Performance

### Latency
- STT: 500ms - 2s
- Intent parsing: 50-100ms
- Response generation: 100-200ms
- TTS: 200-1000ms
- Total: 1-4 seconds per turn

## User Interactions

### Document Upload Flow
1. "Hi, I want to upload a document"
2. → "What type of document? (Aadhaar, PAN, etc.)"
3. "Aadhaar card"
4. → "Ready to receive. Please provide the image."

### Status Check Flow
1. "What's my application status?"
2. → "Checking... Your status is pending review"
3. "When will it be done?"
4. → "Usually 2-3 working days. You'll get an email update."

## Best Practices

### Conversation Design
- Be clear and concise
- Confirm important actions
- Provide options when applicable
- Maintain consistent tone

### Error Handling
- Never blame user
- Offer solutions
- Provide fallback options
- Log for improvement

### Accessibility
- Support text alternative
- Adjustable speech rate
- Multiple languages
- Clear pronunciation

## Dependencies
- `core.stt` - Speech-to-text
- `core.tts` - Text-to-speech
- `core.llm` - Intent parsing/NLP
- `core.agent` - Business logic

## Notes
- Maintains conversation context across turns
- Supports both voice and text modes
- Recoverable from various errors
- Extensible intent system
- Language-aware responses
