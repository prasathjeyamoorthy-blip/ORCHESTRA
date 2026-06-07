# Tamil & Hindi Voice Testing Guide

## Quick Start

### Prerequisites
1. ✅ Pan-rag server running on port 8000
2. ✅ NVIDIA API key configured
3. ✅ Web app open in browser
4. ✅ Microphone connected and working

---

## Tamil Voice Testing (தமிழ்)

### Test 1: Basic Greeting
**Steps:**
1. Click **தமிழ்** button in UI
2. Click microphone 🎤
3. Say: **"வணக்கம்"** *(Hello)*

**Expected:**
- Transcript: "வணக்கம்"
- Response in Tamil with native voice
- Voice sounds natural, not robotic

---

### Test 2: PAN Card Query
**Steps:**
1. Ensure Tamil is selected
2. Click microphone 🎤
3. Say: **"PAN card pathi sollunga"** *(Tell me about PAN card)*

**Expected:**
- Transcript captures the question
- Response explains PAN card in Tamil
- Technical terms like "PAN" pronounced as "பான்"

---

### Test 3: Document Query
**Steps:**
1. Click microphone 🎤
2. Say: **"PAN card-ku enna documents vennum?"** *(What documents are needed for PAN card?)*

**Expected:**
- Lists documents in Tamil:
  - ஆதார் அட்டை (Aadhaar Card)
  - ஓட்டுநர் உரிமம் (Driving License)
  - புகைப்படம் (Photograph)
- Voice pronounces Tamil words correctly

---

### Test 4: Application Process
**Steps:**
1. Click microphone 🎤
2. Say: **"PAN card apply panna eppadi?"** *(How to apply for PAN card?)*

**Expected:**
- Step-by-step process in Tamil
- Clear pronunciation
- Natural flow

---

### Test 5: Fee Query
**Steps:**
1. Click microphone 🎤
2. Say: **"PAN card fee evvalavu?"** *(How much is PAN card fee?)*

**Expected:**
- Response mentions fee in Tamil
- Currency spoken as "ரூபாய்" (rupees)
- Amount clearly stated

---

## Hindi Voice Testing (हिंदी)

### Test 1: Basic Greeting
**Steps:**
1. Click **हिंदी** button in UI
2. Click microphone 🎤
3. Say: **"नमस्ते"** *(Hello)*

**Expected:**
- Transcript: "नमस्ते"
- Response in Hindi with native voice
- Voice sounds natural

---

### Test 2: PAN Card Query
**Steps:**
1. Ensure Hindi is selected
2. Click microphone 🎤
3. Say: **"PAN card ke baare mein bataiye"** *(Tell me about PAN card)*

**Expected:**
- Transcript captures the question
- Response explains PAN card in Hindi
- Technical terms like "PAN" pronounced as "पैन"

---

### Test 3: Document Query
**Steps:**
1. Click microphone 🎤
2. Say: **"PAN card ke liye kya documents chahiye?"** *(What documents are needed for PAN card?)*

**Expected:**
- Lists documents in Hindi:
  - आधार कार्ड (Aadhaar Card)
  - ड्राइविंग लाइसेंस (Driving License)
  - फोटोग्राफ (Photograph)
- Voice pronounces Hindi words correctly

---

### Test 4: Application Process
**Steps:**
1. Click microphone 🎤
2. Say: **"PAN card ke liye kaise apply karein?"** *(How to apply for PAN card?)*

**Expected:**
- Step-by-step process in Hindi
- Clear pronunciation
- Natural flow

---

### Test 5: Fee Query
**Steps:**
1. Click microphone 🎤
2. Say: **"PAN card ki fees kitni hai?"** *(What is the PAN card fee?)*

**Expected:**
- Response mentions fee in Hindi
- Currency spoken as "रुपये" (rupees)
- Amount clearly stated

---

## Mixed Language Testing

### Test 1: Tamil with English Words
**Steps:**
1. Select Tamil
2. Say: **"PAN card application process enna?"**

**Expected:**
- Understands mixed language
- Responds in Tamil
- Handles English words appropriately

---

### Test 2: Hindi with English Words
**Steps:**
1. Select Hindi
2. Say: **"PAN card application kaise complete karein?"**

**Expected:**
- Understands mixed language
- Responds in Hindi
- Handles English words appropriately

---

## Common Tamil Phrases for Testing

| Tamil Phrase | English Meaning | Use Case |
|--------------|-----------------|----------|
| வணக்கம் | Hello | Greeting |
| நன்றி | Thank you | Acknowledgment |
| ஆம் | Yes | Confirmation |
| இல்லை | No | Negation |
| உதவி வேண்டும் | Need help | Assistance |
| புரியவில்லை | Don't understand | Clarification |
| மீண்டும் சொல்லுங்கள் | Say again | Repeat |

---

## Common Hindi Phrases for Testing

| Hindi Phrase | English Meaning | Use Case |
|--------------|-----------------|----------|
| नमस्ते | Hello | Greeting |
| धन्यवाद | Thank you | Acknowledgment |
| हाँ | Yes | Confirmation |
| नहीं | No | Negation |
| मदद चाहिए | Need help | Assistance |
| समझ नहीं आया | Don't understand | Clarification |
| फिर से बोलिए | Say again | Repeat |

---

## Troubleshooting

### Tamil Not Recognized

**Problem**: System doesn't understand Tamil
**Solutions**:
1. Ensure **தமிழ்** is selected in UI
2. Speak clearly in standard Tamil
3. Avoid heavy regional dialects
4. Use complete sentences (not single words)
5. Check microphone is working

**Test Command**:
```bash
# Test Tamil TTS directly
curl -X POST http://localhost:8000/api/voice/tts \
  -F "text=வணக்கம், நான் உங்கள் PAN அட்டை உதவியாளர்" \
  -F "language=ta" \
  --output tamil_test.wav

# Play the audio
# Windows: start tamil_test.wav
# Linux: aplay tamil_test.wav
```

---

### Hindi Not Recognized

**Problem**: System doesn't understand Hindi
**Solutions**:
1. Ensure **हिंदी** is selected in UI
2. Speak clearly in standard Hindi
3. Avoid heavy regional accents
4. Use complete sentences
5. Check microphone is working

**Test Command**:
```bash
# Test Hindi TTS directly
curl -X POST http://localhost:8000/api/voice/tts \
  -F "text=नमस्ते, मैं आपका PAN कार्ड सहायक हूँ" \
  -F "language=hi" \
  --output hindi_test.wav

# Play the audio
# Windows: start hindi_test.wav
# Linux: aplay hindi_test.wav
```

---

### Voice Quality Issues

**Problem**: Voice sounds robotic or unclear
**Solutions**:
1. Check internet connection (NVIDIA NIM requires good connection)
2. Restart pan-rag server
3. Clear browser cache
4. Try different browser
5. Check server logs for TTS errors

---

### Wrong Language Detected

**Problem**: Speaks Tamil but gets English response
**Solutions**:
1. Manually select Tamil before speaking
2. Speak longer phrases (5+ words)
3. Use more Tamil words, fewer English words
4. Check language detection confidence in logs

---

## Performance Benchmarks

### Tamil Voice
- **Transcription Time**: 2-3 seconds
- **Language Detection**: 1 second
- **RAG Processing**: 2-3 seconds
- **TTS Generation**: 1-2 seconds
- **Total Response Time**: 6-9 seconds

### Hindi Voice
- **Transcription Time**: 2-3 seconds
- **Language Detection**: 1 second
- **RAG Processing**: 2-3 seconds
- **TTS Generation**: 1-2 seconds
- **Total Response Time**: 6-9 seconds

---

## Success Criteria

### Tamil Voice ✅
- [ ] Recognizes Tamil speech accurately (>90%)
- [ ] Responds in Tamil with native voice
- [ ] Pronounces Tamil words correctly
- [ ] Handles mixed Tamil-English
- [ ] Currency in Tamil (ரூபாய்)
- [ ] Technical terms translated (பான், கே வை சி)

### Hindi Voice ✅
- [ ] Recognizes Hindi speech accurately (>90%)
- [ ] Responds in Hindi with native voice
- [ ] Pronounces Hindi words correctly
- [ ] Handles mixed Hindi-English
- [ ] Currency in Hindi (रुपये)
- [ ] Technical terms translated (पैन, के वाई सी)

---

## Advanced Testing

### Test 1: Long Conversation in Tamil
1. Start with greeting: "வணக்கம்"
2. Ask about PAN: "PAN card pathi sollunga"
3. Ask about documents: "Enna documents vennum?"
4. Ask about fee: "Fee evvalavu?"
5. Confirm understanding: "Purinjudhu, nandri"

**Expected**: All interactions in Tamil, maintains context

---

### Test 2: Long Conversation in Hindi
1. Start with greeting: "नमस्ते"
2. Ask about PAN: "PAN card ke baare mein bataiye"
3. Ask about documents: "Kya documents chahiye?"
4. Ask about fee: "Fees kitni hai?"
5. Confirm understanding: "Samajh gaya, dhanyavaad"

**Expected**: All interactions in Hindi, maintains context

---

### Test 3: Language Switching
1. Start in English: "Hello"
2. Switch to Tamil: "PAN card pathi sollunga"
3. Switch to Hindi: "Documents kya chahiye?"
4. Back to English: "Thank you"

**Expected**: System adapts to each language change

---

## Reporting Issues

If you find issues:

1. **Note the language**: Tamil or Hindi
2. **What you said**: Exact phrase
3. **What happened**: Transcript and response
4. **What you expected**: Desired behavior
5. **Browser console**: Any errors
6. **Server logs**: Check for errors

**Example Issue Report**:
```
Language: Tamil
Input: "PAN card pathi sollunga"
Transcript: "pan card party sollunga" (incorrect)
Response: English response (should be Tamil)
Expected: Tamil transcript and Tamil response
Browser: Chrome 120
Error: None in console
```

---

## Quick Reference

### Tamil Voice Commands
```
வணக்கம் - Hello
PAN card pathi sollunga - Tell about PAN card
Documents enna vennum? - What documents needed?
Fee evvalavu? - How much is the fee?
Apply panna eppadi? - How to apply?
நன்றி - Thank you
```

### Hindi Voice Commands
```
नमस्ते - Hello
PAN card ke baare mein bataiye - Tell about PAN card
Documents kya chahiye? - What documents needed?
Fees kitni hai? - How much is the fee?
Kaise apply karein? - How to apply?
धन्यवाद - Thank you
```

---

## Next Steps After Testing

1. ✅ Verify all tests pass
2. ✅ Document any issues found
3. ✅ Test with real users (native speakers)
4. ✅ Collect feedback on voice quality
5. ✅ Optimize based on feedback
6. ✅ Deploy to production

---

**Happy Testing! வாழ்த்துக்கள்! शुभकामनाएं! 🎤**
