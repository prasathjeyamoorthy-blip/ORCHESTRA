# Voice Agent for PAN Registration

A fully-featured voice assistant for PAN card registration that combines speech recognition, natural language understanding, and text-to-speech to provide a hands-free application experience.

## Features

### 🎯 Complete PAN Registration Flow
- **New PAN application** (Form 49A for Indian citizens)
- **Application details** collection (submission mode, delivery preferences)
- **Personal details** gathering (name, email, income, address)
- **Multi-field updates** - Change any field at any time via voice
- **Smart confirmation** - Review and update before final submission
- **Document guidance** - Voice instructions for required documents

### 🗣️ Natural Voice Interactions
- Understands various phrasings ("I want a PAN", "Apply for PAN card", "Get me a PAN")
- Handles typos from speech recognition ("aply", "oan" instead of "pan")
- Accepts natural yes/no responses ("yeah", "sure", "yup", "nope")
- Multi-turn conversations with context retention
- Adaptive tone based on user emotion (confused, urgent, frustrated)

### 🔄 Intelligent Flow Management
- **Profile prefill** - Returning users skip already-answered questions
- **Mid-flow updates** - Change submission mode, delivery, or any field after moving ahead
- **Sequential updates** - "Change my address and delivery mode" → handles one at a time
- **Session persistence** - Resume interrupted flows across restarts

### 🎤 Voice-Optimized Responses
- All markdown formatting stripped for natural speech
- Button options converted to spoken lists
- Complex forms simplified into conversational prompts
- Sentence-by-sentence streaming for responsive feel

## Architecture

```
┌─────────────┐
│   User      │
│  Microphone │
└──────┬──────┘
       │ Audio
       ▼
┌─────────────────┐
│  STT (Whisper)  │  ← faster-whisper (local) or NVIDIA NIM (cloud)
└────────┬────────┘
         │ Transcript
         ▼
┌──────────────────────┐
│ Voice Receptionist   │  ← Converts visual flows to voice prompts
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  PAN-RAG Receptionist│  ← Guided flow logic, state management
│  + Flow Manager      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  RAG + LLM (fallback)│  ← For general questions
└──────────┬───────────┘
           │ Response text
           ▼
┌─────────────────┐
│ TTS (Magpie)    │  ← nvidia/magpie-tts-multilingual
└────────┬────────┘
         │ Audio
         ▼
┌─────────────┐
│   User      │
│  Speaker    │
└─────────────┘
```

## Installation

### 1. Prerequisites

**Python 3.10+** and **uv** package manager:

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
# or on Windows with pip:
pip install uv
```

### 2. Install Dependencies

```bash
cd voice-agent
uv pip install -r requirements.txt
```

Key dependencies:
- `faster-whisper` - Local STT (CPU-friendly)
- `nvidia-riva` - NVIDIA NIM STT/TTS cloud APIs
- `fastapi` - Web server for API endpoints
- `rank-bm25` - RAG retrieval
- `openai` - LLM client (NVIDIA NIM compatible)

### 3. Environment Setup

Create `.env` file in `voice-agent/`:

```bash
# NVIDIA API Key (get from build.nvidia.com)
NVIDIA_API_KEY=nvapi-...

# Optional: Separate keys for STT/TTS (defaults to NVIDIA_API_KEY)
STT_API_KEY=nvapi-...
TTS_API_KEY=nvapi-...

# TTS Voice Selection
TTS_VOICE=Magpie-Multilingual.EN-US.Aria

# LLM Configuration
LLM_MODEL=meta/llama-3.3-70b-instruct
LLM_TEMPERATURE=0.75
LLM_MAX_TOKENS=280
```

### 4. Verify PAN-RAG Integration

Ensure `pan-rag` module is accessible:

```bash
cd ../pan-rag
uv pip install -e .
```

The voice agent imports from `pan-rag/agent/` for flow logic.

## Usage

### CLI Mode (Terminal Voice Chat)

```bash
cd voice-agent
python main.py
```

- Speak into your microphone
- Agent responds with voice
- Say "exit" or "quit" to stop
- Say "reset" to start a new conversation

**Example Interaction:**
```
🎙️ User: I want to apply for a PAN card
🤖 Agent: Let's get your New PAN Card Application sorted. 
         Are you an Indian citizen, an Indian company or HUF 
         or firm, or a foreign citizen or NRI?

🎙️ User: Indian citizen
🤖 Agent: You can choose Aadhaar-based online, upload scanned 
         docs and e-sign, or fill online and courier physical 
         form. Which works for you?
```

### Server Mode (API)

```bash
cd voice-agent
uvicorn server:app --host 0.0.0.0 --port 8002
```

#### Endpoints

**1. Speech-to-Text Only**
```bash
POST /api/voice/stt
Content-Type: multipart/form-data

Body:
  audio: <audio file> (webm, ogg, wav)

Response:
{
  "transcript": "I want to apply for a PAN card"
}
```

**2. Full Voice Pipeline**
```bash
POST /api/voice/speak
Content-Type: multipart/form-data

Body:
  audio: <audio file>
  user_id: <user identifier> (optional)
  session_id: <session identifier> (optional)

Response:
  Audio/wav stream with headers:
    X-Transcript: <user's text>
    X-Reply: <agent's text>
    X-Session-Id: <session identifier>
```

#### Frontend Integration Example

```javascript
// Record audio from microphone
const mediaRecorder = new MediaRecorder(stream, {
  mimeType: 'audio/webm;codecs=opus'
});

// On recording stop, send to agent
mediaRecorder.ondataavailable = async (e) => {
  const formData = new FormData();
  formData.append('audio', e.data);
  formData.append('user_id', userId);
  formData.append('session_id', sessionId);
  
  const response = await fetch('http://localhost:8002/api/voice/speak', {
    method: 'POST',
    body: formData
  });
  
  // Get transcript and reply from headers
  const transcript = decodeURIComponent(
    response.headers.get('X-Transcript')
  );
  const reply = decodeURIComponent(
    response.headers.get('X-Reply')
  );
  
  // Play audio response
  const audioBlob = await response.blob();
  const audioUrl = URL.createObjectURL(audioBlob);
  new Audio(audioUrl).play();
};
```

## Testing

### Run Test Suite

```bash
cd voice-agent
python test_voice_flows.py
```

Tests include:
- ✅ Full application flow (start to document upload)
- ✅ Field update mid-flow
- ✅ Multi-field updates
- ✅ Typo handling ("aply for oan")
- ✅ Natural language variations ("yeah", "sure", "yup")

### Manual Testing

Use curl to test the API:

```bash
# Test with a pre-recorded audio file
curl -X POST http://localhost:8002/api/voice/speak \
  -F "audio=@test_audio.webm" \
  -F "user_id=test_user" \
  --output response.wav

# Play the response
# Windows: start response.wav
# macOS: afplay response.wav
# Linux: aplay response.wav
```

## Voice Interaction Patterns

### Starting an Application

All these work:
- "I want to apply for a PAN card"
- "How do I register for PAN?"
- "I need a new PAN"
- "Help me get a PAN"
- "Apply for PAN"

Even with typos:
- "I wnat to aply for oan"
- "I want to appply for pann"

### Answering Questions

**Yes/No questions:**
- Yes: "yes", "yeah", "yep", "yup", "sure", "okay"
- No: "no", "nope", "nah"

**Single choice:**
- Say the option: "Indian citizen", "Aadhaar online"
- Or by number: "option 1", "first one"

**Multiple choice:**
- "Salary and capital gains"
- "Business or profession, also house property"

**Text input:**
- Just speak naturally: "Rajesh Kumar"
- "My name is Rajesh Kumar"
- "6 lakhs" or "600000" for salary

### Updating Fields

**Single field:**
- "Change my email"
- "Update my submission mode"
- "I want to change my name"

**Multiple fields:**
- "Change my name to Priya and my email to priya@example.com"
- "Update my address and delivery mode"

**Inline updates:**
- "My name is Amit" (during flow)
- "My salary is 8 lakhs" (anytime)

## Configuration

### Adjusting Agent Personality

Edit `config.py` → `SYSTEM_PROMPT`:

```python
SYSTEM_PROMPT = """You are Aria, a friendly PAN card voice assistant...

STRICT RULES:
1. No bullet points, dashes, numbered lists, or markdown
2. No URLs, email addresses, or phone numbers
3. Keep responses to 3-4 sentences maximum
4. Use contractions: "you'll", "it's", "don't"
5. Never start two replies with the same word
...
"""
```

### Changing TTS Voice

NVIDIA Magpie supports multiple voices:

```bash
# In .env file
TTS_VOICE=Magpie-Multilingual.EN-US.Aria      # Female (default)
TTS_VOICE=Magpie-Multilingual.EN-US.Michael   # Male
TTS_VOICE=Magpie-Multilingual.EN-IN.Riya      # Indian English female
```

### Adjusting Response Length

```python
# In config.py
LLM_MAX_TOKENS = 280   # Default: 4-5 sentences
LLM_MAX_TOKENS = 150   # Shorter: 2-3 sentences
LLM_MAX_TOKENS = 400   # Longer: 6-8 sentences (not recommended for voice)
```

## Troubleshooting

### "NVIDIA_API_KEY is not set"
- Create `.env` file in `voice-agent/`
- Add `NVIDIA_API_KEY=nvapi-...`
- Get key from https://build.nvidia.com

### "rank_bm25 not installed"
```bash
uv pip install rank-bm25
```

### "Could not hear speech"
- Check microphone permissions
- Speak clearly and closer to mic
- Reduce background noise
- Try adjusting `SILENCE_THRESHOLD` in `config.py`

### "pan-rag module not found"
```bash
# Ensure pan-rag is in Python path
cd ../pan-rag
uv pip install -e .
```

### Voice responses too robotic
- Lower `LLM_TEMPERATURE` for more consistent tone
- Adjust system prompt for more casual language
- Try different TTS voices

### Agent not detecting PAN application
- Check `service_flows.py` patterns
- Test with explicit phrase: "I want to apply for a PAN card"
- Review logs for fuzzy matching results

## Project Structure

```
voice-agent/
├── core/
│   ├── agent.py              # Main orchestrator (STT→Flow→LLM→TTS)
│   ├── voice_receptionist.py # Voice-optimized flow adapter
│   ├── stt.py                # Speech-to-text
│   ├── tts.py                # Text-to-speech
│   └── llm.py                # LLM client (NVIDIA NIM)
├── rag/
│   └── retriever.py          # BM25 retrieval from pan-rag chunks
├── config.py                 # Configuration & system prompt
├── server.py                 # FastAPI web server
├── main.py                   # CLI entry point
├── test_voice_flows.py       # Test suite
├── VOICE_PAN_REGISTRATION.md # Detailed documentation
└── requirements.txt          # Dependencies
```

## Performance

### Latency Breakdown

Typical response time (on decent internet):

1. **STT**: ~500-1000ms (faster-whisper local)
2. **Flow Logic**: ~10-50ms (Python receptionist)
3. **LLM Streaming**: ~800-1500ms (NVIDIA NIM)
4. **TTS**: ~300-600ms (NVIDIA Magpie)

**Total first-sentence latency**: ~1.5-2.5 seconds

Streaming reduces perceived latency - agent starts speaking while still generating the rest.

### Optimization Tips

- Use local faster-whisper for STT (no network latency)
- Keep `LLM_MAX_TOKENS` low (280 is optimal)
- Enable streaming in LLM calls
- Cache RAG results for repeated queries

## Development

### Adding New Flow Steps

1. Update `pan-rag/agent/service_flows.py` with new step
2. Add step handler in `pan-rag/agent/receptionist.py`
3. Add voice-optimized prompt in `voice_receptionist.py`:

```python
def _add_radio_choices_for_voice(self, base_text, choices, field):
    voice_prompts = {
        "new_field": "Natural voice prompt for this field?",
    }
    # ...
```

4. Test with `test_voice_flows.py`

### Debugging

Enable verbose logging:

```python
# In voice-agent/core/agent.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check session state:

```python
# In receptionist or flow_manager
print(f"[DEBUG] Current state: {flow.state}")
print(f"[DEBUG] Step: {flow.get_current_step()}")
```

## Contributing

When adding features:
1. Maintain voice-first design (no visual dependencies)
2. Keep responses under 4 sentences
3. Test with various phrasings and typos
4. Update `test_voice_flows.py` with new test cases
5. Document in `VOICE_PAN_REGISTRATION.md`

## License

[Your license here]

## Support

For issues or questions:
- Check `VOICE_PAN_REGISTRATION.md` for detailed flow documentation
- Review test output: `python test_voice_flows.py`
- Check logs in console for debug information
- Verify environment variables in `.env`
