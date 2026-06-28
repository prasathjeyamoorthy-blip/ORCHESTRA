# PAN RAG - Document Retrieval & Question Answering

Retrieval-Augmented Generation (RAG) system for document-based question answering and information retrieval.

## Overview

PAN RAG provides:
- Document indexing and retrieval
- Question-answering over documents
- Context-aware information extraction
- Multi-document search
- Answer synthesis with source attribution

## Project Structure

```
pan-rag/
├── agent/                      # Core RAG agent
│   ├── receptionist.py         # User interface layer
│   ├── retriever.py            # Document retrieval
│   ├── generator.py            # Answer generation
│   └── chain.py                # RAG chain orchestration
├── api/                        # API endpoints
│   ├── routes.py               # API routes
│   ├── voice.py                # Voice interface
│   └── middleware/
├── data/                       # Documents and data
├── utils/                      # Utility functions
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Features

- **Document Indexing**: Index documents for fast retrieval
- **Semantic Search**: Find relevant documents by meaning
- **Question Answering**: Answer questions from documents
- **Multi-hop Queries**: Handle complex multi-step questions
- **Source Attribution**: Show which documents answer came from
- **Voice Interface**: Ask questions by voice
- **Context Window**: Maintain conversation context

## Installation

```bash
cd pan-rag
pip install -r requirements.txt
```

## API Endpoints

### Ask Question

```
POST /api/ask
Content-Type: application/json

{
  "question": "What documents do I need for PAN application?",
  "auth_id": "user-123",
  "context": []  # Optional: conversation history
}

Response:
{
  "answer": "For PAN application you need...",
  "sources": [
    {
      "document": "PAN_Requirements.pdf",
      "page": 2,
      "excerpt": "..."
    }
  ],
  "confidence": 0.92
}
```

### Upload Document

```
POST /api/documents/upload
Content-Type: multipart/form-data

Parameters:
- document: File to index
- title: Document title
- category: Document category

Response:
{
  "status": "success",
  "document_id": "doc-123",
  "indexed_at": "2024-01-15T10:30:00Z"
}
```

### Search Documents

```
POST /api/documents/search
Content-Type: application/json

{
  "query": "Aadhaar requirement",
  "top_k": 5
}

Response:
{
  "results": [
    {
      "document_id": "doc-123",
      "title": "Document Title",
      "relevance_score": 0.95,
      "excerpt": "..."
    }
  ]
}
```

## Configuration

### Environment Variables

```
OPENAI_API_KEY=your_api_key
PINECONE_API_KEY=your_api_key
PINECONE_ENVIRONMENT=your_environment
INDEX_NAME=pan-documents
```

## Usage

### Basic Question Answering

```python
from agent.chain import RAGChain

chain = RAGChain()

# Ask a question
response = chain.ask(
    question="What is needed for PAN verification?",
    top_k=3  # Use top 3 most relevant documents
)

print(response["answer"])
for source in response["sources"]:
    print(f"From: {source['document']}")
```

### Multi-Document Search

```python
from agent.retriever import DocumentRetriever

retriever = DocumentRetriever()

# Search across documents
results = retriever.search(
    query="Aadhaar card requirements",
    top_k=5,
    filters={"category": "identification"}
)

for result in results:
    print(f"{result['title']} - {result['relevance_score']}")
```

### Voice Interface

```python
from api.voice import VoiceInterface

voice = VoiceInterface()

# Process voice input
response = voice.process_audio(
    audio_bytes=audio_data,
    language="en-IN"
)

print(response["answer"])
voice.speak(response["answer"])
```

## Components

### RAGChain
Orchestrates the retrieval and generation pipeline.

**Methods:**
- `ask(question, top_k)` - Answer a question
- `set_context(messages)` - Set conversation context
- `add_document(doc)` - Index a new document
- `search(query)` - Search for relevant documents

### DocumentRetriever
Manages document indexing and retrieval.

**Methods:**
- `index(document)` - Index a document
- `search(query, top_k)` - Find relevant documents
- `remove(doc_id)` - Remove document from index

### AnswerGenerator
Generates answers from retrieved documents.

**Methods:**
- `generate(question, documents)` - Generate answer
- `synthesize(sources)` - Combine information from multiple sources

### Receptionist
User-facing interface for the RAG system.

**Methods:**
- `handle_question(question)` - Process user question
- `clarify_intent(question)` - Understand user intent
- `suggest_follow_up()` - Suggest related questions

## Data Flow

```
User Question
    ↓
Intent Recognition
    ↓
Document Retrieval
    ↓
Context Assembly
    ↓
Answer Generation
    ↓
Source Attribution
    ↓
Response to User
```

## Supported Document Formats

- PDF
- TXT
- DOCX
- Markdown
- Web pages (HTML)

## Performance

- Average retrieval time: < 500ms
- Answer generation: 1-2 seconds
- Document indexing: 5-10 seconds per document

## Extending RAG

### Add Custom Document Type

1. Create parser in `utils/parsers/`
2. Add to `DocumentRetriever`
3. Test with sample documents

### Add Knowledge Base

1. Prepare documents
2. Use `/api/documents/upload` endpoint
3. Documents automatically indexed

### Custom Prompts

Edit prompts in `agent/generator.py` to customize answer style.

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Low retrieval accuracy | Poor document quality | Improve document indexing |
| Slow responses | Large document set | Use filters, increase relevance threshold |
| Missing information | Not indexed | Upload more relevant documents |
| Wrong answer format | Generator prompt issue | Adjust prompt template |

## Integration with Backend

```python
from pan_rag.agent.chain import RAGChain

# In Flask route
@app.route('/api/ask', methods=['POST'])
def ask_question():
    data = request.get_json()
    chain = RAGChain()
    
    response = chain.ask(
        question=data['question'],
        top_k=5
    )
    
    return jsonify(response)
```

## Best Practices

1. **Document Preparation**: Clean and structure documents well
2. **Index Management**: Regular index maintenance and updates
3. **Query Optimization**: Use specific, clear questions
4. **Source Verification**: Always verify generated answers against sources
5. **Feedback Loop**: Collect user feedback to improve responses

## Future Enhancements

- [ ] Multi-language support
- [ ] Custom knowledge graphs
- [ ] Real-time document updates
- [ ] Advanced filtering options
- [ ] Document versioning
- [ ] Analytics dashboard

## License

Proprietary and confidential.

## Support

For issues or questions, contact the development team.
