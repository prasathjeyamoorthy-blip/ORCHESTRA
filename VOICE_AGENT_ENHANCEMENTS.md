# Voice Agent Enhancements

## Overview
The voice agent has been significantly enhanced to provide natural, understandable, and efficient voice interactions with multilingual support.

## Key Improvements

### 1. **Full Voice Pipeline (`/api/voice/speak`)**
Created a complete voice interaction endpoint that handles:
- **Speech-to-Text (STT)**: Converts user's voice to text using NVIDIA NIM Whisper Large V3
- **RAG + LLM Processing**: Processes the transcript through the intelligent RAG chain
- **Text-to-Speech (TTS)**: Converts the response back to natural speech using NVIDIA NIM Magpie TTS

**Flow:**
```
User Voice → STT → Transcript → RAG Chain → Response Text → TTS → Voice Response
```

### 2. **Natural Speech Output**
Enhanced the `_clean_for_tts()` function to make voice responses sound more natural:

#### Text Cleaning Features:
- ✅ Removes markdown formatting (bold, italic, headers, code blocks)
- ✅ Removes list markers while keeping content
- ✅ Converts abbreviations to full words (e.g., → for example, i.e., → that is)
- ✅ Handles currency naturally (₹5000 → "5000 rupees")
- ✅ Spells out acronyms (PAN → "P A N", KYC → "K Y C")
- ✅ Simplifies pronunciations (Aadhaar → "Aadhar")
- ✅ Adds natural pauses for better speech flow

#### Example Transformation:
**Before:**
```
**PAN Card** application requires:
- Aadhaar Card (eKYC)
- DOB proof
- Fee: ₹110
```

**After (for TTS):**
```
P A N Card application requires Aadhar Card e K Y C, date of birth proof, Fee 110 rupees
```

### 3. **Multilingual Voice Support**
Added support for multiple languages with appropriate voice selection:

| Language | STT Language | TTS Voice | TTS Language |
|----------|-------------|-----------|--------------|
| English  | en-US       | Magpie-Multilingual.EN-US.Aria | en-US |
| Tamil    | ta-IN       | Magpie-Multilingual.EN-IN.Neerja | en-IN |
| Hindi    | hi-IN       | Magpie-Multilingual.HI-IN.Aditi | hi-IN |

**Features:**
- Automatic language detection from user's voice input
- Language-appropriate voice selection for responses
- Fallback error messages in the detected language

### 4. **Improved Speech Recognition**
The STT system now:
- ✅ Handles multiple audio formats (WebM, OGG, WAV)
- ✅ Converts to optimal 16kHz mono format for best recognition
- ✅ Provides clear error messages when speech is unclear
- ✅ Validates audio quality before processing

### 5. **Conversational Response Length**
- Voice responses speak **up to 3 sentences** (increased from 2)
- Provides better context while maintaining conversational speed
- Prevents overly long voice responses that lose user attention

### 6. **Robust Error Handling**
Enhanced error handling with:
- Graceful fallback to text-only responses if TTS fails
- Language-specific error messages
- Clear user feedback for audio quality issues
- Detailed logging for debugging

### 7. **Response Headers**
The `/voice/speak` endpoint returns:
- **Audio Stream**: WAV format audio of the response
- **X-Transcript Header**: What the user said (URL-encoded)
- **X-Reply Header**: Full text response from the agent (URL-encoded)

This allows the frontend to:
- Display both user input and bot response as text
- Play the audio response simultaneously
- Provide accessibility for users who prefer reading

## API Endpoints

### 1. `/api/voice/stt` (POST)
**Purpose**: Speech-to-Text only
**Input**: Audio file (WebM, OGG, WAV)
**Output**: JSON with transcript
```json
{
  "transcript": "What documents do I need for PAN card?"
}
```

### 2. `/api/voice/tts` (POST)
**Purpose**: Text-to-Speech only
**Input**: 
- `text` (form field): Text to synthesize
- `language` (form field, optional): Language code (en, ta, hi)
**Output**: WAV audio stream

### 3. `/api/voice/speak` (POST) ⭐ **NEW**
**Purpose**: Full voice interaction pipeline
**Input**: Audio file (user's voice)
**Output**: 
- WAV audio stream (bot's voice response)
- Headers: X-Transcript, X-Reply

**Fallback**: If TTS fails, returns JSON:
```json
{
  "transcript": "user's question",
  "reply": "bot's text response",
  "audio_available": false
}
```

## Frontend Integration

The voice agent is integrated in the chat interface via the microphone button:

### User Experience:
1. **Click microphone** → Recording starts
2. **Speak naturally** → Visual feedback with waveform
3. **Auto-stop** → Detects silence after speech (3.5s)
4. **Processing** → Shows elapsed time
5. **Response** → Plays audio + displays text bubbles

### Features:
- ✅ Real-time audio visualization
- ✅ Silence detection for auto-stop
- ✅ 30-second hard cap for safety
- ✅ Clear error messages
- ✅ Fallback to text if audio fails

## Technical Stack

### Speech-to-Text:
- **Model**: OpenAI Whisper Large V3
- **Provider**: NVIDIA NIM Cloud gRPC
- **Sample Rate**: 16kHz mono
- **Format**: LINEAR_PCM

### Text-to-Speech:
- **Model**: NVIDIA Magpie TTS Multilingual
- **Provider**: NVIDIA NIM Cloud gRPC
- **Sample Rate**: 22.05kHz
- **Format**: LINEAR_PCM → WAV

### Audio Processing:
- **Decoding**: PyAV (supports all formats)
- **Encoding**: Python wave module
- **Streaming**: FastAPI StreamingResponse

## Configuration

Required environment variables in `pan-rag/.env`:
```bash
# NVIDIA NIM API Keys
NVIDIA_API_KEY=your_nvidia_api_key
# Or separate keys:
STT_API_KEY=your_stt_key
TTS_API_KEY=your_tts_key

# Optional: Custom TTS voice
TTS_VOICE=Magpie-Multilingual.EN-US.Aria
```

## Testing the Voice Agent

### 1. Test STT Only:
```bash
curl -X POST http://localhost:8000/api/voice/stt \
  -F "audio=@test_audio.webm"
```

### 2. Test TTS Only:
```bash
curl -X POST http://localhost:8000/api/voice/tts \
  -F "text=Hello, how can I help you with your PAN card?" \
  -F "language=en" \
  --output response.wav
```

### 3. Test Full Pipeline:
Use the microphone button in the web interface or:
```bash
curl -X POST http://localhost:8000/api/voice/speak \
  -F "audio=@user_question.webm" \
  --output bot_response.wav \
  -D headers.txt
```

## Performance Optimizations

1. **Lazy Loading**: STT and TTS services are initialized only when first used
2. **Async Processing**: Uses asyncio for non-blocking TTS synthesis
3. **Efficient Audio Conversion**: PyAV handles format conversion efficiently
4. **Response Limiting**: Speaks only first 3 sentences to reduce latency
5. **Streaming Response**: Audio is streamed as it's generated

## Error Handling

### Common Errors and Solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| "Audio too short" | Recording < 1 second | Speak for at least 1 second |
| "Could not hear speech" | No speech detected | Speak clearly into microphone |
| "Microphone access denied" | Browser permission | Allow microphone in browser settings |
| "No microphone found" | No mic connected | Connect a microphone |
| "TTS failed" | TTS service issue | Returns text-only response |

## Future Enhancements

### Planned Improvements:
- [ ] Voice activity detection (VAD) for better silence detection
- [ ] Speaker diarization for multi-user conversations
- [ ] Emotion detection in voice
- [ ] Voice biometrics for authentication
- [ ] Real-time streaming TTS (instead of waiting for full response)
- [ ] Voice command shortcuts ("start application", "check status")
- [ ] Offline mode with local models

### Multilingual Expansion:
- [ ] Add more Indian languages (Bengali, Telugu, Marathi)
- [ ] Regional accent support
- [ ] Code-switching detection (mixing languages)

## Troubleshooting

### Voice not working?

1. **Check NVIDIA API keys**:
   ```bash
   cd pan-rag
   cat .env | grep NVIDIA_API_KEY
   ```

2. **Check dependencies**:
   ```bash
   pip list | grep nvidia-riva-client
   pip list | grep av
   ```

3. **Check server logs**:
   ```bash
   # Look for:
   # ✅ NVIDIA NIM STT (whisper-large-v3) connected
   # ✅ NVIDIA NIM TTS (magpie-tts-multilingual) connected
   ```

4. **Test microphone in browser**:
   - Open `frontend/public/mic-test.html`
   - Grant microphone permission
   - Verify audio is being captured

### Audio quality issues?

1. **Use a good microphone**: Built-in laptop mics may have poor quality
2. **Reduce background noise**: Find a quiet environment
3. **Speak clearly**: Enunciate words, don't speak too fast
4. **Check audio levels**: Ensure mic volume is adequate

## Summary

The enhanced voice agent now provides:
- ✅ **Natural speech output** with proper pronunciation
- ✅ **Multilingual support** for English, Tamil, and Hindi
- ✅ **Intelligent responses** through RAG + LLM integration
- ✅ **Robust error handling** with graceful fallbacks
- ✅ **Efficient processing** with optimized audio handling
- ✅ **Great user experience** with visual feedback and clear messaging

The voice agent is production-ready and provides a seamless voice interaction experience for PAN card assistance!
