import React, { useState, useRef, useEffect } from 'react'
import { ChevronRight, FolderLock } from 'lucide-react'
import { cn } from '@/lib/utils'
import { PromptInputBox } from './components/ui/ai-prompt-box'
import { SpotlightBackground } from './components/ui/spotlight-background'
import { ChatSidebar } from './components/ui/chat-sidebar'
import { DocumentsPanel } from './components/ui/documents-panel'
import { AgentConsentModal } from './components/ui/agent-consent-modal'
import Home from './pages/Home'
import { AuthModal } from './components/ui/auth-modal'
import { useDocumentUpload } from './hooks/useDocumentUpload'
import { useAgentFileAccess } from './hooks/useAgentFileAccess'
import { MissingFieldsForm } from './components/ui/missing-fields-form'
import { clearSessionKey } from './lib/keySession'
import { supabase } from './lib/supabase'

function inlineBold(text) {
  if (!text) return text
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((p, i) =>
    p.startsWith('**') && p.endsWith('**')
      ? <strong key={i} className="text-white font-bold">{p.slice(2, -2)}</strong>
      : p
  )
}

function renderMarkdown(text) {
  if (!text) return null
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
      out.push(
        <p key={i} className="leading-7 text-sm" style={{ color: 'var(--text-muted)' }}>{inlineBold(line)}</p>
      )
    } else if (/^\|/.test(line) && line.trim().endsWith('|')) {
      // ── Markdown table ──────────────────────────────────────
      // Collect all consecutive pipe lines
      const tableLines = []
      while (i < lines.length && /^\|/.test(lines[i]) && lines[i].trim().endsWith('|')) {
        tableLines.push(lines[i])
        i++
      }

      // Need at least 3 lines: header + separator + 1 body row
      // If we only have 1-2 lines (partial stream), skip rendering — don't show raw pipes
      if (tableLines.length < 3) {
        // Don't render partial tables — just skip silently
        continue
      }

      // Parse: first row = header, second row = separator (skip), rest = body
      const parseRow = (row) =>
        row.split('|').slice(1, -1).map(cell => cell.trim())

      const headerCells = parseRow(tableLines[0])
      // tableLines[1] is the |---|---| separator — skip it
      const bodyRows = tableLines.slice(2).map(parseRow)

      out.push(
        <div key={`tbl${i}`} className="my-4 w-full overflow-x-auto rounded-xl border border-white/[0.08]">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-white/[0.08] bg-white/[0.04]">
                {headerCells.map((cell, ci) => (
                  <th key={`th-${ci}`} className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-widest text-white/40">
                    {cell}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {bodyRows.map((row, ri) => (
                <tr key={`tr-${ri}`} className={cn(
                  'border-b border-white/[0.04] transition-colors',
                  ri % 2 === 0 ? 'bg-transparent' : 'bg-white/[0.02]'
                )}>
                  {row.map((cell, ci) => (
                    <td key={`td-${ri}-${ci}`} className={cn(
                      'px-4 py-3 leading-relaxed',
                      ci === 0 ? 'text-white/50 text-[11px] font-semibold uppercase tracking-wide' : 'text-white font-medium text-sm'
                    )}>
                      {inlineBold(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
      continue
    } else if (/^\|/.test(line)) {
      // Stray pipe line (malformed or separator-only) — skip silently
      if (/^\|[-| :]+\|$/.test(line.trim())) { i++; continue }
      out.push(
        <p key={i} className="leading-7 text-sm" style={{ color: 'var(--text-muted)' }}>{inlineBold(line)}</p>
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

// ── Guided flow sub-components (hooks must be at top level) ──────
function GuidedOptions({ opts, onSelect }) {
  const [checked, setChecked] = React.useState([])
  const [submitted, setSubmitted] = React.useState(false)

  // Guard against undefined opts
  if (!opts || !opts.choices || !Array.isArray(opts.choices)) {
    return null
  }

  const isCheckbox = opts.type === 'checkbox'

  const handleSelect = (choice) => {
    if (submitted) return
    if (isCheckbox) {
      setChecked(prev => prev.includes(choice) ? prev.filter(c => c !== choice) : [...prev, choice])
    } else {
      setSubmitted(true)
      onSelect(choice)
    }
  }

  return (
    <div>
      <div className={cn("flex gap-4", opts.hint ? "flex-col sm:flex-row" : "flex-wrap")}>
        <div className="flex flex-wrap gap-2">
          {opts.choices.map((choice, i) => {
            const isSelected = checked.includes(choice)
            return (
              <button
                key={i}
                onClick={() => handleSelect(choice)}
                disabled={submitted}
                className={cn(
                  "text-xs border rounded-full px-3 py-1.5 transition-all flex items-center gap-1.5 active:scale-95 disabled:opacity-40",
                  isCheckbox
                    ? isSelected
                      ? "text-white border-purple-500/60 bg-purple-500/10"
                      : "text-neutral-400 hover:text-white border-neutral-700 hover:border-neutral-500 hover:bg-neutral-800 cursor-pointer"
                    : "text-neutral-400 hover:text-white border-neutral-700 hover:border-neutral-500 hover:bg-neutral-800 cursor-pointer"
                )}
              >
                {isCheckbox && (
                  <span className={cn("w-3 h-3 rounded border flex-shrink-0 flex items-center justify-center text-[9px]",
                    isSelected ? "border-purple-400 bg-purple-500/40 text-purple-200" : "border-white/30")}>
                    {isSelected && "✓"}
                  </span>
                )}
                {!isCheckbox && <ChevronRight size={10} className="text-purple-400" />}
                {choice}
              </button>
            )
          })}
        </div>
        {opts.hint && (
          <div className="text-xs text-white/35 leading-relaxed border-l-2 border-purple-500/20 pl-3 max-w-xs">
            {opts.hint.split('\n').map((line, i) => (
              <p key={i} className={line.startsWith('**') ? 'text-white/50 font-semibold mb-1' : 'mb-0.5'}>
                {line.replace(/\*\*/g, '')}
              </p>
            ))}
          </div>
        )}
      </div>
      {isCheckbox && (
        <button
          onClick={() => {
            if (checked.length === 0 || submitted) return
            setSubmitted(true)
            onSelect(checked.join(', '))
          }}
          disabled={checked.length === 0 || submitted}
          className="mt-2 text-xs border rounded-full px-3 py-1.5 transition-all flex items-center gap-1 text-white border-purple-500/50 bg-purple-500/10 hover:bg-purple-500/20 disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <ChevronRight size={10} className="text-purple-400" />
          Confirm selection
        </button>
      )}
    </div>
  )
}

// ── Email confirm component ───────────────────────────────────────
function EmailConfirmOptions({ opts, onSelect }) {
  const [submitted, setSubmitted] = React.useState(false)
  const [showInput, setShowInput] = React.useState(false)
  const [emailValue, setEmailValue] = React.useState('')
  const [emailError, setEmailError] = React.useState('')

  // Guard against undefined opts
  if (!opts || !opts.choices || !Array.isArray(opts.choices)) {
    return null
  }

  const handleEmailSubmit = (e) => {
    e.preventDefault()
    const trimmed = emailValue.trim()
    if (!trimmed) return
    const valid = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/.test(trimmed)
    if (!valid) { 
      setEmailError('Please enter a valid email address.')
      return
    }
    setSubmitted(true)
    setEmailError('')
    onSelect(trimmed)
  }

  if (showInput) {
    return (
      <form onSubmit={handleEmailSubmit} className="flex flex-col gap-2 pt-2 max-w-xs">
        <div className="flex gap-2">
          <input
            type="email"
            value={emailValue}
            onChange={e => { setEmailValue(e.target.value); setEmailError('') }}
            disabled={submitted}
            placeholder="your@email.com"
            autoFocus
            className="flex-1 h-9 rounded-lg bg-white/[0.05] border border-white/[0.12] focus:border-purple-500/50 px-3 text-sm text-white placeholder:text-white/30 outline-none transition-colors disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={submitted || !emailValue.trim()}
            className="h-9 px-4 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95"
          >
            Use this
          </button>
        </div>
        {emailError && <p className="text-rose-400 text-[11px]">{emailError}</p>}
      </form>
    )
  }

  return (
    <div className="flex flex-wrap gap-2 pt-1">
      {opts.choices.map((choice, i) => {
        const isYes = i === 0
        return (
          <button
            key={i}
            disabled={submitted}
            onClick={() => {
              if (submitted) return
              if (isYes) {
                setSubmitted(true)
                onSelect(choice)
              } else {
                setShowInput(true)
              }
            }}
            className={cn(
              "text-xs border rounded-full px-3 py-1.5 transition-all flex items-center gap-1.5 active:scale-95 disabled:opacity-40",
              isYes
                ? "text-emerald-300 border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/20"
                : "text-neutral-400 hover:text-white border-neutral-700 hover:border-neutral-500 hover:bg-neutral-800 cursor-pointer"
            )}
          >
            {isYes ? <span className="text-emerald-400 text-[10px]">✓</span> : <ChevronRight size={10} className="text-purple-400" />}
            {choice}
          </button>
        )
      })}
    </div>
  )
}

// ── Inline email input box ────────────────────────────────────────
function EmailInputBox({ onSubmit }) {
  const [value, setValue] = React.useState('')
  const [submitted, setSubmitted] = React.useState(false)
  const [error, setError] = React.useState('')

  function handleSubmit(e) {
    e.preventDefault()
    const trimmed = value.trim()
    if (!trimmed) return
    const valid = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/.test(trimmed)
    if (!valid) { setError('Please enter a valid email address.'); return }
    setSubmitted(true)
    setError('')
    onSubmit(trimmed)
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2 pt-2 max-w-xs">
      <div className="flex gap-2">
        <input
          type="email"
          value={value}
          onChange={e => { setValue(e.target.value); setError('') }}
          disabled={submitted}
          placeholder="your@email.com"
          autoFocus
          className="flex-1 h-9 rounded-lg bg-white/[0.05] border border-white/[0.12] focus:border-purple-500/50 px-3 text-sm text-white placeholder:text-white/30 outline-none transition-colors disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={submitted || !value.trim()}
          className="h-9 px-4 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95"
        >
          Use this
        </button>
      </div>
      {error && <p className="text-rose-400 text-[11px]">{error}</p>}
    </form>
  )
}

function GuidedConfirm({ onYes, onNo }) {
  const [used, setUsed] = React.useState(null)
  return (
    <div className="flex gap-3 pt-1">
      <button
        onClick={() => { if (!used) { setUsed('yes'); onYes() } }}
        disabled={!!used}
        className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/25 active:scale-95 transition-all disabled:opacity-40"
      >
        <span className="text-emerald-400">✓</span> Yes, proceed
      </button>
      <button
        onClick={() => { if (!used) { setUsed('no'); onNo() } }}
        disabled={!!used}
        className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-white/[0.04] border border-white/20 text-white/70 hover:bg-white/[0.08] active:scale-95 transition-all disabled:opacity-40"
      >
        <span className="text-white/40">✎</span> Change something
      </button>
    </div>
  )
}

// ── Confirmation fields panel — all fields editable simultaneously ─────────
function ConfirmationFieldsPanel({ fields, language, onUpdate, disabled }) {
  const isTamil = language === 'ta'

  // Build initial state from current field values — always store in English
  const buildInitial = () => {
    const s = {}
    for (const f of fields) {
      if (f.field_type === 'text') {
        s[f.key] = f.display_value === '—' ? '' : (f.display_value || '')
      } else if (f.field_type === 'radio') {
        // Use display_value — it's already normalized to the English choice string
        // (e.g. "Yes"/"No" for booleans, actual choice text for others).
        // f.value can be "True"/"False" for boolean fields which won't match choices[].
        s[f.key] = f.display_value === '—' ? '' : (f.display_value || '')
      } else if (f.field_type === 'checkbox') {
        s[f.key] = f.value ? f.value.split(',').map(v => v.trim()).filter(Boolean) : []
      }
    }
    return s
  }

  const [vals, setVals] = React.useState(buildInitial)
  // savingCount tracks in-flight saves for button feedback, but never permanently locks the panel
  const [savingCount, setSavingCount] = React.useState(0)

  // When fields prop changes (backend refreshed after a save), re-sync vals
  // Only update fields that the user hasn't manually changed in this session
  const prevFieldsRef = React.useRef(fields)
  React.useEffect(() => {
    const prev = prevFieldsRef.current
    // Check if any field's display_value actually changed
    const hasChanges = fields.some(f => {
      const old = prev.find(p => p.key === f.key)
      return old && old.display_value !== f.display_value
    })
    if (hasChanges) {
      setVals(buildInitial())
      prevFieldsRef.current = fields
    }
  }, [fields]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!fields || fields.length === 0) return null

  const personalFields = fields.filter(f => f.section === 'personal')
  const applicationFields = fields.filter(f => f.section === 'application')

  // Get display choices (Tamil if available)
  function getChoices(f) {
    if (isTamil && f.choices_ta && f.choices_ta.length === (f.choices || []).length)
      return f.choices_ta
    return f.choices || []
  }

  // Map Tamil display value → English for backend
  function toEnglish(f, displayVal) {
    if (!isTamil || !f.choices_ta || !f.choices) return displayVal
    const idx = f.choices_ta.indexOf(displayVal)
    return idx >= 0 ? f.choices[idx] : displayVal
  }

  function handleRadio(key, displayVal, f) {
    // Always store English value internally for language-switch safety
    const englishVal = toEnglish(f, displayVal)
    setVals(prev => ({ ...prev, [key]: englishVal }))
  }

  function handleCheckbox(f, displayVal) {
    const englishVal = toEnglish(f, displayVal)
    setVals(prev => {
      const cur = prev[f.key] || []
      const alreadySel = cur.includes(englishVal)
      return {
        ...prev,
        [f.key]: alreadySel
          ? cur.filter(x => x !== englishVal)
          : [...cur, englishVal],
      }
    })
  }

  function handleText(key, val) {
    setVals(prev => ({ ...prev, [key]: val }))
  }

  function handleSaveAll() {
    if (savingCount > 0 || disabled) return

    // Collect only fields whose value actually changed
    const changes = []        // English commands for backend
    const changesDisplay = [] // Human-readable labels for user bubble (Tamil/Hindi/English)

    for (const f of fields) {
      const cur = vals[f.key]
      let englishVal = ''
      let displayVal = ''

      if (f.field_type === 'text') {
        englishVal = (cur || '').trim()
        if (!englishVal) continue
        const orig = f.display_value === '—' ? '' : (f.display_value || '')
        if (englishVal === orig) continue
        displayVal = englishVal
      } else if (f.field_type === 'radio') {
        if (!cur) continue
        englishVal = cur  // already English
        // Compare against display_value (normalized English) not f.value (may be "True"/"False")
        const origDisplay = f.display_value === '—' ? '' : (f.display_value || '')
        if (englishVal === origDisplay) continue
        // For display, find the Tamil label if active
        const idx = f.choices ? f.choices.indexOf(englishVal) : -1
        displayVal = (isTamil && f.choices_ta && idx >= 0) ? f.choices_ta[idx] : englishVal
      } else if (f.field_type === 'checkbox') {
        if (!cur || cur.length === 0) continue
        englishVal = cur.join(', ')  // already English values
        const origVal = f.value || ''
        if (englishVal === origVal) continue
        // For display, map each English value to the Tamil label if active
        displayVal = cur.map(v => {
          const idx = f.choices ? f.choices.indexOf(v) : -1
          return (isTamil && f.choices_ta && idx >= 0) ? f.choices_ta[idx] : v
        }).join(', ')
      }

      changes.push(`change ${f.label} to ${englishVal}`)
      const displayLabel = isTamil && f.label_ta ? f.label_ta : f.label
      changesDisplay.push(`${displayLabel}: ${displayVal}`)
    }

    if (changes.length === 0) return
    setSavingCount(n => n + 1)
    // Brief "Saved ✓" flash on the button, then reset so user can edit again
    setTimeout(() => setSavingCount(n => n - 1), 1200)
    // Build a friendly display summary for the user bubble (works for all languages)
    const displayLines = changesDisplay.length > 0 ? changesDisplay : changes
    const display = `✏️ ${displayLines.join(' | ')}`

    // Build patched confirmation_fields so the panel re-initializes correctly if re-mounted
    const updatedFields = fields.map(f => {
      const cur = vals[f.key]
      if (f.field_type === 'text') {
        const v = (cur || '').trim()
        return v ? { ...f, display_value: v, value: v } : f
      } else if (f.field_type === 'radio') {
        return cur ? { ...f, display_value: cur, value: cur } : f
      } else if (f.field_type === 'checkbox') {
        return cur?.length ? { ...f, display_value: cur.join(', '), value: cur.join(', ') } : f
      }
      return f
    })

    // Send { command, display, updatedFields } — App.jsx uses updatedFields to patch the message
    onUpdate({ command: changes.join(' | '), display, updatedFields })
  }

  function renderField(f) {
    const label = isTamil && f.label_ta ? f.label_ta : f.label
    const choices = getChoices(f)
    const curVal = vals[f.key]

    return (
      <div key={f.key} className="rounded-xl border border-white/[0.06] bg-white/[0.025] px-3 py-2.5 space-y-2">
        <p className="text-[10px] text-white/40 font-medium">{label}</p>

        {f.field_type === 'text' && (
          <input
            type="text"
            value={curVal || ''}
            onChange={e => handleText(f.key, e.target.value)}
            disabled={disabled}
            placeholder={isTamil ? 'புதிய மதிப்பை உள்ளிடுங்கள்…' : 'Enter value…'}
            className="w-full bg-white/[0.05] border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-white/25 focus:outline-none focus:border-purple-500/40 disabled:opacity-50"
          />
        )}

        {f.field_type === 'radio' && (
          <div className="flex flex-wrap gap-1.5">
            {choices.map((c, i) => {
              // vals stores English; c is the display label (may be Tamil)
              const englishC = toEnglish(f, c)
              const isSelected = curVal === englishC
              return (
                <button
                  key={i}
                  type="button"
                  disabled={disabled}
                  onClick={() => handleRadio(f.key, c, f)}
                  className={`text-[11px] px-2.5 py-1 rounded-full border transition-all disabled:opacity-50
                    ${isSelected
                      ? 'border-purple-400/60 bg-purple-500/20 text-purple-200'
                      : 'border-white/15 text-white/50 hover:border-white/30 hover:text-white/80'
                    }`}
                >
                  {c}
                </button>
              )
            })}
          </div>
        )}

        {f.field_type === 'checkbox' && (
          <div className="flex flex-wrap gap-1.5">
            {choices.map((c, i) => {
              // vals stores English; compare against English equivalent of display label
              const englishC = toEnglish(f, c)
              const sel = (curVal || []).includes(englishC)
              return (
                <button
                  key={i}
                  type="button"
                  disabled={disabled}
                  onClick={() => handleCheckbox(f, c)}
                  className={`text-[11px] px-2.5 py-1 rounded-full border transition-all flex items-center gap-1 disabled:opacity-50
                    ${sel
                      ? 'border-purple-400/60 bg-purple-500/20 text-purple-200'
                      : 'border-white/15 text-white/50 hover:border-white/30 hover:text-white/80'
                    }`}
                >
                  {sel && <span className="text-[9px] text-purple-300">✓</span>}
                  {c}
                </button>
              )
            })}
          </div>
        )}
      </div>
    )
  }

  function renderSection(title, sectionFields) {
    if (sectionFields.length === 0) return null
    return (
      <div className="space-y-1.5">
        <p className="text-[10px] uppercase tracking-widest text-white/25 font-semibold px-1 pt-1">{title}</p>
        {sectionFields.map(renderField)}
      </div>
    )
  }

  return (
    <div className="mt-3 rounded-2xl border border-white/[0.07] bg-white/[0.02] p-3 space-y-3">
      <p className="text-[11px] text-white/40 font-semibold">
        {isTamil ? '📋 விவரங்களை திருத்தவும்' : '📋 Edit your details'}
      </p>

      {renderSection(isTamil ? 'விண்ணப்ப விவரங்கள்' : 'Application Details', applicationFields)}
      {renderSection(isTamil ? 'தனிப்பட்ட விவரங்கள்' : 'Personal Details', personalFields)}

      {/* ── Save All button ──────────────────────────────────────────── */}
      {!disabled && (
        <div className="pt-2 border-t border-white/[0.06]">
          <button
            type="button"
            onClick={handleSaveAll}
            disabled={savingCount > 0}
            className="w-full py-2 rounded-xl text-sm font-semibold transition-all
              bg-purple-600/25 border border-purple-500/40 text-purple-200
              hover:bg-purple-600/40 hover:border-purple-400/60
              active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {savingCount > 0
              ? (isTamil ? '✓ புதுப்பிக்கப்பட்டது' : '✓ Updated')
              : (isTamil ? '💾 அனைத்தையும் சேமி' : '💾 Save Changes')}
          </button>
        </div>
      )}
    </div>
  )
}

// ── Details summary card — shows all collected fields in chat ────────────
function DetailsCard({ fields, language }) {
  if (!fields || fields.length === 0) return null
  const isTamil = language === 'ta'
  const isHindi = language === 'hi'

  const applicationFields = fields.filter(f => f.section === 'application')
  const personalFields = fields.filter(f => f.section === 'personal')

  const sectionTitle = (en, ta, hi) => {
    if (isTamil) return ta
    if (isHindi) return hi
    return en
  }

  function renderValue(f) {
    const val = f.display_value
    if (!val || val === '—') {
      return <span className="text-white/25 italic text-xs">—</span>
    }
    return <span className="text-white font-medium text-xs">{val}</span>
  }

  function renderSection(title, sectionFields) {
    if (sectionFields.length === 0) return null
    return (
      <div className="space-y-1">
        <p className="text-[10px] uppercase tracking-widest text-purple-400/60 font-semibold px-0.5 pt-1">
          {title}
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
          {sectionFields.map(f => {
            const label = isTamil && f.label_ta ? f.label_ta : f.label
            return (
              <div key={f.key}
                className="flex flex-col gap-0.5 rounded-lg border border-white/[0.06] bg-white/[0.025] px-2.5 py-2">
                <span className="text-[10px] text-white/35">{label}</span>
                {renderValue(f)}
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div className="mt-3 rounded-2xl border border-white/[0.08] bg-white/[0.02] p-3 space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <div className="w-1.5 h-1.5 rounded-full bg-purple-400" />
        <p className="text-xs text-white/60 font-semibold">
          {sectionTitle('Your Application Details', 'உங்கள் விண்ணப்ப விவரங்கள்', 'आपके आवेदन विवरण')}
        </p>
      </div>

      {renderSection(
        sectionTitle('Application Options', 'விண்ணப்ப விருப்பங்கள்', 'आवेदन विकल्प'),
        applicationFields
      )}
      {renderSection(
        sectionTitle('Personal Details', 'தனிப்பட்ட விவரங்கள்', 'व्यक्तिगत विवरण'),
        personalFields
      )}
    </div>
  )
}

function Message({ msg, onFollowup, language }) {
  const isUser = msg.role === 'user'
  const [usedFollowup, setUsedFollowup] = React.useState(null)
  const [checkedOptions, setCheckedOptions] = React.useState([])
  const [optionSubmitted, setOptionSubmitted] = React.useState(false)
  const [confirmUsed, setConfirmUsed] = React.useState(null) // 'yes' | 'no'
  if (!msg.content && !msg.streaming) return null

  if (isUser) {
    return (
      <div className="flex justify-end px-2">
        <div className="max-w-[85%] sm:max-w-[70%] text-sm px-4 py-2.5 rounded-2xl rounded-br-sm leading-relaxed bg-neutral-800 text-white">
          {msg.content}
        </div>
      </div>
    )
  }

  // ── Resume banner — special styled card ────────────────────────────────────
  if (msg._resumeBanner) {
    return (
      <div className="px-2 w-full max-w-2xl">
        <div className="rounded-2xl border border-amber-500/25 bg-amber-500/[0.06] px-4 py-3 space-y-1">
          {renderMarkdown(msg.content)}
        </div>
      </div>
    )
  }

  const opts = msg.options
  const isCheckbox = opts?.type === 'checkbox'
  const isRadio = opts?.type === 'radio'
  const isEmailConfirm = opts?.type === 'email_confirm'
  const isEmailInput = opts?.type === 'email_input'

  const handleOptionSelect = (choice) => {
    if (optionSubmitted || msg.followupUsed) return
    if (isCheckbox) {
      setCheckedOptions(prev =>
        prev.includes(choice) ? prev.filter(c => c !== choice) : [...prev, choice]
      )
    } else {
      // Radio / email_confirm — submit immediately on click
      setOptionSubmitted(true)
      onFollowup(choice, msg.id)
    }
  }

  const handleCheckboxSubmit = () => {
    if (checkedOptions.length === 0 || optionSubmitted) return
    setOptionSubmitted(true)
    onFollowup(checkedOptions.join(', '), msg.id)
  }

  return (
    <div className="px-2 w-full max-w-2xl text-white/90">
      <div className="space-y-0.5">
        {msg.content ? renderMarkdown(msg.content) : null}
        {msg.streaming && (
          <span className="inline-block w-2 h-4 ml-0.5 bg-white/60 rounded-sm animate-pulse align-middle" />
        )}

        {/* ── Details summary card — shown at confirmation step ── */}
        {!msg.streaming && msg.confirmation_fields && confirmUsed === null && (
          <DetailsCard fields={msg.confirmation_fields} language={language} />
        )}

        {/* ── Missing Fields Form — for manual data entry after document upload ── */}
        {!msg.streaming && msg.missing_fields_form && !optionSubmitted && (
          <div className="pt-4 pb-2">
            <MissingFieldsForm
              missingFields={msg.missing_fields_form.fields}
              extractedFields={msg.missing_fields_form.extracted_fields}
              sessionId={msg.missing_fields_form.session_id}
              authId={msg.missing_fields_form.auth_id}
              qualityScore={msg.missing_fields_form.quality_score}
              onComplete={(result) => {
                setOptionSubmitted(true)
                onFollowup(`Document completion successful! ${result.message || ''}`, msg.id)
              }}
              onCancel={() => {
                setOptionSubmitted(true)
                onFollowup("I'll provide the details manually later.", msg.id)
              }}
            />
          </div>
        )}

        {/* ── Confirmation fields panel (inline per-field update buttons) ── */}
        {/* Stays open and editable until the user clicks "Yes, proceed" */}
        {!msg.streaming && msg.confirmation_fields && confirmUsed === null && (
          <ConfirmationFieldsPanel
            fields={msg.confirmation_fields}
            language={language}
            onUpdate={(updatePayload) => {
              // Never lock the panel — just send the update and let the user keep editing
              onFollowup(updatePayload, msg.id)
            }}
            disabled={false}
          />
        )}

        {/* ── Confirm action buttons (Confirm / Change something) ── */}
        {/* Always shown alongside the edit panel until a final decision is made */}
        {!msg.streaming && msg.confirm_action && confirmUsed === null && (
          <div className="flex gap-3 pt-4">
            <button
              onClick={() => { setConfirmUsed('yes'); onFollowup('Yes, proceed', msg.id) }}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/25 hover:border-emerald-400/60 active:scale-95 transition-all"
            >
              <span className="text-emerald-400">✓</span> Confirm
            </button>
            <button
              onClick={() => { setConfirmUsed('no'); onFollowup('No, I need to change something', msg.id) }}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-white/[0.04] border border-white/20 text-white/70 hover:bg-white/[0.08] hover:border-white/30 active:scale-95 transition-all"
            >
              <span className="text-white/40">✎</span> Change something
            </button>
          </div>
        )}

        {/* Confirm used — show greyed state (panel is already hidden via confirmUsed === null check above) */}
        {!msg.streaming && msg.confirm_action && confirmUsed !== null && (
          <div className="flex gap-3 pt-4 opacity-40 pointer-events-none">
            <div className={cn(
              "flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold border",
              confirmUsed === 'yes'
                ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-300"
                : "bg-white/[0.04] border-white/20 text-white/70"
            )}>
              {confirmUsed === 'yes' ? <><span className="text-emerald-400">✓</span> Confirmed</> : <><span className="text-white/40">✎</span> Change something</>}
            </div>
          </div>
        )}

        {/* Interactive options UI */}
        {!msg.streaming && opts && !optionSubmitted && !msg.followupUsed && (
          <div className="pt-3">
            {isCheckbox && (
              <>
                <div className="flex flex-wrap gap-2">
                  {opts.choices.map((choice, i) => {
                    const isSelected = checkedOptions.includes(choice)
                    return (
                      <button
                        key={i}
                        onClick={() => handleOptionSelect(choice)}
                        className={`text-xs border rounded-full px-3 py-1.5 transition-all flex items-center gap-1.5
                          ${isSelected
                            ? 'text-white border-purple-500/60 bg-purple-500/10'
                            : 'text-neutral-400 hover:text-white border-neutral-700 hover:border-neutral-500 hover:bg-neutral-800 active:scale-95 cursor-pointer'
                          }`}
                      >
                        <span className={`w-3 h-3 rounded border flex-shrink-0 flex items-center justify-center text-[9px]
                          ${isSelected ? 'border-purple-400 bg-purple-500/40 text-purple-200' : 'border-white/30'}`}>
                          {isSelected && '✓'}
                        </span>
                        {choice}
                      </button>
                    )
                  })}
                </div>
                <button
                  onClick={handleCheckboxSubmit}
                  disabled={checkedOptions.length === 0}
                  className="mt-2 text-xs border rounded-full px-3 py-1.5 transition-all flex items-center gap-1 text-white border-purple-500/50 bg-purple-500/10 hover:bg-purple-500/20 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <ChevronRight size={10} className="text-purple-400" />
                  Confirm selection
                </button>
              </>
            )}
            {isRadio && (
              <div className={cn("flex gap-4", opts.hint ? "flex-col sm:flex-row" : "flex-wrap")}>
                <div className="flex flex-wrap gap-2">
                  {opts.choices.map((choice, i) => (
                    <button
                      key={i}
                      onClick={() => handleOptionSelect(choice)}
                      className="text-xs text-neutral-400 hover:text-white border border-neutral-700 hover:border-neutral-500 hover:bg-neutral-800 active:scale-95 rounded-full px-3 py-1.5 transition-all flex items-center gap-1 cursor-pointer"
                    >
                      <ChevronRight size={10} className="text-purple-400" />
                      {choice}
                    </button>
                  ))}
                </div>
                {opts.hint && (
                  <div className="text-xs text-white/40 leading-relaxed border-l-2 border-purple-500/30 pl-3 max-w-sm">
                    {opts.hint.split('\n').map((line, i) => (
                      <p key={i} className={line.startsWith('**') ? 'text-white/60 font-semibold mb-1' : 'mb-0.5'}>
                        {line.replace(/\*\*/g, '')}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Email confirm — Yes use account / No use different */}
            {isEmailConfirm && (
              <EmailConfirmOptions
                opts={opts}
                onSelect={(choice) => { setOptionSubmitted(true); onFollowup(choice, msg.id) }}
              />
            )}

            {/* Email input — inline text box */}
            {isEmailInput && (
              <EmailInputBox
                onSubmit={(email) => { setOptionSubmitted(true); onFollowup(email, msg.id) }}
              />
            )}
          </div>
        )}

        {/* Submitted — show greyed out */}
        {!msg.streaming && opts && opts.choices && (optionSubmitted || msg.followupUsed) && (
          <div className="flex flex-wrap gap-2 pt-3 opacity-40 pointer-events-none">
            {opts.choices.map((choice, i) => (
              <span key={i} className="text-xs text-neutral-500 border border-neutral-800 rounded-full px-3 py-1.5 flex items-center gap-1">
                <ChevronRight size={10} className="text-neutral-600" />
                {choice}
              </span>
            ))}
          </div>
        )}


        {!msg.streaming && msg.elapsed_ms != null && (
          <p className="text-[10px] text-neutral-600 pt-1">{msg.elapsed_ms}ms</p>
        )}
      </div>
    </div>
  )
}

export default function App() {
  const [page, setPage] = useState('home')
  const [showAuth, setShowAuth] = useState(false)
  const [user, setUser] = useState(null)
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [started, setStarted] = useState(false)
  const [sessions, setSessions] = useState([])
  // Start collapsed on mobile, open on desktop
  const [sidebarOpen, setSidebarOpen] = useState(() => typeof window !== 'undefined' ? window.innerWidth >= 768 : true)
  const [toast, setToast] = useState(null)
  const [lastInputWasVoice, setLastInputWasVoice] = useState(false)
  const [drafts, setDrafts] = useState({})
  const [docsOpen, setDocsOpen] = useState(false)
  const [docCount, setDocCount] = useState(0)

  // Keep doc count badge in sync via Supabase realtime
  useEffect(() => {
    if (!user) { setDocCount(0); return }

    // Initial count
    supabase
      .from('document_meta')
      .select('id', { count: 'exact', head: true })
      .then(({ count }) => setDocCount(count ?? 0))

    // Live updates
    const ch = supabase
      .channel('doc_count_badge')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'document_meta' },
        () => setDocCount(n => n + 1))
      .on('postgres_changes', { event: 'DELETE', schema: 'public', table: 'document_meta' },
        () => setDocCount(n => Math.max(0, n - 1)))
      .subscribe()

    return () => { supabase.removeChannel(ch) }
  }, [user])
  const [agentConsent, setAgentConsent] = useState(null)
  const [consentError, setConsentError] = useState(null)
  // Voice response toggle - when enabled, agent responds with voice even for text input
  // Default to true for better voice experience - users can disable if needed
  const [voiceResponseEnabled, setVoiceResponseEnabled] = useState(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('voice_response_enabled')
      // If not set yet, default to true (voice enabled). If explicitly set, use that value.
      return stored !== null ? stored === 'true' : true
    }
    return true
  })
  // Language preference — persisted to localStorage
  const [language, setLanguage] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('pan_lang') || 'en'
    }
    return 'en'
  })
  const msgIdRef = useRef(1)
  const nextId = () => ++msgIdRef.current
  const sessionIdRef = useRef(null)
  const audioPlayerRef = useRef(null)   // kept for legacy reference, playback now uses Web Audio
  const audioCtxTTSRef = useRef(null)   // Web Audio API context for TTS playback
  const activeTTSSourceRef = useRef(null)  // currently playing BufferSourceNode — stopped on new TTS
  const activeTTSAbortRef = useRef(null)   // AbortController for in-flight TTS fetch
  const bottomRef = useRef(null)

  // Create (or reuse) the shared TTS AudioContext
  function _getTTSAudioCtx() {
    if (!audioCtxTTSRef.current || audioCtxTTSRef.current.state === 'closed') {
      audioCtxTTSRef.current = new (window.AudioContext || window.webkitAudioContext)()
    }
    return audioCtxTTSRef.current
  }

  function showToast(msg, type = 'error') {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 4000)
  }
  
  function toggleVoiceResponse() {
    const newValue = !voiceResponseEnabled
    setVoiceResponseEnabled(newValue)
    if (typeof window !== 'undefined') {
      localStorage.setItem('voice_response_enabled', newValue.toString())
    }
    
    // Unlock / create AudioContext on user gesture
    if (newValue) {
      const ctx = _getTTSAudioCtx()
      if (ctx.state === 'suspended') ctx.resume()
    }
    
    showToast(
      newValue 
        ? 'Voice responses enabled - Agent will speak replies' 
        : 'Voice responses disabled',
      'success'
    )
  }
  
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  function handleLogin(userData) {
    setUser(userData)
    setShowAuth(false)
    setPage('chat')
    loadSessions()
  }

  // ── Sessions ────────────────────────────────────────────────────
  async function loadSessions() {
    try {
      const res = await fetch('/api/chat/sessions', { credentials: 'include' })
      if (!res.ok) return
      const data = await res.json()
      setSessions(data.sessions || [])
      // Auto-load most recent session ONLY if no session is currently active
      if (data.sessions?.length && !sessionId && !sessionIdRef.current) {
        await switchSession(data.sessions[0].id)
      }
    } catch { /* ignore */ }
  }

  async function createNewSession() {
    // If the current session is already empty (no messages sent), don't open another new chat
    if (!started && messages.length === 0) return

    try {
      const res = await fetch('/api/chat/sessions', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      })
      const data = await res.json()
      
      // CRITICAL: Set session ID and clear messages BEFORE updating sessions list
      // This prevents race conditions where loadSessions might auto-switch
      setSessionId(data.session.id)
      sessionIdRef.current = data.session.id
      setMessages([])
      setStarted(false)
      
      // Now update sessions list
      setSessions(prev => [data.session, ...prev])
    } catch { /* ignore */ }
  }

  async function switchSession(id) {
    // CRITICAL: Update session ID and clear messages synchronously FIRST
    setSessionId(id)
    sessionIdRef.current = id
    setMessages([])  // Clear immediately - this must happen before any async operations
    setStarted(false)
    setLoading(false)
    
    try {
      const res = await fetch(`/api/chat/history/${id}`, { credentials: 'include' })
      if (!res.ok) return
      const data = await res.json()
      
      // Guard: only set messages if this session is still active
      // This prevents race conditions when rapidly switching sessions
      if (sessionIdRef.current !== id) {
        console.log('[switchSession] Session changed during load, ignoring stale history')
        return
      }
      
      const historyMsgs = (data.history || []).map((m, i) => ({
        id: i, role: m.role === 'assistant' ? 'bot' : m.role,
        content: m.content, sources: [], followups: [],
      }))

      // ── Resume banner: inject a synthetic bot message if flow is in progress ─
      const fs = data.flow_state
      if (fs?.active && fs.current_step && historyMsgs.length > 0) {
        const isTa = (fs.language || language) === 'ta'
        const stepLabel = isTa ? fs.step_labels?.ta : fs.step_labels?.en
        const completedFields = fs.completed_fields || {}
        const missingFields   = fs.missing_for_step || []

        // Field display names bilingual
        const FIELD_NAMES = {
          applicant_type:    { en: 'Applicant Type',            ta: 'விண்ணப்பதாரர் வகை' },
          submission_mode:   { en: 'Submission Mode',           ta: 'சமர்ப்பிக்கும் முறை' },
          delivery_mode:     { en: 'PAN Delivery',              ta: 'விநியோக முறை' },
          aadhaar_photo:     { en: 'Aadhaar Photo',             ta: 'ஆதார் புகைப்படம்' },
          source_of_income:  { en: 'Source of Income',          ta: 'வருமான மூலம்' },
          address_for_comm:  { en: 'Address for Communication', ta: 'தொடர்பு முகவரி' },
          residential_status:{ en: 'Residential Status',        ta: 'குடியிருப்பு நிலை' },
          rep_assessee:      { en: 'Representative Assessee',   ta: 'பிரதிநிதி நியமனம்' },
          full_name:         { en: 'Full Name',                 ta: 'முழு பெயர்' },
          grandfather_name:  { en: "Grandfather's Name",        ta: 'தாத்தாவின் பெயர்' },
          mother_name:       { en: "Mother's Name",             ta: 'தாயின் பெயர்' },
          email:             { en: 'Email',                     ta: 'மின்னஞ்சல்' },
          salary:            { en: 'Annual Income',             ta: 'ஆண்டு வருமானம்' },
        }
        const fname = (k) => isTa ? (FIELD_NAMES[k]?.ta || k) : (FIELD_NAMES[k]?.en || k)

        // Build filled fields summary
        const doneLines = Object.entries(completedFields).map(([k, v]) => `✅ **${fname(k)}:** ${v}`)
        const missLines = missingFields.map(k => `⬜ **${fname(k)}**`)

        let resumeText
        if (isTa) {
          resumeText = [
            `👋 **வரவேற்கிறோம்!** உங்கள் PAN விண்ணப்பம் **${stepLabel}** கட்டத்தில் உள்ளது.`,
            '',
            doneLines.length > 0 ? `**நிரப்பிய விவரங்கள்:**\n${doneLines.join('\n')}` : '',
            missLines.length > 0 ? `\n**இன்னும் தேவையானவை:**\n${missLines.join('\n')}` : '',
            '',
            '_"தொடர்" என்று டைப் செய்து தொடரவும் அல்லது மேலே உள்ள புதுப்பி பொத்தான்களை கிளிக் செய்யவும்._',
          ].filter(Boolean).join('\n')
        } else {
          resumeText = [
            `👋 **Welcome back!** Your PAN application is in progress — you were on the **${stepLabel}** step.`,
            '',
            doneLines.length > 0 ? `**Filled so far:**\n${doneLines.join('\n')}` : '',
            missLines.length > 0 ? `\n**Still needed:**\n${missLines.join('\n')}` : '',
            '',
            '_Type "continue" to pick up where you left off, or use the **Update** buttons above to change any field._',
          ].filter(Boolean).join('\n')
        }

        const resumeMsg = {
          id: -1,
          role: 'bot',
          content: resumeText,
          sources: [], followups: [],
          _resumeBanner: true,
        }
        setStarted(true)
        setMessages([...historyMsgs, resumeMsg])
      } else if (historyMsgs.length > 0) {
        setStarted(true)
        setMessages(historyMsgs)
      } else {
        // Explicitly set empty array for new sessions with no history
        setMessages([])
      }
    } catch (err) {
      console.error('[switchSession] Failed to load history:', err)
      // On error, ensure messages are cleared
      if (sessionIdRef.current === id) {
        setMessages([])
      }
    }
  }

  async function deleteSession(id) {
    // ── OPTIMISTIC UPDATE: Remove from UI immediately ────────────────────────
    setSessions(prev => {
      const remaining = prev.filter(s => s.id !== id)
      // If we deleted the active session, switch to the next one
      if (sessionId === id) {
        if (remaining.length) {
          switchSession(remaining[0].id)
        } else {
          setSessionId(null)
          sessionIdRef.current = null
          setMessages([])
          setStarted(false)
        }
      }
      return remaining
    })

    // ── API CALL: Delete from backend (in background) ────────────────────────
    try {
      const res = await fetch(`/api/chat/sessions/${id}`, { method: 'DELETE', credentials: 'include' })
      if (!res.ok) {
        // If API fails, reload sessions to restore correct state
        showToast('Failed to delete chat from server.')
        loadSessions()
        return
      }
    } catch {
      // If API fails, reload sessions to restore correct state
      showToast('Failed to delete chat from server.')
      loadSessions()
      return
    }
  }

  async function handleLogout() {
    clearSessionKey()                                          // wipe MEK first
    await supabase.auth.signOut()                             // then sign out
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {})
    setUser(null); setPage('home'); setMessages([])
    setSessionId(null); sessionIdRef.current = null; setStarted(false); setSessions([])
  }

  // ── Shared AudioContext for TTS playback (bypasses autoplay policy) ──────
  useEffect(() => {
    const unlock = () => {
      const ctx = audioCtxTTSRef.current
      if (ctx && ctx.state === 'suspended') ctx.resume()
    }
    window.addEventListener('click', unlock, { once: false })
    window.addEventListener('keydown', unlock, { once: false })
    return () => {
      window.removeEventListener('click', unlock)
      window.removeEventListener('keydown', unlock)
    }
  }, [])

  // ── Stop any currently playing TTS immediately ───────────────────────────
  function _stopTTS() {
    // Abort an in-flight fetch (audio still downloading)
    if (activeTTSAbortRef.current) {
      activeTTSAbortRef.current.abort()
      activeTTSAbortRef.current = null
    }
    // Stop a playing BufferSourceNode
    if (activeTTSSourceRef.current) {
      try { activeTTSSourceRef.current.stop() } catch (_) {}
      activeTTSSourceRef.current = null
    }
  }

  // ── Core TTS fetch+play — streams WAV bytes and starts playing ASAP ──────────
  async function _playTTS(text) {
    if (!text?.trim()) return

    // Stop whatever is currently playing / downloading before starting new audio
    _stopTTS()

    const t0 = performance.now()
    const abortCtrl = new AbortController()
    activeTTSAbortRef.current = abortCtrl

    try {
      const form = new FormData()
      form.append('text', text)
      form.append('language', language)

      const res = await fetch('/api/voice/tts', {
        method: 'POST',
        body: form,
        signal: abortCtrl.signal,
      })
      if (!res.ok) { console.error('[TTS] request failed:', res.status); return }
      console.log(`[TTS] headers received in ${(performance.now() - t0).toFixed(0)}ms`)

      const reader = res.body.getReader()
      const chunks = []
      let totalBytes = 0

      // Resume AudioContext in parallel while bytes are downloading
      const ctx = _getTTSAudioCtx()
      const resumePromise = ctx.state === 'suspended' ? ctx.resume() : Promise.resolve()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        chunks.push(value)
        totalBytes += value.byteLength
      }

      // Clear the abort controller — download finished cleanly
      activeTTSAbortRef.current = null

      if (totalBytes === 0) { console.error('[TTS] empty response'); return }

      const merged = new Uint8Array(totalBytes)
      let offset = 0
      for (const chunk of chunks) { merged.set(chunk, offset); offset += chunk.byteLength }

      console.log(`[TTS] ${totalBytes} bytes in ${(performance.now() - t0).toFixed(0)}ms, decoding…`)

      await resumePromise
      const audioBuffer = await ctx.decodeAudioData(merged.buffer)

      // Stop anything that started while we were decoding
      if (activeTTSSourceRef.current) {
        try { activeTTSSourceRef.current.stop() } catch (_) {}
        activeTTSSourceRef.current = null
      }

      const source = ctx.createBufferSource()
      source.buffer = audioBuffer
      source.connect(ctx.destination)
      source.onended = () => {
        // Clean up ref when playback finishes naturally
        if (activeTTSSourceRef.current === source) activeTTSSourceRef.current = null
      }
      activeTTSSourceRef.current = source
      source.start(0)
      console.log(`[TTS] ✅ playing in ${(performance.now() - t0).toFixed(0)}ms: ${text.slice(0, 60)}`)
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log('[TTS] fetch aborted (new message started)')
      } else {
        console.error('[TTS] failed:', err)
      }
    }
  }

  // ── Build options spoken sentence ─────────────────────────────
  function _optionsSentence(options) {
    if (!options?.choices?.length) return ''
    const choiceList = options.choices
    if (language === 'ta') return 'உங்கள் விருப்பங்கள்: ' + choiceList.join(', ') + '.'
    if (language === 'hi') return 'आपके विकल्प हैं: ' + choiceList.join(', ') + '.'
    const readable = choiceList.map(c => c.replace(/\s*\/\s*/g, ' or '))
    if (readable.length === 1) return `Your option is: ${readable[0]}.`
    const last = readable[readable.length - 1]
    const rest = readable.slice(0, -1).join(', ')
    return `Your options are: ${rest}, or ${last}.`
  }

  // ── TTS playback for voice replies ─────────────────────────────
  async function speakReply(text, options = null) {
    if (!text?.trim()) return
    const clean = text.replace(/<think>[\s\S]*?<\/think>/g, '').trim()
    if (!clean) return
    const sentences = clean.split(/(?<=[.!?।॥])\s+/).map(s => s.trim()).filter(Boolean)
    let speakText = sentences.slice(0, 3).join(' ')
    const optSentence = _optionsSentence(options)
    if (optSentence) speakText = speakText + ' ' + optSentence
    if (!speakText.trim()) return
    await _playTTS(speakText)
  }

  // ── Messaging ───────────────────────────────────────────────────
  async function sendMessage(question, { fromVoice = false, displayText = null } = {}) {
    if (!question.trim() || loading) return

    // Stop any currently playing TTS immediately — new message takes over
    _stopTTS()

    // Auto-create session if none active
    let sid = sessionId
    if (!sid) {
      try {
        const res = await fetch('/api/chat/sessions', {
          method: 'POST', credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
        })
        const data = await res.json()
        if (!data.session?.id) throw new Error('No session returned')
        sid = data.session.id
        setSessions(prev => [data.session, ...prev])
        setSessionId(sid)
      } catch (err) {
        showToast('Could not start a session. Make sure the backend is running.')
        return
      }
    }

    const requestSid = sid
    sessionIdRef.current = sid

    if (!started) setStarted(true)
    const userMsgId = nextId()
    // Show displayText in the bubble if provided (e.g. Tamil summary), send question to backend
    setMessages(prev => [...prev, { id: userMsgId, role: 'user', content: displayText || question, _sid: requestSid }])
    setLoading(true)

    // Add a placeholder bot message that we'll stream into
    const botId = nextId()
    setMessages(prev => [...prev, { id: botId, role: 'bot', content: '', sources: [], followups: [], _sid: requestSid, streaming: true }])

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ message: question, session_id: requestSid, language }),
      })

      if (res.status === 401) {
        handleLogout()
        showToast('Your session expired. Please sign in again.')
        setMessages(prev => prev.filter(m => m.id !== botId))
        return
      }

      // Handle non-streaming error responses (e.g. 502, 503)
      if (!res.ok) {
        let errMsg = 'Something went wrong.'
        try { const d = await res.json(); errMsg = d.error || errMsg } catch {}
        if (sessionIdRef.current !== requestSid) return
        setMessages(prev => prev.map(m =>
          m.id === botId ? { ...m, content: errMsg, streaming: false } : m
        ))
        return
      }

      // Non-streaming fallback (when RAG server hasn't restarted yet)
      const contentType = res.headers.get('content-type') || ''
      if (contentType.includes('application/json')) {
        const data = await res.json()
        if (sessionIdRef.current !== requestSid) return
        const reply = data.answer || data.reply || data.error || 'Something went wrong.'
        if (data.title) setSessions(prev => prev.map(s => s.id === requestSid ? { ...s, title: data.title } : s))
        const freshFields = data.confirmation_fields || null
        setMessages(prev => prev.map(m => {
          if (m.id === botId) {
            return { ...m, content: reply, sources: data.sources || [], followups: data.followups || [], options: data.options || null, confirm_action: data.confirm_action || false, guided: data.guided === true && !!(data.options || data.confirm_action), streaming: false, elapsed_ms: data.elapsed_ms, confirmation_fields: freshFields }
          }
          // Sync all older confirmation panels with the fresh field data
          if (freshFields && m.confirmation_fields) {
            return { ...m, confirmation_fields: freshFields }
          }
          return m
        }))
        // Play voice response — include option choices if present
        if ((voiceResponseEnabled || fromVoice) && reply) speakReply(reply, data.options || null)
        return
      }

      // Consume SSE stream
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      let fullText = ''
      let streamOptions = null     // captured from meta event
      let earlyTTSFired = false    // true once we've fired TTS mid-stream
      let earlySpokenSentCount = 0 // how many sentences were spoken early

      // ── Fire TTS as early as possible ────────────────────────────────────
      // Instead of waiting for sentence-ending punctuation, we fire TTS
      // after a short grace period (350ms) from the first token.
      // This overlaps the Sarvam API call with the remainder of streaming,
      // slashing the perceived delay by 1-2 seconds.
      let firstTokenTime = null
      let earlyTTSTimer = null

      function maybeFireEarlyTTS() {
        if (earlyTTSFired || !(voiceResponseEnabled || fromVoice)) return
        const cleaned = fullText.replace(/<think>[\s\S]*?<\/think>/g, '').trim()
        if (!cleaned) return

        // Prefer a clean sentence boundary if we already have one
        const hasBoundary = /[.!?।॥]/.test(cleaned)
        if (hasBoundary) {
          const sentences = splitSentences(cleaned)
          if (sentences.length >= 1) {
            earlyTTSFired = true
            if (earlyTTSTimer) { clearTimeout(earlyTTSTimer); earlyTTSTimer = null }
            earlySpokenSentCount = Math.min(sentences.length, 2)
            _playTTS(sentences.slice(0, earlySpokenSentCount).join(' '))
          }
        }
      }

      const splitSentences = (t) =>
        t.split(/(?<=[.!?।॥])\s+/).map(s => s.trim()).filter(Boolean)

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buf += decoder.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop()

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          let event
          try { event = JSON.parse(line.slice(6)) } catch { continue }

          if (sessionIdRef.current !== requestSid) {
            reader.cancel()
            return
          }

          if (event.type === 'meta') {
            const isGuided = !!(event.options || event.confirm_action)
            streamOptions = event.options || null
            setMessages(prev => {
              const freshFields = event.confirmation_fields || null
              return prev.map(m => {
                if (m.id === botId) {
                  return { ...m, sources: event.sources || [], followups: event.followups || [], open_upload: event.open_upload, options: event.options || null, confirm_action: event.confirm_action || false, guided: isGuided, confirmation_fields: freshFields, missing_fields_form: event.missing_fields_form }
                }
                if (freshFields && m.confirmation_fields) {
                  return { ...m, confirmation_fields: freshFields }
                }
                return m
              })
            })

          } else if (event.type === 'token') {
            fullText += event.text
            setMessages(prev => prev.map(m =>
              m.id === botId ? { ...m, content: fullText } : m
            ))

            // ── Early TTS ────────────────────────────────────────────────
            if (!earlyTTSFired && (voiceResponseEnabled || fromVoice)) {
              if (firstTokenTime === null) {
                // First token received — start a 350ms grace timer.
                // If a sentence boundary arrives before the timer fires,
                // maybeFireEarlyTTS() will fire immediately and cancel the timer.
                firstTokenTime = performance.now()
                earlyTTSTimer = setTimeout(() => {
                  // Grace period elapsed — speak whatever text we have so far
                  if (earlyTTSFired) return
                  const cleaned = fullText.replace(/<think>[\s\S]*?<\/think>/g, '').trim()
                  if (!cleaned) return
                  earlyTTSFired = true
                  earlyTTSTimer = null
                  // Take up to first 2 sentences if boundaries exist, else first ~150 chars
                  const hasBoundary = /[.!?।॥]/.test(cleaned)
                  if (hasBoundary) {
                    const sentences = splitSentences(cleaned)
                    earlySpokenSentCount = Math.min(sentences.length, 2)
                    _playTTS(sentences.slice(0, earlySpokenSentCount).join(' '))
                  } else {
                    earlySpokenSentCount = 0
                    _playTTS(cleaned.slice(0, 200))
                  }
                }, 350)
              }
              // Also try to fire immediately if we already have a sentence boundary
              maybeFireEarlyTTS()
            }

          } else if (event.type === 'replace') {
            fullText = event.text
            setMessages(prev => prev.map(m =>
              m.id === botId ? { ...m, content: event.text } : m
            ))

          } else if (event.type === 'title') {
            setSessions(prev => prev.map(s =>
              s.id === requestSid ? { ...s, title: event.title } : s
            ))

          } else if (event.type === 'error') {
            if (earlyTTSTimer) { clearTimeout(earlyTTSTimer); earlyTTSTimer = null }
            setMessages(prev => prev.map(m =>
              m.id === botId
                ? { ...m, content: event.message || 'Something went wrong.', streaming: false }
                : m
            ))

          } else if (event.type === 'done') {
            if (earlyTTSTimer) { clearTimeout(earlyTTSTimer); earlyTTSTimer = null }
            setMessages(prev => prev.map(m =>
              m.id === botId ? { ...m, streaming: false, elapsed_ms: event.elapsed_ms } : m
            ))

            if (voiceResponseEnabled || fromVoice) {
              const cleaned = fullText.replace(/<think>[\s\S]*?<\/think>/g, '').trim()
              const sentences = splitSentences(cleaned)

              if (!earlyTTSFired) {
                // Response was short / no sentence boundary mid-stream — speak it all now
                speakReply(fullText, streamOptions)
              } else {
                // Speak remaining sentences (after what was already spoken early)
                // + options if present
                const remaining = sentences.slice(earlySpokenSentCount)
                const optSentence = _optionsSentence(streamOptions)
                const remainText = [...remaining.slice(0, 2), optSentence].filter(Boolean).join(' ')
                if (remainText.trim()) _playTTS(remainText)
              }
            }
          }
        }
      }

    } catch (err) {
      console.error('[sendMessage]', err)
      if (sessionIdRef.current !== requestSid) return
      setMessages(prev => prev.map(m =>
        m.id === botId
          ? { ...m, content: 'Something went wrong. Please make sure the backend is running.', streaming: false }
          : m
      ))
    } finally {
      setLoading(false)
    }
  }

  const { upload: encryptedUpload } = useDocumentUpload()
  const { authorizeAndSend, loading: agentLoading, error: agentError } = useAgentFileAccess()

  // Called when user sends message with attached files
  // Step 1: show consent modal — actual processing happens after password entry
  async function handleFileUpload(fileList, messageText = '') {
    setConsentError(null)
    setAgentConsent({ fileList, messageText })
  }

  // Step 2: user entered password — encrypt+store + send to agent
  async function handleAgentConsent(password) {
    if (!agentConsent) return
    setConsentError(null)
    const { fileList, messageText } = agentConsent

    if (!started) setStarted(true)

    const fileNames = fileList.map(f => f.name).join(', ')
    const label = messageText.trim()
      ? `📎 ${fileNames} — "${messageText.trim()}"`
      : `📎 ${fileNames}`
    setMessages(prev => [...prev, { id: nextId(), role: 'user', content: label }])

    const botMessages = []

    const detectDocType = (filename) => {
      const name = filename.toLowerCase()
      if (name.includes('aadhaar') || name.includes('aadhar')) return 'aadhaar'
      if (name.includes('driving') || name.includes('license') || name.includes('licence') || name.includes('dl')) return 'driving_license'
      if (name.includes('photo') || name.includes('photograph') || name.includes('pic') || name.includes('selfie')) return 'photograph'
      if (messageText) {
        const msg = messageText.toLowerCase()
        if (msg.includes('aadhaar') || msg.includes('aadhar')) return 'aadhaar'
        if (msg.includes('driving') || msg.includes('license') || msg.includes('dl')) return 'driving_license'
        if (msg.includes('photo') || msg.includes('photograph')) return 'photograph'
      }
      return 'aadhaar'
    }

    let allOk = true
    for (const file of fileList) {
      const docType = detectDocType(file.name)

      // 1. Encrypt and store in Supabase (zero-knowledge)
      const uploaded = await encryptedUpload(file, () => {
        showToast('Session expired — please sign in again.')
        handleLogout()
      })
      if (!uploaded) {
        botMessages.push(`❌ ${file.name} — encryption/upload failed.`)
        allOk = false
        continue
      }

      // 2. Authorize agent access with password + send decrypted file to agent
      const result = await authorizeAndSend(
        { file, docType, message: messageText, sessionId },
        password,
      )

      if (!result) {
        // Password was wrong — stop everything, show error in modal
        setConsentError(agentError || 'Incorrect password. Agent access denied.')
        // Remove the user message we just added since we're aborting
        setMessages(prev => prev.slice(0, -1))
        return
      }

      botMessages.push({
        msg: result.agentMessage,
        requiresCompletion: result.data?.requires_completion,
        missingFieldsForm: result.data?.missing_fields_form
      })
    }

    // All files processed — close modal and show responses
    setAgentConsent(null)
    setConsentError(null)
    
    // Check if any results require manual completion
    const firstResultWithMissingFields = botMessages.find(m => m.requiresCompletion)
    
    setMessages(prev => [...prev, {
      id: nextId(), role: 'bot',
      content: botMessages.map(m => m.msg).join('\n\n'),
      sources: [], followups: [],
      missing_fields_form: firstResultWithMissingFields?.missingFieldsForm || null
    }])
  }

  return (
    <>

      {page === 'home' && <Home onRobotClick={() => setShowAuth(true)} />}
      {showAuth && (
        <AuthModal onClose={() => setShowAuth(false)} onLogin={handleLogin} />
      )}
      {page === 'chat' && (
        <SpotlightBackground>
          <div className="flex w-full min-h-[100svh] transition-colors duration-300"
            style={{ fontFamily: 'Inter, sans-serif' }}>

            {/* Sidebar */}
            <ChatSidebar
              sessions={sessions}
              activeId={sessionId}
              onSelect={switchSession}
              onNew={createNewSession}
              onDelete={deleteSession}
              collapsed={!sidebarOpen}
              onToggle={() => setSidebarOpen(p => !p)}
              newDisabled={!started && messages.length === 0}
            />

            {/* Toast */}
            {toast && (
              <div className={cn(
                'fixed top-4 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-xl text-sm font-medium shadow-lg transition-all',
                toast.type === 'error'
                  ? 'bg-rose-500/20 border border-rose-500/30 text-rose-300'
                  : 'bg-emerald-500/20 border border-emerald-500/30 text-emerald-300'
              )}>
                {toast.msg}
              </div>
            )}

            {/* Main area — shifts right when sidebar open on desktop */}
            <div className={cn(
              'flex flex-col flex-1 min-h-[100svh] transition-all duration-200',
              sidebarOpen ? 'md:ml-60' : 'ml-0'
            )}>

              {/* Top bar */}
              <div className={cn(
                'fixed top-0 right-0 z-30 flex items-center justify-between gap-2 px-3 sm:px-4 py-3 bg-[#050508]/80 backdrop-blur-md border-b border-white/[0.06] transition-all duration-200',
                sidebarOpen ? 'md:left-60 left-0' : 'left-0'
              )}>
                {/* Left: Title */}
                <span className="text-white/70 text-xs sm:text-sm font-semibold tracking-widest uppercase whitespace-nowrap ml-8 sm:ml-0">
                  PAN Assistant
                </span>

                {/* Right: Controls */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  {/* ── Language switcher ─────────────────────────────── */}
                  <div className="flex items-center gap-0.5 bg-white/[0.04] border border-white/[0.08] rounded-lg p-0.5">
                    {[
                      { code: 'en', label: 'EN' },
                      { code: 'hi', label: 'हिं' },
                      { code: 'ta', label: 'தமி' },
                    ].map(({ code, label }) => (
                      <button
                        key={code}
                        onClick={() => {
                          setLanguage(code)
                          if (typeof window !== 'undefined') localStorage.setItem('pan_lang', code)
                        }}
                        className={cn(
                          'px-2 sm:px-2.5 py-1 rounded-md text-[10px] sm:text-xs font-semibold transition-all whitespace-nowrap',
                          language === code
                            ? 'bg-purple-600 text-white shadow-sm'
                            : 'text-white/40 hover:text-white/70'
                        )}
                        title={code === 'en' ? 'English' : code === 'hi' ? 'Hindi' : 'Tamil'}
                      >
                        {label}
                      </button>
                    ))}
                  </div>

                  {/* ── Voice Response Toggle ─────────────────────────── */}
                  <button
                    onClick={toggleVoiceResponse}
                    className={cn(
                      'flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1.5 rounded-lg text-[10px] sm:text-xs font-semibold transition-all whitespace-nowrap',
                      voiceResponseEnabled
                        ? 'bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/30'
                        : 'bg-white/[0.04] border border-white/[0.08] text-white/40 hover:text-white/70 hover:border-white/20'
                    )}
                    title={voiceResponseEnabled ? 'Voice responses enabled - Click to disable' : 'Voice responses disabled - Click to enable'}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="flex-shrink-0">
                      {voiceResponseEnabled ? (
                        <>
                          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
                          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                          <line x1="12" y1="19" x2="12" y2="22"/>
                        </>
                      ) : (
                        <>
                          <line x1="2" y1="2" x2="22" y2="22"/>
                          <path d="M18.89 13.23A7.12 7.12 0 0 0 19 12v-2"/>
                          <path d="M5 10v2a7 7 0 0 0 12 5"/>
                          <path d="M15 9.34V5a3 3 0 0 0-5.68-1.33"/>
                          <path d="M9 9v3a3 3 0 0 0 5.12 2.12"/>
                          <line x1="12" y1="19" x2="12" y2="22"/>
                        </>
                      )}
                    </svg>
                    <span className="hidden md:inline">
                      {voiceResponseEnabled ? 'Voice On' : 'Voice Off'}
                    </span>
                  </button>

                  {user && (
                    <>
                      {/* User email - hidden on small screens */}
                      <span className="text-white/60 text-xs hidden lg:block max-w-[120px] truncate">
                        {user.display_name || user.email}
                      </span>
                      
                      {/* Documents button */}
                      <button
                        onClick={() => setDocsOpen(true)}
                        className="relative flex items-center gap-1 sm:gap-1.5 text-[10px] sm:text-xs text-white/50 hover:text-white border border-white/[0.1] hover:border-white/30 px-2 sm:px-3 py-1.5 rounded-lg transition-all whitespace-nowrap"
                        title="My encrypted documents"
                      >
                        <FolderLock size={12} className="flex-shrink-0" />
                        <span className="hidden md:inline">Docs</span>
                        {docCount > 0 && (
                          <span className="absolute -top-1.5 -right-1.5 min-w-[16px] h-4 px-1 rounded-full bg-emerald-500 text-white text-[9px] font-bold flex items-center justify-center leading-none">
                            {docCount > 99 ? '99+' : docCount}
                          </span>
                        )}
                      </button>
                      
                      {/* Sign out button */}
                      <button 
                        onClick={handleLogout}
                        className="text-[10px] sm:text-xs text-white/60 hover:text-white border border-white/20 hover:border-white/40 px-2 sm:px-3 py-1.5 rounded-lg transition-all whitespace-nowrap"
                      >
                        <span className="hidden sm:inline">Sign out</span>
                        <span className="sm:hidden">Out</span>
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Scrollable messages */}
              <div className="flex flex-col flex-1 pt-20 pb-40 px-4 sm:px-6">
                <div className="w-full max-w-2xl mx-auto flex flex-col flex-1">

                  {/* Landing */}
                  {!started && (
                    <div className="flex flex-col items-center justify-center flex-1 text-center gap-4 min-h-[60vh]">
                      <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight shiny-text"
                        style={{ fontFamily: 'Syne, sans-serif' }}>
                        {language === 'ta' ? 'நான் உங்களுக்கு எப்படி உதவலாம்?' : language === 'hi' ? 'मैं आपकी कैसे मदद करूँ?' : 'What can I help you with?'}
                      </h2>
                      <p className="text-sm max-w-sm mx-auto leading-relaxed text-neutral-500">
                        {language === 'ta'
                          ? 'PAN Card, Aadhaar இணைப்பு, TAN, TDS அல்லது ஆவண தேவைகள் பற்றி கேளுங்கள்.'
                          : language === 'hi'
                          ? 'PAN Card, Aadhaar लिंकिंग, TAN, TDS या दस्तावेज़ आवश्यकताओं के बारे में पूछें।'
                          : 'Ask me anything about PAN cards, Aadhaar linking, TAN, TDS, or document requirements.'
                        }
                      </p>
                    </div>
                  )}

                  {/* Messages */}
                  <div className="space-y-5 sm:space-y-6">
                    {messages.map(msg => (
                      <Message key={msg.id} msg={msg} language={language} onFollowup={(q, msgId) => {
                        // q can be a string or { command, display } object from Save All
                        if (q && typeof q === 'object' && q.command) {
                          // Patch the source message's confirmation_fields with the saved values
                          // so if the panel re-mounts it shows the updated data, not stale fields
                          if (msgId && q.updatedFields) {
                            setMessages(prev => prev.map(m =>
                              m.id === msgId
                                ? { ...m, confirmation_fields: q.updatedFields }
                                : m
                            ))
                          }
                          sendMessage(q.command, { displayText: q.display })
                        } else {
                          if (msgId) setMessages(prev => prev.map(m => m.id === msgId ? { ...m, followupUsed: true } : m))
                          sendMessage(q)
                        }
                      }} />
                    ))}
                    <div ref={bottomRef} />
                  </div>
                </div>
              </div>

              {/* Fixed input — anchored to main area */}
              <div
                className={cn(
                  'fixed bottom-0 right-0 z-20 flex justify-center px-4 sm:px-6 pb-4 sm:pb-6 pt-3 bg-gradient-to-t from-[#050508] via-[#050508]/90 to-transparent transition-all duration-200',
                  sidebarOpen ? 'md:left-60 left-0' : 'left-0'
                )}
                style={{ paddingBottom: 'max(1rem, env(safe-area-inset-bottom))' }}
              >
                <div className="w-full max-w-2xl">
                  <PromptInputBox
                    onSend={(msg, files) => {
                      if (files?.length) {
                        handleFileUpload(files, msg || '')
                      } else if (msg?.trim()) {
                        sendMessage(msg.trim())
                      }
                    }}
                    onVoiceResponse={(transcript, errorMsg, prebuiltReply) => {
                      if (transcript?.trim()) {
                        // Auto-enable voice responses when user speaks
                        if (!voiceResponseEnabled) {
                          console.log('[VOICE] Auto-enabling voice responses after microphone use')
                          setVoiceResponseEnabled(true)
                          localStorage.setItem('voice_response_enabled', 'true')
                        }
                        
                        if (prebuiltReply) {
                          if (!started) setStarted(true)
                          setMessages(prev => [
                            ...prev,
                            { id: nextId(),     role: 'user', content: transcript },
                            { id: nextId(), role: 'bot',  content: prebuiltReply, sources: [], followups: [] },
                          ])
                          // Speak the prebuilt reply too
                          speakReply(prebuiltReply)
                        } else {
                          sendMessage(transcript.trim(), { fromVoice: true })
                        }
                      }
                    }}
                    sessionId={sessionId}
                    userContext=""
                    isLoading={loading}
                    placeholder={
                      language === 'ta'
                        ? 'PAN Card பற்றி கேளுங்கள் அல்லது ஆவணங்களை இணைக்கவும்...'
                        : language === 'hi'
                        ? 'PAN Card के बारे में पूछें या दस्तावेज़ संलग्न करें...'
                        : 'Ask about PAN cards, or attach documents with your details...'
                    }
                    draftValue={drafts[sessionId] ?? ''}
                    onDraftChange={(val) =>
                      setDrafts(prev => ({ ...prev, [sessionId]: val }))
                    }
                    language={language}
                  />
                </div>
              </div>

            </div>
          </div>
        </SpotlightBackground>
      )}

      {/* Encrypted documents panel */}
      <DocumentsPanel
        open={docsOpen}
        onClose={() => setDocsOpen(false)}
        onNotLoggedIn={() => {
          setDocsOpen(false)
          showToast('Session expired — please sign in again.')
          handleLogout()
        }}
      />

      {/* Agent consent modal — shown when files are attached */}
      {agentConsent && (
        <AgentConsentModal
          files={agentConsent.fileList}
          onConfirm={handleAgentConsent}
          onCancel={() => { setAgentConsent(null); setConsentError(null) }}
          error={consentError}
          loading={agentLoading}
        />
      )}
    </>
  )
}
