# Voice Agent PAN Registration Integration

## Overview

The voice agent now fully supports the complete PAN registration workflow through natural voice interactions. All flows from the chat-based receptionist have been integrated and optimized for voice.

## Supported Flows

### 1. **New PAN Application (Indian Citizen)**
Complete guided flow for Form 49A application:

**Application Details Collection:**
- Applicant type selection
- Submission mode (Aadhaar eKYC / Upload & eSign / Physical courier)
- Delivery mode (Physical + Soft copy / Soft copy only)
- Aadhaar photo consent
- Source of income (multiple selection)
- Address for communication
- Residential status
- Representative assessee

**Personal Details Collection:**
- Full name (as per Aadhaar)
- Mother's name
- Email address
- Annual income/salary

**Details Confirmation:**
- Review all collected information
- Update any field at any time
- Multi-field updates supported

**Document Upload Instructions:**
- Aadhaar card (front & back)
- Passport-size photograph
- Driving license (if applicable)

### 2. **Voice Interaction Features**

#### Natural Language Understanding
The voice agent understands various ways to express the same intent:

**Starting an application:**
- "I want to apply for a PAN card"
- "How do I register for PAN?"
- "I need a new PAN"
- "Help me get a PAN card"

**Answering questions:**
- For yes/no: "yes", "yeah", "sure", "no", "nope"
- For choices: Say the option name or number
- For text fields: Just speak the value naturally

**Updating fields:**
- "Change my email"
- "Update my name and salary"
- "My mother's name is Lakshmi"
- "I want to change my submission mode"

#### Multi-Field Updates
Update multiple fields in one voice command:
- "Change my name to Ravi and salary to 6 lakhs"
- "Update my email and mother's name"
- Sequential queue: Updates one field at a time for clarity

### 3. **Voice-Optimized Responses**

#### Choice Presentation
Instead of showing buttons, the agent speaks options naturally:

**Radio buttons (single choice):**
- "Are you an Indian citizen, an Indian company or HUF or firm, or a foreign citizen or NRI?"
- "Would you like physical copy plus email, or just email?"

**Checkboxes (multiple choice):**
- "You can pick as many as apply: salary, business or profession, house property, other sources, capital gains, or no income. What are your income sources?"

**Text input:**
- "What's your full name as it appears on your Aadhaar?"
- "What's your annual income or salary?"

#### Markdown Removal
All visual formatting is stripped for voice:
- No bold, italic, or headers
- No bullet points or numbered lists
- No links or tables
- Natural sentence flow with pauses

### 4. **Session Management**

Each voice session maintains:
- Unique session ID
- User ID for profile loading
- Conversation history
- Flow state (current step, collected data)
- Pending updates queue

**Session continuity:**
- Sessions persist across server restarts (Redis + disk storage)
- Profile data auto-loads from previous applications
- Can resume interrupted flows

## Technical Architecture

### Core Components

1. **VoiceReceptionist** (`core/voice_receptionist.py`)
   - Wraps pan-rag receptionist for voice
   - Converts visual responses to voice prompts
   - Handles markdown stripping and choice formatting

2. **VoiceAgent** (`core/agent.py`)
   - Orchestrates STT → Flow/RAG → LLM → TTS pipeline
   - Checks for guided flows first
   - Falls back to RAG+LLM for general questions
   - Adaptive tone based on user emotion

3. **FastAPI Server** (`server.py`)
   - `/api/voice/stt` - Speech to text only
   - `/api/voice/speak` - Full pipeline with guided flow support
   - Session tracking via headers

### Integration Points

The voice agent integrates with:
- **pan-rag receptionist**: All flow logic and state management
- **FlowManager**: Session persistence and step tracking
- **User profiles**: Auto-load saved preferences
- **Document access**: File upload coordination

### Data Flow

```
User speaks → STT (Whisper) 
           → Voice Receptionist → Pan-rag Receptionist
                                → Flow Manager (state check)
                                → Step handler
                                → Options/prompts
           ← Voice-optimized response
           ← TTS (Magpie) → User hears
```

## Usage Examples

### Starting an Application

**User:** "I want to apply for a PAN card"

**Agent:** "Let's get your New PAN Card Application sorted. Are you an Indian citizen, an Indian company or HUF or firm, or a foreign citizen or NRI?"

**User:** "Indian citizen"

**Agent:** "You can choose Aadhaar-based online, upload scanned docs and e-sign, or fill online and courier physical form. Which works for you?"

### Updating Multiple Fields

**User:** "Change my name to Rajesh Kumar and my email to rajesh@example.com"

**Agent:** "Name updated. Continuing from where we left off. Now what's your mother's name?"

**User:** "Wait, also update my salary"

**Agent:** "Sure. What's your annual income or salary?"

### Mid-Flow Updates

At any point during the flow:

**User:** "Actually, I want to change my submission mode"

**Agent:** "Sure. You can choose Aadhaar-based online, upload scanned docs and e-sign, or fill online and courier physical form. Which works for you?"

**User:** "Upload and e-sign"

**Agent:** "Submission mode updated. Continuing from where we left off..."

## Configuration

### Environment Variables

Set in `voice-agent/.env`:

```bash
# NVIDIA API keys
NVIDIA_API_KEY=nvapi-...
STT_API_KEY=nvapi-...  # Optional, defaults to NVIDIA_API_KEY
TTS_API_KEY=nvapi-...  # Optional, defaults to NVIDIA_API_KEY

# TTS voice selection
TTS_VOICE=Magpie-Multilingual.EN-US.Aria

# LLM configuration
LLM_MODEL=meta/llama-3.3-70b-instruct
LLM_TEMPERATURE=0.75
LLM_MAX_TOKENS=280
```

### Voice Agent Personality

Defined in `config.py`:
- Warm, clear, and helpful tone
- Conversational style (contractions, personal pronouns)
- 3-4 sentence maximum responses
- Adaptive to user emotion (confused, urgent, frustrated, grateful)
- Guided flow expertise for PAN registration

## Running the Voice Agent

### CLI Mode (Terminal)

```bash
cd voice-agent
python main.py
```

Speak into your microphone to interact. Say "exit" or "quit" to stop.

### Server Mode (API)

```bash
cd voice-agent
uvicorn server:app --host 0.0.0.0 --port 8002
```

API endpoints:
- `POST /api/voice/stt` - Transcribe audio
- `POST /api/voice/speak` - Full pipeline (STT + Flow + TTS)

### Frontend Integration

The frontend can call the API with:

```javascript
const formData = new FormData();
formData.append('audio', audioBlob);
formData.append('user_id', userId);
formData.append('session_id', sessionId);

const response = await fetch('http://localhost:8002/api/voice/speak', {
  method: 'POST',
  body: formData
});

// Response headers contain:
// X-Transcript: user's spoken text
// X-Reply: agent's text response
// X-Session-Id: session identifier

// Response body is audio/wav for playback
```

## Testing

### Test Flow Coverage

1. **Full application flow** - Start to document upload
2. **Field updates** - Single and multiple field changes
3. **Mid-flow updates** - Change fields after moving ahead
4. **Profile prefill** - Returning user with saved preferences
5. **Error handling** - Typos, ambiguous input, off-topic
6. **Emotion adaptation** - Confused, urgent, frustrated users

### Test Commands

```bash
# Test STT only
curl -X POST http://localhost:8002/api/voice/stt \
  -F "audio=@test.webm"

# Test full pipeline
curl -X POST http://localhost:8002/api/voice/speak \
  -F "audio=@test.webm" \
  -F "user_id=test_user" \
  -F "session_id=test_session" \
  --output response.wav
```

## Troubleshooting

### Common Issues

**Agent doesn't detect PAN application intent:**
- Check receptionist patterns in `service_flows.py`
- Verify fuzzy matching is enabled
- Test with explicit phrases: "I want to apply for PAN"

**Voice responses too verbose:**
- Adjust `LLM_MAX_TOKENS` in config (default 280)
- Enhance markdown stripping in `_strip_markdown_for_voice`
- Check system prompt constraints

**Session state not persisting:**
- Verify Redis connection for Upstash
- Check disk storage path: `pan-rag/storage/sessions/`
- Ensure `FlowManager.save()` is called

**Options not spoken naturally:**
- Review `_add_radio_choices_for_voice` mappings
- Add field-specific prompts for new fields
- Test choice shortening rules

## Future Enhancements

### Multilingual Support
- Detect language from speech
- Load Tamil/Hindi templates
- Use multilingual TTS voices

### Advanced Features
- Voice authentication via voiceprint
- Real-time interruption handling
- Contextual help ("What does this mean?")
- Progress tracking ("How far are we?")

### Integration Improvements
- Direct Aadhaar eKYC via voice OTP
- Document upload via voice commands
- Payment confirmation via voice
- SMS/Email notifications with voice refs

## Support

For issues or questions:
1. Check `voice-agent/README.md` for setup
2. Review logs in console output
3. Test individual components (STT, TTS, receptionist)
4. Verify pan-rag dependencies are installed
