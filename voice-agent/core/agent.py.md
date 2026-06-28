# agent.py - Agent Coordination

## Purpose
Core orchestration module that coordinates between different voice services and manages business logic for voice-based document processing and application workflows.

## Key Responsibilities
- Coordinate STT, TTS, and LLM services
- Manage conversation flow and state
- Handle business logic for document operations
- Track user progress through application
- Integrate with backend document processing

## Main Components

### VoiceAgent Class
Primary agent for voice interactions.

**Initialization**:
```python
agent = VoiceAgent(
    language="en-IN",
    user_id="user-123",
    voice_type="female"
)
```

**Key Methods**:
- `process_voice_input(audio)` - Process incoming audio
- `get_response(text)` - Generate response
- `execute_action(intent)` - Execute based on intent
- `maintain_state()` - Track conversation state

## Workflow Management

### Application State Machine

```
START
  ↓
GREETING - Greet user
  ↓
GET_INTENT - Understand what user wants
  ↓
PROCESS_REQUEST - Handle the request
  ├─ UPLOAD_DOCUMENT
  ├─ CHECK_STATUS  
  ├─ MODIFY_DATA
  ├─ SUBMIT_APPLICATION
  └─ GET_HELP
  ↓
CONFIRM_ACTION - Confirm completion
  ↓
OFFER_NEXT - Suggest next step
  ↓
LOOP or END
```

## Service Coordination

### STT Service Integration
```python
def get_user_input(self, language):
    audio = capture_audio()
    transcript = self.stt.transcribe(audio, language)
    return transcript
```

### TTS Service Integration
```python
def speak_response(self, response_text, language):
    audio = self.tts.synthesize(response_text, language)
    play_audio(audio)
```

### LLM Service Integration
```python
def understand_intent(self, text):
    intent = self.llm.extract_intent(text)
    return intent
```

## Business Logic

### Document Upload Intent Handler
```python
def handle_upload_document(self):
    # 1. Ask which document type
    # 2. Wait for document
    # 3. Call backend API
    # 4. Return extracted data
    # 5. Ask for confirmation
```

### Status Check Handler
```python
def handle_check_status(self, user_id):
    # 1. Query backend for status
    # 2. Format status for voice
    # 3. Provide estimated timeline
    # 4. Offer next steps
```

### Data Modification Handler
```python
def handle_modify_data(self, field_name, new_value):
    # 1. Confirm field to modify
    # 2. Get new value via voice
    # 3. Validate new value
    # 4. Update in database
    # 5. Confirm completion
```

## State Management

### Context Tracking
```python
self.context = {
    "user_id": "user-123",
    "language": "en-IN",
    "current_intent": "upload_document",
    "extracted_data": {},
    "conversation_turns": 0,
    "session_start": timestamp,
    "last_action": "greeting"
}
```

### State Persistence
- Store conversation history
- Track user progress
- Remember preferences
- Maintain session across interactions

## Error Recovery

### Graceful Degradation
- If STT fails: Ask user to repeat
- If API fails: Offer retry or manual input
- If TTS fails: Provide text output
- If LLM fails: Use simple pattern matching

### User Guidance
- Clear error explanations
- Suggestions for correction
- Fallback options
- Manual alternative paths

## Integration Points

### Backend API Calls
```python
def upload_to_backend(self, document_data):
    response = requests.post(
        "/api/verify",
        data=document_data,
        headers={"auth_id": self.user_id}
    )
    return response.json()
```

### Data Persistence
```python
def save_conversation(self, intent, response):
    # Log conversation for training/debugging
    # Store extracted data
    # Update user progress
```

## Conversation Features

### Context Awareness
- Remember previous messages
- Reference extracted data
- Suggest relevant next steps
- Personalize responses

### Natural Language
- Conversational tone
- Varied responses
- Proper pronouns and references
- Language-appropriate expressions

### Confirmation & Safety
- Confirm critical actions
- Ask before proceeding
- Provide review of changes
- Allow cancellation

## Performance Optimization

### Caching
- Cache extracted data
- Store common responses
- Remember user preferences
- Reuse session state

### Async Operations
- Don't block on API calls
- Provide updates during wait
- Handle long-running processes
- Implement timeouts

## Logging & Monitoring

### Conversation Logging
```python
def log_interaction(self, user_input, intent, response):
    log_entry = {
        "timestamp": now(),
        "user_id": self.user_id,
        "input": user_input,
        "intent": intent,
        "response": response,
        "success": True/False
    }
    save_to_log(log_entry)
```

### Metrics
- STT confidence
- Intent accuracy
- Response success rate
- Average conversation length
- Error frequency

## Configuration

### Agent Parameters
```python
config = {
    "language": "en-IN",
    "timeout": 30,  # seconds
    "max_retries": 3,
    "confidence_threshold": 0.7,
    "voice_type": "female"
}
```

## Dependencies
- `core.stt` - Speech recognition
- `core.tts` - Speech synthesis
- `core.llm` - Intent recognition
- `core.voice_receptionist` - User interaction
- `requests` - Backend API calls

## Notes
- Stateful across conversation turns
- Handles interruptions gracefully
- Supports context switching
- Extensible intent system
- Recoverable from various errors
- Maintains audit trail
