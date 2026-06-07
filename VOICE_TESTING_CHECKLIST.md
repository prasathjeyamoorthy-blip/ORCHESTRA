# Voice Agent Testing Checklist

## Pre-Testing Setup

### 1. Restart the pan-rag Server
```bash
# Find and stop the current uvicorn process
# Process ID: 34052 (from earlier check)

# On Windows:
taskkill /PID 34052 /F

# Then restart:
cd e:\PAN_APP\pan-rag
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 2. Verify Server Startup
Look for these messages in the console:
- ✅ `NVIDIA NIM STT (whisper-large-v3) connected`
- ✅ `NVIDIA NIM TTS (magpie-tts-multilingual) connected`
- ✅ `RAG chain ready`

---

## Testing Scenarios

### Test 1: Basic English Voice Interaction ✅

**Steps:**
1. Open the web app in browser
2. Ensure language is set to **EN** (English)
3. Click the microphone button 🎤
4. Say: **"What is a PAN card?"**
5. Wait for the recording to stop (auto-detects silence)
6. Observe the processing indicator

**Expected Results:**
- ✅ User's text appears in chat: "What is a PAN card?"
- ✅ Bot's text response appears
- ✅ Voice response plays automatically
- ✅ Voice sounds natural (acronyms spelled: "P A N")
- ✅ No robotic or choppy audio

---

### Test 2: Document Query ✅

**Steps:**
1. Click microphone 🎤
2. Say: **"What documents do I need for PAN card application?"**
3. Wait for response

**Expected Results:**
- ✅ Transcript appears correctly
- ✅ Bot lists documents (Aadhaar, Driving License, Photograph)
- ✅ Voice pronounces "Aadhar" (not "Aadhaar")
- ✅ Voice spells "P A N", "K Y C"
- ✅ Response is clear and understandable

---

### Test 3: Tamil Language Voice ✅

**Steps:**
1. Switch language to **தமிழ்** (Tamil)
2. Click microphone 🎤
3. Say in Tamil: **"PAN card-ku enna documents vennum?"**
4. Wait for response

**Expected Results:**
- ✅ Transcript appears (may be in Tamil or English)
- ✅ Response text in Tamil
- ✅ Voice uses Indian English accent (Neerja voice)
- ✅ Documents section shows Tamil labels

---

### Test 4: Hindi Language Voice ✅

**Steps:**
1. Switch language to **हिंदी** (Hindi)
2. Click microphone 🎤
3. Say in Hindi: **"PAN card ke liye kya documents chahiye?"**
4. Wait for response

**Expected Results:**
- ✅ Transcript appears
- ✅ Response text in Hindi
- ✅ Voice uses Hindi voice (Aditi)
- ✅ Natural pronunciation

---

### Test 5: Complex Query ✅

**Steps:**
1. Switch back to English
2. Click microphone 🎤
3. Say: **"I want to apply for a new PAN card. My name is John Doe and my annual income is 5 lakh rupees."**
4. Wait for response

**Expected Results:**
- ✅ Full transcript captured
- ✅ Bot starts guided flow
- ✅ Voice response guides user through next steps
- ✅ Currency mentioned naturally ("5 lakh rupees")

---

### Test 6: Error Handling - No Speech ✅

**Steps:**
1. Click microphone 🎤
2. Don't say anything (stay silent)
3. Wait for auto-stop

**Expected Results:**
- ✅ Error message: "Could not hear speech — please speak clearly and try again"
- ✅ No crash or hang
- ✅ Can try again immediately

---

### Test 7: Error Handling - Very Short Audio ✅

**Steps:**
1. Click microphone 🎤
2. Say just "Hi" very quickly
3. Wait for response

**Expected Results:**
- ✅ Either processes successfully OR
- ✅ Shows error: "Audio too short — please speak for at least 1 second"
- ✅ Can retry

---

### Test 8: Background Noise Handling ✅

**Steps:**
1. Play some background music or noise
2. Click microphone 🎤
3. Speak clearly: **"What is the PAN card fee?"**
4. Wait for response

**Expected Results:**
- ✅ Transcript may have some errors but captures main words
- ✅ Bot responds appropriately
- ✅ Voice output is clear
- ✅ System handles imperfect input gracefully

---

### Test 9: Long Response Handling ✅

**Steps:**
1. Click microphone 🎤
2. Say: **"Tell me everything about PAN card application process"**
3. Wait for response

**Expected Results:**
- ✅ Bot provides comprehensive text response
- ✅ Voice speaks only first 3 sentences (not entire response)
- ✅ User can read full response in text
- ✅ Voice doesn't go on too long

---

### Test 10: Fallback to Text ✅

**Steps:**
1. This tests automatic fallback if TTS fails
2. Click microphone 🎤
3. Say any question
4. If TTS service is unavailable, should see:

**Expected Results:**
- ✅ Transcript appears
- ✅ Text response appears
- ✅ No audio plays (graceful degradation)
- ✅ User can still interact via text

---

## Visual Feedback Tests

### Test 11: Recording Indicator ✅

**Steps:**
1. Click microphone 🎤
2. Observe the UI while speaking

**Expected Results:**
- ✅ Microphone button shows recording state (red/pulsing)
- ✅ Waveform visualization appears
- ✅ Timer shows elapsed time
- ✅ Visual feedback is smooth

---

### Test 12: Processing Indicator ✅

**Steps:**
1. After speaking, observe processing phase

**Expected Results:**
- ✅ Loading indicator appears
- ✅ Shows "Processing..." or similar message
- ✅ Elapsed time counter
- ✅ User knows system is working

---

## Browser Compatibility Tests

### Test 13: Chrome ✅
- Test all basic scenarios in Chrome
- Verify microphone permissions work

### Test 14: Firefox ✅
- Test in Firefox
- Verify audio format compatibility

### Test 15: Edge ✅
- Test in Edge
- Verify all features work

---

## Performance Tests

### Test 16: Response Time ✅

**Measure:**
- Time from stop speaking to hearing response
- Should be < 5 seconds for simple queries

### Test 17: Multiple Interactions ✅

**Steps:**
1. Use voice 5 times in a row
2. Check for memory leaks or slowdowns

**Expected Results:**
- ✅ Each interaction works smoothly
- ✅ No degradation in performance
- ✅ No audio artifacts

---

## Edge Cases

### Test 18: Interruption ✅

**Steps:**
1. Start recording
2. Close the modal or navigate away
3. Return and try again

**Expected Results:**
- ✅ Recording stops cleanly
- ✅ No errors
- ✅ Can start new recording

### Test 19: Network Issues ✅

**Steps:**
1. Simulate slow network (browser dev tools)
2. Try voice interaction

**Expected Results:**
- ✅ Shows appropriate loading state
- ✅ Eventually completes or times out gracefully
- ✅ Clear error message if fails

### Test 20: Concurrent Users ✅

**Steps:**
1. Open app in 2 different browsers
2. Use voice in both simultaneously

**Expected Results:**
- ✅ Both work independently
- ✅ No cross-talk or interference
- ✅ Each gets correct response

---

## Accessibility Tests

### Test 21: Keyboard Navigation ✅

**Steps:**
1. Use Tab key to navigate to microphone button
2. Press Enter to activate
3. Speak and test

**Expected Results:**
- ✅ Can activate via keyboard
- ✅ Focus indicators visible
- ✅ Accessible to keyboard-only users

### Test 22: Screen Reader ✅

**Steps:**
1. Enable screen reader (NVDA/JAWS)
2. Navigate to microphone button
3. Activate and use

**Expected Results:**
- ✅ Button is announced properly
- ✅ Status changes are announced
- ✅ Transcript and response are readable

---

## Sign-Off Checklist

After completing all tests, verify:

- [ ] All 22 tests passed
- [ ] No console errors
- [ ] Voice quality is good
- [ ] Response accuracy is high
- [ ] Error handling works
- [ ] All languages work
- [ ] Performance is acceptable
- [ ] UI feedback is clear
- [ ] Accessibility is maintained
- [ ] Documentation is complete

---

## Known Limitations

1. **Voice sessions are stateless**: Each voice interaction is independent (no conversation history)
2. **3-sentence limit**: Voice speaks max 3 sentences (full text available in chat)
3. **English-only TTS for Tamil**: Tamil responses use Indian English voice (not native Tamil TTS)
4. **Network dependent**: Requires internet for NVIDIA NIM services
5. **Microphone required**: No fallback for devices without mic

---

## Reporting Issues

If you find issues during testing:

1. **Note the test number** (e.g., "Test 3 failed")
2. **Describe what happened** vs. what was expected
3. **Check browser console** for errors
4. **Check server logs** for backend errors
5. **Note your environment**:
   - Browser and version
   - Operating system
   - Microphone type
   - Network conditions

---

## Success Criteria

Voice agent is ready for production when:

✅ All basic tests (1-10) pass
✅ At least 2 browsers tested successfully
✅ All 3 languages work
✅ Error handling is graceful
✅ Performance is acceptable (< 5s response time)
✅ No critical bugs found

---

**Happy Testing! 🎤🤖**
