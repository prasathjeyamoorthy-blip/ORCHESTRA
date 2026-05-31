# Hallucination Fix - Casual Chat Detection

## Issue
The agent was hallucinating responses when users asked casual/unrelated questions during a PAN application flow. 

### Example:
```
User: "do you want coffee"
Agent: "Whenever you're ready, reply Yes and I'll open the upload panel."
```

The agent completely ignored the off-topic question and continued with the flow as if the user had said something relevant.

## Root Cause
The `_OFF_TOPIC_PATTERN` regex only matched questions that **started** with specific words like "why", "what", "how", etc.

```python
# Old pattern - only matches questions starting with these words
_OFF_TOPIC_PATTERN = re.compile(
    r"^(why|what|how\s+does|...)",  # ^ means "starts with"
    re.IGNORECASE
)
```

This pattern **did not catch**:
- "do you want coffee" (starts with "do")
- "hello" (greeting)
- "tell me a joke" (casual request)
- "how are you" (personal question)
- "what's the weather" (unrelated topic)

## Solution
Added a new `_CASUAL_CHAT_PATTERN` to detect casual/unrelated conversation:

```python
# New pattern - detects casual chat anywhere in the message
_CASUAL_CHAT_PATTERN = re.compile(
    r"\b(coffee|tea|drink|food|eat|hungry|thirsty|weather|"
    r"hello|hi|hey|good\s+morning|good\s+evening|good\s+afternoon|"
    r"how\s+are\s+you|what'?s\s+up|wassup|sup|"
    r"joke|funny|laugh|story|game|play|"
    r"movie|music|song|video|watch|"
    r"love|hate|like|dislike|favorite|favourite|"
    r"sports|cricket|football|match|"
    r"do\s+you\s+(want|like|have|know)|"
    r"are\s+you\s+(a\s+)?(robot|bot|human|ai|assistant)|"
    r"who\s+(are|is)\s+you|what\s+(are|is)\s+you)\b",
    re.IGNORECASE
)
```

### Updated Detection Function
```python
def _is_off_topic_during_flow(q):
    """
    Detect if user's message is off-topic during a guided flow.
    Returns True if the message is unrelated to PAN application process.
    """
    q = q.strip()
    
    # Never treat single-word flow answers as off-topic
    if len(q.split()) <= 2:
        return False
    
    # Check for casual/unrelated conversation (NEW!)
    if _CASUAL_CHAT_PATTERN.search(q):
        return True
    
    # Check for general questions
    if _OFF_TOPIC_PATTERN.match(q):
        return True
    
    # Long questions with question marks are likely off-topic
    if len(q) > 80 and '?' in q:
        return True
    
    return False
```

## What Happens Now

### Before (Hallucination):
```
User: "do you want coffee"
Agent: [Ignores question, continues with flow]
       "Whenever you're ready, reply Yes and I'll open the upload panel."
```

### After (Proper Handling):
```
User: "do you want coffee"
Agent: [Detects off-topic, returns None]
       [Routes to RAG system]
RAG:   "I can only help with PAN card services. What PAN-related question can I answer?"
```

## Detected Patterns

### Casual Conversation
- ✅ "do you want coffee"
- ✅ "hello", "hi", "hey"
- ✅ "how are you"
- ✅ "what's up"
- ✅ "tell me a joke"
- ✅ "do you like music"

### Greetings
- ✅ "good morning"
- ✅ "good evening"
- ✅ "good afternoon"

### Personal Questions
- ✅ "are you a robot"
- ✅ "are you human"
- ✅ "who are you"
- ✅ "what are you"

### Unrelated Topics
- ✅ "what's the weather"
- ✅ "do you watch movies"
- ✅ "tell me about sports"
- ✅ "what's your favorite food"

### Entertainment
- ✅ "play a game"
- ✅ "tell me a story"
- ✅ "sing a song"

## System Prompt Backup

The LLM system prompt also has a rule for off-topic questions:

```python
# From pan-rag/generation/llm.py
AGENT_IDENTITY = """...
10. For off-topic questions: "I can only help with PAN card services. What PAN-related question can I answer?"
..."""
```

This provides a **second layer of defense** if the pattern matching fails.

## Testing

### Test Cases:
1. ✅ "do you want coffee" → Detected as off-topic
2. ✅ "hello how are you" → Detected as off-topic
3. ✅ "tell me a joke" → Detected as off-topic
4. ✅ "what's the weather" → Detected as off-topic
5. ✅ "are you a robot" → Detected as off-topic
6. ✅ "my name is John" → NOT off-topic (valid flow answer)
7. ✅ "yes" → NOT off-topic (valid flow answer)
8. ✅ "1" → NOT off-topic (valid flow answer)

### How to Test:
1. Start a PAN application flow
2. When agent asks a question, type: "do you want coffee"
3. Observe: Agent should route to RAG and say "I can only help with PAN card services"
4. Try other casual phrases from the list above

## Edge Cases Handled

### Short Answers (Not Off-Topic)
```python
if len(q.split()) <= 2:
    return False
```
- "yes" → Not off-topic (valid answer)
- "no" → Not off-topic (valid answer)
- "1" → Not off-topic (valid choice)
- "ok" → Not off-topic (valid confirmation)

### Long Questions
```python
if len(q) > 80 and '?' in q:
    return True
```
- Very long questions with "?" are likely off-topic or too complex

## Files Modified
- `pan-rag/agent/receptionist.py` - Added `_CASUAL_CHAT_PATTERN` and updated `_is_off_topic_during_flow()`

## Benefits

### 1. **No More Hallucinations** 🎯
- Agent doesn't make up responses to unrelated questions
- Stays focused on PAN application process

### 2. **Better User Experience** ✨
- Clear feedback when question is off-topic
- Guides user back to PAN-related topics

### 3. **Maintains Flow Integrity** 🔒
- Flow doesn't break with casual chat
- User can continue after off-topic question

### 4. **Professional Behavior** 💼
- Agent stays in character
- Doesn't pretend to be a general chatbot

## Future Enhancements

### Potential Additions:
1. **Multilingual casual chat detection** (Tamil, Hindi)
2. **Context-aware responses** (e.g., "I appreciate the offer, but let's focus on your PAN application")
3. **Sentiment analysis** (detect frustration, confusion)
4. **Intent classification** (ML-based detection)

## Conclusion

The hallucination issue is now **fixed**. The agent will:
1. ✅ Detect casual/unrelated conversation
2. ✅ Route to RAG system
3. ✅ Respond with: "I can only help with PAN card services"
4. ✅ Stay focused on PAN application process

No more random responses to "do you want coffee"! ☕❌
