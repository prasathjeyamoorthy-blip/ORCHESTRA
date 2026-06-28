# llm.py - Language Model Integration

## Purpose
Integrates with large language models for natural language understanding, intent extraction, and response generation. Handles semantic processing of voice inputs.

## Key Functions

### extract_intent(user_input, context)
Extract user intent from natural language input.
- **Input**: User text, optional conversation context
- **Output**: Intent classification with confidence
- **Returns**: 
  ```python
  {
    "intent": "upload_document",
    "confidence": 0.95,
    "entities": {"document_type": "aadhaar"},
    "parameters": {...}
  }
  ```

### generate_response(intent, context, data)
Generate contextual response for user.
- **Input**: Detected intent, conversation context, extracted data
- **Output**: Natural language response text
- **Features**: Context-aware, personalized, helpful

### extract_entities(text, entity_types)
Extract structured information from text.
- **Entities**: Numbers, dates, names, locations
- **Returns**: Extracted entities with confidence

### validate_user_input(text, expected_format)
Validate if input matches expected format.
- **Checks**: Required fields, data type, value range
- **Returns**: Validation result with feedback

## Intent Categories

### Document Operations
- `upload_document` - User wants to upload
- `view_extracted_data` - Request to see data
- `edit_extracted_data` - Modify extracted fields
- `delete_document` - Remove document

### Status & Information
- `check_status` - Ask for application status
- `get_help` - Request assistance
- `provide_feedback` - Share feedback
- `contact_support` - Reach support team

### Application Management
- `start_application` - Begin new application
- `submit_application` - Submit for verification
- `cancel_application` - Cancel application
- `resume_application` - Resume saved application

## LLM Configuration

### Supported Models
- OpenAI GPT-4 / GPT-3.5
- Google PaLM / Gemini
- Open source models (Llama, Mistral)
- Domain-specific fine-tuned models

### Model Parameters
```python
model_config = {
    "model": "gpt-4",
    "temperature": 0.3,  # Lower = more deterministic
    "max_tokens": 150,
    "top_p": 0.9,
    "frequency_penalty": 0.5,
    "presence_penalty": 0.0
}
```

## Prompt Engineering

### System Prompts
```
You are a helpful voice assistant for a PAN application system.
You understand Indian languages and cultural context.
Always be concise, clear, and helpful.
Confirm important actions before proceeding.
```

### Few-Shot Examples
```
User: "Upload my ID"
Intent: upload_document
Entities: {document_type: "id"}

User: "Where's my application?"
Intent: check_status
```

## Entity Extraction

### Supported Entities
- **DOCUMENT_TYPE**: aadhaar, pan, passport, etc.
- **ACTION**: upload, delete, modify, view
- **NUMBER**: 10-digit number, etc.
- **DATE**: various date formats
- **NAME**: person names
- **LOCATION**: states, cities, addresses

## Context Handling

### Conversation Memory
```python
context = {
    "user_id": "123",
    "conversation_history": [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ],
    "extracted_data": {},
    "current_document": "aadhaar"
}
```

### Context Persistence
- Store recent conversation turns
- Remember user preferences
- Maintain extracted information
- Track application progress

## Response Generation

### Template Variables
```
Response: "Your {document_type} has been {status}."
Variables: {
  "document_type": "Aadhaar",
  "status": "extracted successfully"
}
```

### Conditional Logic
```python
if intent == "upload_document":
    if context.get("active_document"):
        response = "Your previous upload is still pending. Proceed?"
    else:
        response = "Ready for upload. What document?"
```

## Error Handling

### Intent Disambiguation
- Low confidence: Ask for clarification
- Ambiguous intent: Present options
- Out of domain: Escalate to support

### Fallback Strategies
```python
if intent_confidence < threshold:
    # Present options
    options = ["Upload document", "Check status", "Get help"]
    response = "I'm not sure. Did you want to:\n" + "\n".join(options)
```

## Integration

### With Agent
```python
from core.llm import LanguageModel
from core.agent import VoiceAgent

llm = LanguageModel()
agent = VoiceAgent()

transcript = "I want to upload my Aadhaar"
intent_result = llm.extract_intent(transcript)
agent.execute_action(intent_result)
```

### With Voice Service
```python
user_audio → STT → transcript → LLM → intent → Agent → Response → TTS → audio
```

## Configuration

### Environment Variables
```
LLM_API_KEY=your_api_key
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=150
```

## Performance

### Latency
- Intent extraction: 100-500ms
- Entity extraction: 50-200ms
- Response generation: 200-1000ms

### Accuracy
- Intent classification: 95%+
- Entity extraction: 90%+
- Response relevance: 92%+

## Domain Adaptation

### Fine-Tuning
- Train on PAN application domain
- Add application-specific intents
- Learn user behavior patterns
- Improve accuracy over time

### Custom Vocabulary
```python
custom_entities = {
    "aadhaar_number": r"\d{12}",
    "mobile_number": r"[6-9]\d{9}",
    "pan_number": r"[A-Z]{5}[0-9]{4}[A-Z]"
}
```

## Monitoring

### Metrics
- Intent classification accuracy
- Entity extraction precision
- Response satisfaction score
- Error rate by intent type

### Logging
```python
log_entry = {
    "timestamp": now(),
    "user_id": user_id,
    "input": transcript,
    "intent": intent,
    "confidence": confidence,
    "entities": entities,
    "response": response
}
```

## Best Practices

### Prompt Design
- Be specific and clear
- Provide context
- Include examples
- Specify output format

### Error Handling
- Graceful fallbacks
- User-friendly messages
- Offer alternatives
- Escalate when needed

### Performance
- Cache common intents
- Batch API calls
- Implement timeouts
- Monitor token usage

## Future Enhancements

- [ ] Multi-turn reasoning
- [ ] Contextual disambiguation
- [ ] Sentiment analysis
- [ ] User preference learning
- [ ] Domain expert integration
- [ ] Real-time confidence feedback

## Dependencies
- `openai` - OpenAI API client
- `langchain` - LLM framework
- `google-generativeai` - Google Gemini
- `together` - Open source models

## Notes
- Temperature affects response creativity
- Token limits impact response length
- Costs scale with API usage
- Fine-tuning improves domain accuracy
- Caching reduces API calls
