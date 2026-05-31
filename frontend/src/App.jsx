import React, { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
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

function Message({ msg, onFollowup }) {
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

        {/* ── Confirm action buttons (Yes, proceed / No, change something) ── */}
        {!msg.streaming && msg.confirm_action && confirmUsed === null && (
          <div className="flex gap-3 pt-4">
            <button
              onClick={() => { setConfirmUsed('yes'); onFollowup('Yes, proceed', msg.id) }}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/25 hover:border-emerald-400/60 active:scale-95 transition-all"
            >
              <span className="text-emerald-400">✓</span> Yes, proceed
            </button>
            <button
              onClick={() => { setConfirmUsed('no'); onFollowup('No, I need to change something', msg.id) }}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-white/[0.04] border border-white/20 text-white/70 hover:bg-white/[0.08] hover:border-white/30 active:scale-95 transition-all"
            >
              <span className="text-white/40">✎</span> Change something
            </button>
          </div>
        )}

        {/* Confirm used — show greyed state */}
        {!msg.streaming && msg.confirm_action && confirmUsed !== null && (
          <div className="flex gap-3 pt-4 opacity-40 pointer-events-none">
            <div className={cn(
              "flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold border",
              confirmUsed === 'yes'
                ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-300"
                : "bg-white/[0.04] border-white/20 text-white/70"
            )}>
              {confirmUsed === 'yes' ? <><span className="text-emerald-400">✓</span> Yes, proceed</> : <><span className="text-white/40">✎</span> Change something</>}
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

        {/* Followup buttons */}
        {!msg.streaming && msg.followups?.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-3">
            {msg.followups.map((q, i) => (
              <button key={i}
                onClick={() => {
                  if (usedFollowup !== null) return
                  setUsedFollowup(i)
                  onFollowup(q, msg.id)
                }}
                disabled={usedFollowup !== null || msg.followupUsed}
                className={`text-xs border rounded-full px-3 py-1.5 transition-all flex items-center gap-1
                  ${(usedFollowup === null && !msg.followupUsed)
                    ? 'text-neutral-400 hover:text-white border-neutral-700 hover:border-neutral-500 hover:bg-neutral-800 active:scale-95 cursor-pointer'
                    : usedFollowup === i
                      ? 'text-white border-purple-500/50 bg-neutral-800 cursor-default'
                      : 'text-neutral-600 border-neutral-800 cursor-not-allowed opacity-40'
                  }`}>
                <ChevronRight size={10} className={usedFollowup === null ? "text-purple-400" : usedFollowup === i ? "text-purple-400" : "text-neutral-600"} />
                {q}
              </button>
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
  const [agentConsent, setAgentConsent] = useState(null)
  const [consentError, setConsentError] = useState(null)
  // Active guided question — shown as sliding panel, not in message list
  const [guidedQuestion, setGuidedQuestion] = useState(null) // { id, content, options, confirm_action }
  const [guidedDir, setGuidedDir] = useState(1) // 1 = slide in from right, -1 = from left
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
  const audioPlayerRef = useRef(null)
  const bottomRef = useRef(null)

  function showToast(msg, type = 'error') {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 4000)
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
      // Auto-load most recent session if exists
      if (data.sessions?.length) {
        await switchSession(data.sessions[0].id)
      }
    } catch { /* ignore */ }
  }

  async function createNewSession() {
    try {
      const res = await fetch('/api/chat/sessions', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      })
      const data = await res.json()
      setSessions(prev => [data.session, ...prev])
      setSessionId(data.session.id)
      sessionIdRef.current = data.session.id
      setMessages([])
      setGuidedQuestion(null)  // Clear any guided questions from previous session
      setStarted(false)
    } catch { /* ignore */ }
  }

  async function switchSession(id) {
    setSessionId(id)
    sessionIdRef.current = id
    setGuidedQuestion(null)
    setStarted(false)
    setMessages([])  // clear immediately before async load
    setLoading(false)
    try {
      const res = await fetch(`/api/chat/history/${id}`, { credentials: 'include' })
      if (!res.ok) return
      const data = await res.json()
      // Guard: only set messages if this session is still active
      if (sessionIdRef.current !== id) return
      if (data.history?.length) {
        setStarted(true)
        setMessages(data.history.map((m, i) => ({
          id: i, role: m.role === 'assistant' ? 'bot' : m.role,
          content: m.content, sources: [], followups: [],
        })))
      }
    } catch { /* ignore */ }
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

  // ── TTS playback for voice replies ─────────────────────────────
  async function speakReply(text) {
    if (!text?.trim()) return
    // Strip markdown so Kokoro reads clean prose
    const clean = text
      .replace(/<think>[\s\S]*?<\/think>/g, '')
      .replace(/\*\*/g, '').replace(/\*/g, '')
      .replace(/#{1,6}\s/g, '')
      .replace(/`+/g, '')
      .replace(/[-–—•]\s+/g, '')
      .replace(/\[.*?\]\(.*?\)/g, '')
      .replace(/\n+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
    if (!clean) return
    try {
      const form = new FormData()
      form.append('text', clean)
      const res = await fetch('/api/voice/tts', {
        method: 'POST',
        credentials: 'include',
        body: form,
      })
      if (!res.ok) return
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      if (audioPlayerRef.current) {
        audioPlayerRef.current.src = url
        audioPlayerRef.current.play().catch(() => {})
      }
    } catch { /* silent — TTS is optional */ }
  }

  // ── Messaging ───────────────────────────────────────────────────
  async function sendMessage(question, { fromVoice = false } = {}) {
    if (!question.trim() || loading) return

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
    setMessages(prev => [...prev, { id: userMsgId, role: 'user', content: question, _sid: requestSid }])
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
        setMessages(prev => prev.map(m =>
          m.id === botId ? { ...m, content: reply, sources: data.sources || [], followups: data.followups || [], options: data.options || null, confirm_action: data.confirm_action || false, guided: !!(data.options || data.confirm_action), streaming: false, elapsed_ms: data.elapsed_ms } : m
        ))
        if (fromVoice && reply) speakReply(reply)
        return
      }

      // Consume SSE stream
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      let fullText = ''

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
            setMessages(prev => prev.map(m =>
              m.id === botId
                ? { ...m, sources: event.sources || [], followups: event.followups || [], open_upload: event.open_upload, options: event.options || null, confirm_action: event.confirm_action || false, guided: isGuided }
                : m
            ))

          } else if (event.type === 'token') {
            fullText += event.text
            const snapshot = fullText
            setMessages(prev => prev.map(m =>
              m.id === botId ? { ...m, content: snapshot } : m
            ))

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
            setMessages(prev => prev.map(m =>
              m.id === botId
                ? { ...m, content: event.message || 'Something went wrong.', streaming: false }
                : m
            ))

          } else if (event.type === 'done') {
            // Route guided messages to the sliding panel
            setMessages(prev => {
              const msg = prev.find(m => m.id === botId)
              if (msg && msg.guided && msg.options) {
                setGuidedDir(1)
                setGuidedQuestion({ id: msg.id, content: msg.content, options: msg.options, confirm_action: msg.confirm_action || false })
                return prev.filter(m => m.id !== botId)
              }
              return prev.map(m => m.id === botId ? { ...m, streaming: false, elapsed_ms: event.elapsed_ms } : m)
            })
            if (fromVoice && fullText) speakReply(fullText)
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

      botMessages.push(result.agentMessage)
    }

    // All files processed — close modal and show responses
    setAgentConsent(null)
    setConsentError(null)
    setMessages(prev => [...prev, {
      id: nextId(), role: 'bot',
      content: botMessages.join('\n\n'),
      sources: [], followups: [],
    }])
  }

  return (
    <>
      {/* Hidden audio player for TTS voice replies */}
      <audio ref={audioPlayerRef} className="hidden" />

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
                'fixed top-0 right-0 z-30 flex items-center px-4 sm:px-6 py-4 transition-all duration-200',
                sidebarOpen ? 'md:left-60 left-0' : 'left-0'
              )}>
                <span className="text-white/70 text-sm font-semibold tracking-widest uppercase mr-auto ml-8">PAN Assistant</span>

                {/* ── Language switcher ─────────────────────────────── */}
                <div className="flex items-center gap-0.5 mr-3 bg-white/[0.04] border border-white/[0.08] rounded-lg p-0.5">
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
                        'px-2.5 py-1 rounded-md text-xs font-semibold transition-all',
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

                {user && (
                  <div className="flex items-center gap-3">
                    <span className="text-white/60 text-sm hidden sm:block">
                      {user.display_name || user.email}
                    </span>
                    <button
                      onClick={() => setDocsOpen(true)}
                      className="flex items-center gap-1.5 text-sm text-white/50 hover:text-white border border-white/[0.1] hover:border-white/30 px-3 py-1.5 rounded-lg transition-all"
                      title="My encrypted documents"
                    >
                      <FolderLock size={13} />
                      <span className="hidden sm:inline">Documents</span>
                    </button>
                    <button onClick={handleLogout}
                      className="text-sm text-white/60 hover:text-white border border-white/20 hover:border-white/40 px-4 py-1.5 rounded-lg transition-all">
                      Sign out
                    </button>
                  </div>
                )}
              </div>

              {/* Scrollable messages */}
              <div className="flex flex-col flex-1 pt-16 pb-40 px-4 sm:px-6">
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
                      <Message key={msg.id} msg={msg} onFollowup={(q, msgId) => {
                        if (msgId) setMessages(prev => prev.map(m => m.id === msgId ? { ...m, followupUsed: true } : m))
                        sendMessage(q)
                      }} />
                    ))}
                    <div ref={bottomRef} />
                  </div>
                </div>
              </div>

              {/* Guided flow panel — slides horizontally between questions */}
              <AnimatePresence mode="wait">
                {guidedQuestion && (
                  <div
                    className={cn(
                      'fixed bottom-0 right-0 z-25 flex justify-center px-4 sm:px-6 pb-36 sm:pb-40 transition-all duration-200',
                      sidebarOpen ? 'md:left-60 left-0' : 'left-0'
                    )}
                  >
                    <div className="w-full max-w-2xl overflow-hidden">
                      <motion.div
                        key={guidedQuestion.id}
                        initial={{ x: guidedDir * 60, opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        exit={{ x: guidedDir * -60, opacity: 0 }}
                        transition={{ duration: 0.28, ease: [0.32, 0.72, 0, 1] }}
                        className="bg-[#0f0f18]/95 border border-white/[0.08] rounded-2xl px-5 py-4 backdrop-blur-sm shadow-2xl"
                      >
                        <div className="text-sm text-white/90 mb-3 leading-relaxed">
                          {renderMarkdown(guidedQuestion.content)}
                        </div>
                        {guidedQuestion.options && guidedQuestion.options.type === 'email_confirm' && (
                          <EmailConfirmOptions
                            opts={guidedQuestion.options}
                            onSelect={(val) => { setGuidedDir(1); setGuidedQuestion(null); sendMessage(val) }}
                          />
                        )}
                        {guidedQuestion.options && guidedQuestion.options.type !== 'email_confirm' && (
                          <GuidedOptions
                            opts={guidedQuestion.options}
                            onSelect={(val) => { setGuidedDir(1); setGuidedQuestion(null); sendMessage(val) }}
                          />
                        )}
                        {guidedQuestion.confirm_action && (
                          <GuidedConfirm
                            onYes={() => { setGuidedDir(1); setGuidedQuestion(null); sendMessage('Yes, proceed') }}
                            onNo={() => { setGuidedDir(1); setGuidedQuestion(null); sendMessage('No, I need to change something') }}
                          />
                        )}
                      </motion.div>
                    </div>
                  </div>
                )}
              </AnimatePresence>

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
                        if (prebuiltReply) {
                          if (!started) setStarted(true)
                          setMessages(prev => [
                            ...prev,
                            { id: nextId(),     role: 'user', content: transcript },
                            { id: nextId(), role: 'bot',  content: prebuiltReply, sources: [], followups: [] },
                          ])
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
