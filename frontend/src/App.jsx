import { useState, useRef, useEffect } from 'react'
import './App.css'

const API_BASE = '/api'

function TypingDots() {
  return (
    <div className="typing-dots">
      <span /><span /><span />
    </div>
  )
}

// Simple markdown renderer — handles bold, bullets, numbered lists
function renderMarkdown(text) {
  const lines = text.split('\n')
  const elements = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    if (/^#{1,3}\s/.test(line)) {
      const content = line.replace(/^#{1,3}\s/, '')
      elements.push(
        <p key={i} style={{ fontWeight: 500, marginBottom: 6 }}>
          {renderInline(content)}
        </p>
      )
    } else if (/^(\d+)\.\s/.test(line)) {
      const items = []
      while (i < lines.length && /^(\d+)\.\s/.test(lines[i])) {
        items.push(<li key={i}>{renderInline(lines[i].replace(/^\d+\.\s/, ''))}</li>)
        i++
      }
      elements.push(<ol key={`ol-${i}`} style={{ paddingLeft: 20, marginBottom: 8 }}>{items}</ol>)
      continue
    } else if (/^[-•]\s/.test(line)) {
      const items = []
      while (i < lines.length && /^[-•]\s/.test(lines[i])) {
        items.push(<li key={i}>{renderInline(lines[i].replace(/^[-•]\s/, ''))}</li>)
        i++
      }
      elements.push(<ul key={`ul-${i}`} style={{ paddingLeft: 20, marginBottom: 8 }}>{items}</ul>)
      continue
    } else if (line.trim() === '') {
      elements.push(<br key={i} />)
    } else {
      elements.push(
        <p key={i} style={{ marginBottom: 4, lineHeight: 1.6 }}>
          {renderInline(line)}
        </p>
      )
    }
    i++
  }
  return elements
}

function renderInline(text) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>
    }
    return part
  })
}

function Message({ msg, onFollowup }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`msg-row ${isUser ? 'user' : 'bot'}`}>
      {!isUser && <div className="avatar bot-avatar" aria-hidden="true">🤖</div>}
      <div className={`bubble ${isUser ? 'user-bubble' : 'bot-bubble'}`}>

        {isUser
          ? <p className="bubble-text">{msg.content}</p>
          : <div className="bubble-text">{renderMarkdown(msg.content)}</div>
        }

        {msg.sources?.length > 0 && (
          <div className="sources">
            <span className="sources-label">Sources</span>
            {msg.sources.map((s, i) => (
              <a key={i} href={s.url} target="_blank" rel="noreferrer" className="source-link">
                {s.title}
              </a>
            ))}
          </div>
        )}

        {msg.followups?.length > 0 && (
          <div className="followups">
            {msg.followups.map((q, i) => (
              <button key={i} className="followup-btn" onClick={() => onFollowup(q)}>
                {q}
              </button>
            ))}
          </div>
        )}
      </div>
      {isUser && <div className="avatar user-avatar" aria-hidden="true">👤</div>}
    </div>
  )
}

export default function App() {
  const [messages, setMessages] = useState([{
    id: 0,
    role: 'bot',
    content: "Hi! I'm your PAN card assistant. Ask me anything about PAN applications, Aadhaar linking, TAN, or related services.",
    sources: [],
    followups: [],
  }])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [uploading, setUploading] = useState(false)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const fileRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function sendMessage(question) {
    if (!question.trim() || loading) return

    const userMsg = { id: Date.now(), role: 'user', content: question }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          session_id: sessionId,
          user_id: 'anonymous',
        }),
      })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const data = await res.json()
      if (!sessionId) setSessionId(data.session_id)

      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'bot',
        content: data.answer,
        sources: data.sources || [],
        followups: data.followups || [],
      }])
    } catch {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'bot',
        content: 'Something went wrong. Please make sure the backend is running and try again.',
        sources: [],
        followups: [],
      }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  async function handleFileUpload(e) {
    const file = e.target.files?.[0]
    if (!file || !sessionId) {
      if (!sessionId) {
        setMessages(prev => [...prev, {
          id: Date.now(),
          role: 'bot',
          content: 'Please send a message first to start a session before uploading documents.',
          sources: [],
          followups: [],
        }])
      }
      return
    }

    setUploading(true)
    setMessages(prev => [...prev, {
      id: Date.now(),
      role: 'user',
      content: `📎 Uploading: ${file.name}`,
      sources: [],
      followups: [],
    }])

    try {
      const formData = new FormData()
      formData.append('session_id', sessionId)
      formData.append('doc_type', file.name)
      formData.append('file', file)

      const res = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
      const data = await res.json()

      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'bot',
        content: data.message,
        sources: [],
        followups: [],
      }])
    } catch {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'bot',
        content: 'Document upload failed. Please try again.',
        sources: [],
        followups: [],
      }])
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  function handleSubmit(e) {
    e.preventDefault()
    sendMessage(input)
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  return (
    <div className="chat-shell">
      <header className="chat-header">
        <div className="header-logo">🪪</div>
        <div>
          <h1 className="header-title">PAN Assistant</h1>
          <p className="header-sub">Powered by Protean PAN Services</p>
        </div>
      </header>

      <main className="chat-body" role="log" aria-live="polite" aria-label="Chat messages">
        {messages.map(msg => (
          <Message key={msg.id} msg={msg} onFollowup={sendMessage} />
        ))}
        {(loading || uploading) && (
          <div className="msg-row bot">
            <div className="avatar bot-avatar" aria-hidden="true">🤖</div>
            <div className="bubble bot-bubble"><TypingDots /></div>
          </div>
        )}
        <div ref={bottomRef} />
      </main>

      <footer className="chat-footer">
        <form className="input-form" onSubmit={handleSubmit}>

          {/* Upload button */}
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            style={{ display: 'none' }}
            onChange={handleFileUpload}
          />
          <button
            type="button"
            className="upload-btn"
            onClick={() => fileRef.current?.click()}
            disabled={loading || uploading}
            aria-label="Upload document"
            title="Upload document"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </button>

          <textarea
            ref={inputRef}
            className="chat-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about PAN card, Aadhaar linking, TAN..."
            rows={1}
            disabled={loading || uploading}
            aria-label="Type your question"
          />
          <button
            type="submit"
            className="send-btn"
            disabled={loading || uploading || !input.trim()}
            aria-label="Send message"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </form>
        <p className="footer-note">Responses are based on Protean PAN Services documentation.</p>
      </footer>
    </div>
  )
}