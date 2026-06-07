# Voice Agent Quick Start

## Installation (2 minutes)

```bash
cd voice-agent

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "NVIDIA_API_KEY=nvapi-YOUR-KEY-HERE" > .env
```

## Run Voice Agent

### CLI Mode (Talk to Mic)
```bash
python main.py
```

Say: **"I want to apply for a PAN card"**

### Server Mode (API)
```bash
uvicorn server:app --port 8002
```

Test:
```bash
curl -X POST http://localhost:8002/api/voice/speak \
  -F "audio=@recording.webm" \
  --output response.wav
```

## The Complete Flow

User says → **"I want to apply for PAN"**

### 1. Application Details (8 questions)
1. **Applicant type** → "Indian citizen"
2. **Submission mode** → "Aadhaar online"
3. **Delivery mode** → "Physical and email"
4. **Aadhaar photo** → "Yes"
5. **Income sources** → "Salary"
6. **Communication address** → "Residence"
7. **Residential status** → "Resident"
8. **Representative** → "No"

### 2. Personal Details (4 questions)
1. **Full name** → "Rajesh Kumar"
2. **Mother's name** → "Lakshmi"
3. **Email** → "rajesh@example.com"
4. **Annual income** → "6 lakhs"

### 3. Confirmation
- Shows summary
- Say **"Yes"** to proceed
- Or say **"Change my email"** to update

### 4. Documents
- Lists required docs
- Ready to upload

**Total time: ~1.5-2 minutes**

## Voice Prompts (Speed Optimized)

| Question | Agent Says |
|----------|------------|
| Applicant Type | "Are you an Indian citizen, company or HUF, or foreign citizen?" |
| Submission | "Choose Aadhaar online, upload and e-sign, or fill and courier." |
| Delivery | "Physical card plus email, or email only?" |
| Aadhaar Photo | "Use your Aadhaar photo on the PAN card? Yes or no." |
| Income | "Pick your income sources. Salary, business, house property, other sources, capital gains, or no income." |
| Address | "Send mail to residence, office, or representative address?" |
| Status | "Are you resident, non-resident, or resident but not ordinarily resident?" |
| Representative | "Appointing a representative? Yes or no." |
| Full Name | "Your full name as on Aadhaar?" |
| Mother's Name | "Mother's name?" |
| Email | "Your email address?" |
| Income | "Your annual income?" |

## Updating Fields

### During Flow
- **"Change my email"** → Updates email
- **"Change my name and salary"** → Updates both

### At Confirmation
- **"Change submission mode"** → Updates mode
- **"My email is new@example.com"** → Updates directly

## Natural Inputs

### Yes/No
- Yes: "yes", "yeah", "yep", "sure", "okay"
- No: "no", "nope", "nah"

### Choices
- Say option name: "Aadhaar online"
- Or be casual: "upload and e-sign"

### Salary (flexible)
- "6 lakhs" ✅
- "6 LPA" ✅
- "600000" ✅
- "6 lakh" ✅

### Typos (handled)
- "I wnat to aply for oan" ✅
- "appply for pann" ✅

## Testing

```bash
# Full test suite
python test_voice_flows.py

# Individual tests available:
# - Full application flow
# - Field updates
# - Multi-field updates
# - Typo handling
# - Natural variations
```

## Configuration

**File:** `config.py`

### Speed Settings
```python
LLM_MAX_TOKENS = 150      # Response length
LLM_TEMPERATURE = 0.75    # Variation
```

### Faster (less natural)
```python
LLM_MAX_TOKENS = 100
LLM_TEMPERATURE = 0.5
```

### Slower (more natural)
```python
LLM_MAX_TOKENS = 200
LLM_TEMPERATURE = 0.9
```

## API Integration

### Frontend Example
```javascript
// Record audio
const mediaRecorder = new MediaRecorder(stream);

// Send to voice agent
const formData = new FormData();
formData.append('audio', audioBlob);
formData.append('user_id', userId);
formData.append('session_id', sessionId);

const res = await fetch('http://localhost:8002/api/voice/speak', {
  method: 'POST',
  body: formData
});

// Get transcript and reply
const transcript = res.headers.get('X-Transcript');
const reply = res.headers.get('X-Reply');
const sessionId = res.headers.get('X-Session-Id');

// Play response
const audio = await res.blob();
new Audio(URL.createObjectURL(audio)).play();
```

## Troubleshooting

### "NVIDIA_API_KEY not set"
Create `.env` file with your key:
```bash
echo "NVIDIA_API_KEY=nvapi-YOUR-KEY" > .env
```

### "Could not hear speech"
- Speak louder
- Move closer to mic
- Reduce background noise

### "pan-rag module not found"
```bash
cd ../pan-rag
pip install -e .
```

### Responses too slow
Reduce tokens in `config.py`:
```python
LLM_MAX_TOKENS = 100
```

### Responses too brief
Increase tokens:
```python
LLM_MAX_TOKENS = 200
```

## File Structure

```
voice-agent/
├── core/
│   ├── agent.py              # Main orchestrator
│   ├── voice_receptionist.py # Voice flow adapter
│   ├── stt.py                # Speech-to-text
│   ├── tts.py                # Text-to-speech
│   └── llm.py                # LLM client
├── config.py                 # All settings here
├── server.py                 # API server
├── main.py                   # CLI entry
└── test_voice_flows.py       # Test suite
```

## Performance

| Metric | Value |
|--------|-------|
| Per question | 1.5-2.5s |
| Application details | ~1 minute |
| Personal details | ~30 seconds |
| Confirmation | ~15 seconds |
| **Total flow** | **~1.5-2 min** |

## Next Steps

1. **Test CLI**: `python main.py`
2. **Test API**: `uvicorn server:app --port 8002`
3. **Run tests**: `python test_voice_flows.py`
4. **Integrate**: Use API endpoints in your frontend

## Documentation

- `README.md` - Full setup guide
- `VOICE_PAN_REGISTRATION.md` - Complete flow documentation
- `VOICE_FLOW_OPTIMIZED.md` - Speed optimization details
- `QUICK_START.md` - This file

## Support

Check logs for debug info:
```bash
python main.py 2>&1 | tee voice_agent.log
```

All ready! Start with `python main.py` and say "I want to apply for PAN" 🎤
