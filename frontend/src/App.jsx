import { useState, useRef, useEffect } from 'react'
import { ChevronRight } from 'lucide-react'
import { PromptInputBox } from './components/ui/ai-prompt-box'
import { ShapeBackground } from './components/ui/shape-landing-hero'
import { SpotlightBackground } from './components/ui/spotlight-background'
import Home from './pages/Home'
import { PanApplicationForm } from './components/ui/pan-application-form'

function inlineBold(text) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((p, i) =>
    p.startsWith('**') && p.endsWith('**')
      ? <strong key={i} className="text-white font-bold">{p.slice(2, -2)}</strong>
      : p
  )
}

function renderMarkdown(text) {
  const lines = text.split('\n')
  const out = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    if (/^#\s/.test(line)) {
      out.push(
        <h1 key={i} className="text-lg sm:text-xl font-extrabold text-white tracking-tight mt-5 mb-3"
          style={{ fontFamily: 'Archivo, sans-serif' }}>
          {inlineBold(line.replace(/^#\s/, ''))}
        </h1>
      )
    } else if (/^##\s/.test(line)) {
      out.push(
        <h2 key={i} className="text-base font-bold text-white mt-5 mb-2 tracking-tight"
          style={{ fontFamily: 'Archivo, sans-serif' }}>
          {inlineBold(line.replace(/^##\s/, ''))}
        </h2>
      )
    } else if (/^###\s/.test(line)) {
      const title = line.replace(/^###\s/, '')
      let why = null, accepted = null
      let j = i + 1
      if (j < lines.length && lines[j].startsWith('> ')) { why = lines[j].replace(/^>\s*/, ''); j++ }
      if (j < lines.length && lines[j].startsWith('Accepted:')) { accepted = lines[j].replace('Accepted: ', ''); j++ }
      out.push(
        <div key={i} className="rounded-xl border border-white/[0.07] bg-white/[0.025] p-3 sm:p-4 mt-3 space-y-2">
          <p className="text-white font-bold text-sm" style={{ fontFamily: 'Archivo, sans-serif' }}>
            {inlineBold(title)}
          </p>
          {why && (
            <p className="text-white/45 text-xs leading-relaxed border-l-2 border-purple-500/40 pl-3">
              {why}
            </p>
          )}
          {accepted && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {accepted.split(',').map((opt, k) => (
                <span key={k} className="text-[11px] text-white/60 bg-white/[0.05] border border-white/[0.08] rounded-full px-2.5 py-0.5">
                  {opt.trim()}
                </span>
              ))}
            </div>
          )}
        </div>
      )
      i = j
      continue
    } else if (/^>\s/.test(line)) {
      out.push(
        <div key={i} className="border-l-2 border-purple-500/50 pl-3 my-2">
          <p className="text-white/50 text-xs leading-relaxed italic">
            {inlineBold(line.replace(/^>\s*/, ''))}
          </p>
        </div>
      )
    } else if (/^---/.test(line)) {
      out.push(<hr key={i} className="border-white/[0.07] my-4" />)
    } else if (/^\d+\.\s/.test(line)) {
      const items = []
      while (i < lines.length && /^\d+\.\s/.test(lines[i])) {
        const num = lines[i].match(/^(\d+)\./)[1]
        const content = lines[i].replace(/^\d+\.\s/, '')
        items.push(
          <li key={i} className="flex gap-2.5 sm:gap-3 items-start">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-white/[0.06] border border-white/[0.1] flex items-center justify-center text-[10px] font-bold text-white/50 mt-0.5">
              {num}
            </span>
            <span className="text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>{inlineBold(content)}</span>
          </li>
        )
        i++
      }
      out.push(<ol key={`ol${i}`} className="space-y-2.5 my-3">{items}</ol>)
      continue
    } else if (/^[-•]\s/.test(line)) {
      const items = []
      while (i < lines.length && /^[-•]\s/.test(lines[i])) {
        items.push(
          <li key={i} className="flex gap-2.5 items-start text-sm">
            <span className="mt-[7px] w-1 h-1 rounded-full bg-purple-400/70 flex-shrink-0" />
            <span className="leading-relaxed text-sm" style={{ color: 'var(--text-muted)' }}>{inlineBold(lines[i].replace(/^[-•]\s/, ''))}</span>
          </li>
        )
        i++
      }
      out.push(<ul key={`ul${i}`} className="space-y-2 my-2 ml-1">{items}</ul>)
      continue
    } else if (/^\*\*[^*]+:\*\*/.test(line)) {
      const key = line.match(/^\*\*([^*]+):\*\*/)?.[1]
      const val = line.replace(/^\*\*[^*]+:\*\*\s*/, '')
      out.push(
        <div key={i} className="flex flex-col sm:flex-row sm:gap-3 sm:items-baseline py-1.5 border-b border-white/[0.04]">
          <span className="text-white/35 text-[10px] font-semibold uppercase tracking-widest sm:w-24 flex-shrink-0 mb-0.5 sm:mb-0">
            {key}
          </span>
          <span className="text-white text-sm font-medium">{val}</span>
        </div>
      )
    } else if (line.trim() === '') {
      out.push(<div key={i} className="h-2" />)
    } else {
      out.push(
        <p key={i} className="leading-7 text-sm" style={{ color: 'var(--text-muted)' }}>{inlineBold(line)}</p>
      )
    }
    i++
  }
  return out
}

function Message({ msg, onFollowup }) {
  const isUser = msg.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end px-2">
        <div className="max-w-[85%] sm:max-w-[70%] text-sm px-4 py-2.5 rounded-2xl rounded-br-sm leading-relaxed bg-neutral-800 text-white">
          {msg.content}
        </div>
      </div>
    )
  }

  const hasUploadPrompt = msg.content?.includes("Ready to upload?") || msg.content?.includes("Reply **Yes**")

  return (
    <div className="px-2 w-full max-w-2xl text-white/90">
      <div className="space-y-0.5">
        {renderMarkdown(
          hasUploadPrompt
            ? msg.content.replace(/Ready to upload\?.*$/ms, '').trimEnd()
            : msg.content
        )}

        {hasUploadPrompt && (
          <div className="mt-4 pt-4 border-t border-white/[0.06]">
            <p className="text-white/70 text-sm mb-3">Are you ready to upload your documents?</p>
            <div className="flex gap-2">
              <button onClick={() => onFollowup('__open_upload__')}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-500 active:scale-95 text-white text-sm font-semibold transition-all shadow-lg shadow-violet-900/30">
                Yes
              </button>
              <button onClick={() => onFollowup('__not_yet__')}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.09] active:scale-95 border border-white/10 text-white/60 hover:text-white text-sm font-medium transition-all">
                Not yet
              </button>
            </div>
          </div>
        )}

        {msg.followups?.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-3">
            {msg.followups.map((q, i) => (
              <button key={i} onClick={() => onFollowup(q)}
                className="text-xs text-neutral-400 hover:text-white border border-neutral-700 hover:border-neutral-500 hover:bg-neutral-800 active:scale-95 rounded-full px-3 py-1.5 transition-all flex items-center gap-1">
                <ChevronRight size={10} className="text-purple-400" />
                {q}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default function App() {
  const [page, setPage] = useState('home')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [started, setStarted] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function sendMessage(question) {
    if (!question.trim() || loading) return
    if (question === '__open_upload__') { setShowForm(true); return }
    if (question === '__not_yet__') {
      setMessages(prev => [...prev,
        { id: Date.now(), role: 'user', content: 'Not yet' },
        { id: Date.now() + 1, role: 'bot', content: "No worries! Whenever you're ready, just let me know and we'll get the documents uploaded. Take your time.", sources: [], followups: [] }
      ])
      return
    }

    // Close form on every new user message — backend will re-open if needed
    setShowForm(false)
    if (!started) setStarted(true)
    setMessages(prev => [...prev, { id: Date.now(), role: 'user', content: question }])
    setLoading(true)
    try {
      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, session_id: sessionId, user_id: 'anonymous' }),
      })
      const data = await res.json()
      if (!sessionId) setSessionId(data.session_id)
      if (data.open_upload) setShowForm(true)
      if (data.close_form) setShowForm(false)
      setMessages(prev => [...prev, {
        id: Date.now() + 1, role: 'bot',
        content: data.answer, sources: data.sources || [], followups: data.followups || [],
      }])
    } catch {
      setMessages(prev => [...prev, {
        id: Date.now() + 1, role: 'bot',
        content: 'Something went wrong. Please make sure the backend is running.',
        sources: [], followups: [],
      }])
    } finally {
      setLoading(false)
    }
  }

  async function handleFileUpload(file) {
    if (!sessionId) {
      setMessages(prev => [...prev, { id: Date.now(), role: 'bot', content: 'Please send a message first to start a session before uploading.', sources: [], followups: [] }])
      return
    }
    if (!started) setStarted(true)
    setMessages(prev => [...prev, { id: Date.now(), role: 'user', content: `📎 ${file.name}`, sources: [], followups: [] }])
    setLoading(true)
    try {
      const form = new FormData()
      form.append('session_id', sessionId)
      form.append('doc_type', file.name)
      form.append('file', file)
      const res = await fetch('/api/upload', { method: 'POST', body: form })
      const data = await res.json()
      setMessages(prev => [...prev, { id: Date.now() + 1, role: 'bot', content: data.message, sources: [], followups: [] }])
    } catch {
      setMessages(prev => [...prev, { id: Date.now() + 1, role: 'bot', content: 'Upload failed. Please try again.', sources: [], followups: [] }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {page === 'home' && <Home onGetStarted={() => setPage('chat')} />}
      {page === 'chat' && (
        <SpotlightBackground>
          <div className="w-full min-h-[100svh] flex flex-col items-center transition-colors duration-300"
            style={{ fontFamily: 'Inter, sans-serif' }}>

            {/* Theme toggle removed */}

            {/* Scrollable content */}
            <div className="w-full max-w-2xl mx-auto flex flex-col min-h-[100svh] px-3 sm:px-5 pt-5 sm:pt-8 pb-36 sm:pb-44">

              {/* Landing */}
              {!started && (
                <div className="flex flex-col items-center justify-center flex-1 text-center gap-3 py-10">
                  <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight shiny-text"
                    style={{ fontFamily: 'Syne, sans-serif' }}>
                    What can I help you with?
                  </h2>
                  <p className="text-sm max-w-xs sm:max-w-sm mx-auto leading-relaxed text-neutral-500">
                    Ask me anything about PAN cards, Aadhaar linking, TAN, TDS, or document requirements.
                  </p>
                </div>
              )}

              {/* Messages */}
              <div className="space-y-5 sm:space-y-6">
                {messages.map(msg => (
                  <Message key={msg.id} msg={msg} onFollowup={sendMessage} />
                ))}
                {/* Inline application form */}
                {showForm && (
                  <PanApplicationForm
                    sessionId={sessionId}
                    onCancel={() => setShowForm(false)}
                    onComplete={(data) => {
                      setShowForm(false)
                      setMessages(prev => [...prev, {
                        id: Date.now(), role: 'bot',
                        content: `## Application Submitted\n\n**Mother's Name:** ${data.motherName}\n**Annual Income:** ₹${data.salary}\n**Email:** ${data.email}\n**Designation:** ${data.designation}\n\nAll documents received. Your application is now under review — we'll notify you at **${data.email}** once it's processed.`,
                        sources: [], followups: [],
                      }])
                    }}
                  />
                )}
                <div ref={bottomRef} />
              </div>
            </div>

            {/* Fixed input */}
            <div className="fixed bottom-0 left-0 right-0 z-20 flex justify-center px-3 sm:px-4 pb-4 sm:pb-6 pt-3 bg-gradient-to-t from-[#050508] via-[#050508]/90 to-transparent" style={{ paddingBottom: 'max(1rem, env(safe-area-inset-bottom))' }}>
              <div className="w-full max-w-2xl">
                <PromptInputBox
                  onSend={(msg, files) => {
                    if (files?.length) handleFileUpload(files[0])
                    if (msg?.trim()) sendMessage(msg.trim())
                  }}
                  isLoading={loading}
                  placeholder="Ask about PAN cards, Aadhaar linking, TAN..."
                />
              </div>
            </div>

          </div>
        </SpotlightBackground>
      )}
    </>
  )
}
