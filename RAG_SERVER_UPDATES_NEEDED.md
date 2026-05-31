# RAG Server Updates for Agent Memory

## Overview
The backend now sends a `system_prompt` field to the RAG server and expects two new endpoints for AI-powered summarization and preference extraction.

## Required Changes

### 1. Accept `system_prompt` in Existing Endpoints

#### Update `/api/ask-stream` endpoint
Add `system_prompt` parameter and use it in LLM calls:

```python
@app.post("/api/ask-stream")
async def ask_stream(request: dict):
    question = request.get("question")
    session_id = request.get("session_id")
    user_id = request.get("user_id")
    user_context = request.get("user_context")
    account_email = request.get("account_email")
    system_prompt = request.get("system_prompt", "")  # NEW
    
    # Use system_prompt in LLM call
    if system_prompt:
        # Prepend system prompt to the conversation
        messages = [
            {"role": "system", "content": system_prompt},
            # ... rest of messages
        ]
    
    # Continue with existing logic...
```

#### Update `/api/ask` endpoint (fallback)
Same as above - accept and use `system_prompt`:

```python
@app.post("/api/ask")
async def ask(request: dict):
    question = request.get("question")
    session_id = request.get("session_id")
    user_id = request.get("user_id")
    user_context = request.get("user_context")
    account_email = request.get("account_email")
    system_prompt = request.get("system_prompt", "")  # NEW
    
    # Use system_prompt in LLM call
    # ... rest of logic
```

### 2. Add Summarization Endpoint

Create `/api/summarize` endpoint for AI-powered conversation summarization:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

class SummarizeRequest(BaseModel):
    prompt: str
    user_id: str

@app.post("/api/summarize")
async def summarize(request: SummarizeRequest):
    """
    Generate a rolling summary of conversation history.
    Called by backend when history exceeds 20 messages.
    """
    try:
        prompt = request.prompt
        user_id = request.user_id
        
        # Call your LLM (Claude, OpenAI, etc.)
        # Example with OpenAI:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that summarizes conversations concisely."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        summary = response.choices[0].message.content.strip()
        
        return {"summary": summary}
        
    except Exception as e:
        print(f"[summarize] Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Summarization failed")
```

### 3. Add Preference Extraction Endpoint

Create `/api/extract-preferences` endpoint for AI-powered user fact extraction:

```python
import json

class ExtractPreferencesRequest(BaseModel):
    prompt: str
    user_id: str

@app.post("/api/extract-preferences")
async def extract_preferences(request: ExtractPreferencesRequest):
    """
    Extract user facts from conversation.
    Called by backend every 5 messages.
    """
    try:
        prompt = request.prompt
        user_id = request.user_id
        
        # Call your LLM with JSON mode
        # Example with OpenAI:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that extracts user information from conversations. Always return valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"}  # Force JSON output
        )
        
        preferences_text = response.choices[0].message.content.strip()
        
        # Parse JSON to validate
        try:
            preferences = json.loads(preferences_text)
        except json.JSONDecodeError:
            # If LLM didn't return valid JSON, return empty object
            preferences = {}
        
        return {"preferences": preferences}
        
    except Exception as e:
        print(f"[extract-preferences] Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Preference extraction failed")
```

## Example Integration with Existing RAG Code

### If using Claude (Anthropic)

```python
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

@app.post("/api/summarize")
async def summarize(request: SummarizeRequest):
    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            temperature=0.3,
            messages=[
                {
                    "role": "user",
                    "content": request.prompt
                }
            ]
        )
        
        summary = message.content[0].text
        return {"summary": summary}
        
    except Exception as e:
        print(f"[summarize] Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Summarization failed")

@app.post("/api/extract-preferences")
async def extract_preferences(request: ExtractPreferencesRequest):
    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            temperature=0.1,
            messages=[
                {
                    "role": "user",
                    "content": request.prompt
                }
            ]
        )
        
        preferences_text = message.content[0].text
        
        # Try to parse JSON
        try:
            # Extract JSON from markdown code blocks if present
            if "```json" in preferences_text:
                json_start = preferences_text.find("```json") + 7
                json_end = preferences_text.find("```", json_start)
                preferences_text = preferences_text[json_start:json_end].strip()
            elif "```" in preferences_text:
                json_start = preferences_text.find("```") + 3
                json_end = preferences_text.find("```", json_start)
                preferences_text = preferences_text[json_start:json_end].strip()
            
            preferences = json.loads(preferences_text)
        except:
            preferences = {}
        
        return {"preferences": preferences}
        
    except Exception as e:
        print(f"[extract-preferences] Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Preference extraction failed")
```

### If using OpenAI

```python
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.post("/api/summarize")
async def summarize(request: SummarizeRequest):
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that summarizes conversations concisely."
                },
                {
                    "role": "user",
                    "content": request.prompt
                }
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        summary = response.choices[0].message.content.strip()
        return {"summary": summary}
        
    except Exception as e:
        print(f"[summarize] Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Summarization failed")

@app.post("/api/extract-preferences")
async def extract_preferences(request: ExtractPreferencesRequest):
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that extracts user information. Always return valid JSON."
                },
                {
                    "role": "user",
                    "content": request.prompt
                }
            ],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        
        preferences_text = response.choices[0].message.content.strip()
        preferences = json.loads(preferences_text)
        
        return {"preferences": preferences}
        
    except Exception as e:
        print(f"[extract-preferences] Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Preference extraction failed")
```

## Testing the New Endpoints

### Test Summarization
```bash
curl -X POST http://localhost:8000/api/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Summarize this conversation in 3-5 sentences focusing on what the user asked, what was resolved, and any important details like PAN number, name, or issues.\n\nConversation:\nUser: I want to apply for PAN\nAssistant: Sure! Let me help you with that...\nUser: My name is Rajesh Kumar\nAssistant: Great, I have noted your name...",
    "user_id": "test-user-123"
  }'
```

Expected response:
```json
{
  "summary": "The user wants to apply for a PAN card. Their name is Rajesh Kumar. The assistant is helping them through the application process."
}
```

### Test Preference Extraction
```bash
curl -X POST http://localhost:8000/api/extract-preferences \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "From this conversation extract any user facts worth remembering. Return ONLY a JSON object with these fields: {name, pan, city, aadhaarLinked, commonIssues, preferredLanguage}. Use empty string for unknown fields. Merge with existing: {}\n\nConversation:\nUser: My name is Rajesh Kumar\nAssistant: Great!\nUser: I live in Mumbai\nAssistant: Noted.",
    "user_id": "test-user-123"
  }'
```

Expected response:
```json
{
  "preferences": {
    "name": "Rajesh Kumar",
    "pan": "",
    "city": "Mumbai",
    "aadhaarLinked": "",
    "commonIssues": "",
    "preferredLanguage": ""
  }
}
```

## Optional: Use system_prompt in RAG

If you want the RAG to use the agent memory context, update your LLM calls:

```python
# In your existing ask-stream or ask endpoint
def build_llm_messages(question, user_context, system_prompt=None):
    messages = []
    
    # Add system prompt if provided
    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt
        })
    
    # Add user context
    if user_context:
        messages.append({
            "role": "system",
            "content": f"User context:\n{user_context}"
        })
    
    # Add user question
    messages.append({
        "role": "user",
        "content": question
    })
    
    return messages
```

## Backward Compatibility

All changes are backward compatible:
- If `system_prompt` is not provided, RAG works as before
- If summarization/extraction endpoints don't exist, backend silently skips them
- No breaking changes to existing functionality

## Deployment Checklist

- [ ] Add `system_prompt` parameter to `/api/ask-stream`
- [ ] Add `system_prompt` parameter to `/api/ask`
- [ ] Create `/api/summarize` endpoint
- [ ] Create `/api/extract-preferences` endpoint
- [ ] Test all endpoints with cURL
- [ ] Restart RAG server
- [ ] Test end-to-end with backend
- [ ] Monitor logs for errors

## File to Modify
- `pan-rag/api/routes.py` (or wherever your RAG endpoints are defined)
- `pan-rag/generation/chain.py` (if LLM calls are there)

## Dependencies
No new dependencies required if you already have:
- `anthropic` (for Claude)
- `openai` (for OpenAI)
- `fastapi` (for endpoints)
- `pydantic` (for request models)

## Status
⚠️ **PENDING** - RAG server needs these updates for full functionality
✅ Backend is ready and will gracefully degrade if endpoints don't exist
