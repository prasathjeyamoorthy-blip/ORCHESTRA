import React from "react"
import * as TooltipPrimitive from "@radix-ui/react-tooltip"
import * as DialogPrimitive from "@radix-ui/react-dialog"
import { ArrowUp, Paperclip, Square, X, StopCircle, Mic, Globe, BrainCog, FolderCode } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"

const cn = (...classes) => classes.filter(Boolean).join(" ")

const styles = `
*:focus-visible { outline-offset: 0 !important; }
textarea::-webkit-scrollbar { width: 6px; }
textarea::-webkit-scrollbar-track { background: transparent; }
textarea::-webkit-scrollbar-thumb { background-color: #444444; border-radius: 3px; }
textarea::-webkit-scrollbar-thumb:hover { background-color: #555555; }
`
if (typeof document !== "undefined") {
  const s = document.createElement("style")
  s.innerText = styles
  document.head.appendChild(s)
}

// ── Textarea ──────────────────────────────────────────────────────
const Textarea = React.forwardRef(({ className, ...props }, ref) => (
  <textarea
    className={cn(
      "flex w-full rounded-md border-none bg-transparent px-3 py-2.5 text-base text-gray-100 placeholder:text-gray-400 focus-visible:outline-none focus-visible:ring-0 disabled:cursor-not-allowed disabled:opacity-50 min-h-[44px] resize-none",
      className
    )}
    ref={ref}
    rows={1}
    {...props}
  />
))
Textarea.displayName = "Textarea"

// ── Tooltip ───────────────────────────────────────────────────────
const TooltipProvider = TooltipPrimitive.Provider
const Tooltip = TooltipPrimitive.Root
const TooltipTrigger = TooltipPrimitive.Trigger
const TooltipContent = React.forwardRef(({ className, sideOffset = 4, ...props }, ref) => (
  <TooltipPrimitive.Content
    ref={ref}
    sideOffset={sideOffset}
    className={cn(
      "z-50 overflow-hidden rounded-md border border-[#333333] bg-[#1F2023] px-3 py-1.5 text-sm text-white shadow-md animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95",
      className
    )}
    {...props}
  />
))
TooltipContent.displayName = TooltipPrimitive.Content.displayName

// ── Dialog ────────────────────────────────────────────────────────
const Dialog = DialogPrimitive.Root
const DialogPortal = DialogPrimitive.Portal

const DialogOverlay = React.forwardRef(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      "fixed inset-0 z-50 bg-black/60 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
      className
    )}
    {...props}
  />
))
DialogOverlay.displayName = DialogPrimitive.Overlay.displayName

const DialogContent = React.forwardRef(({ className, children, ...props }, ref) => (
  <DialogPortal>
    <DialogOverlay />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        "fixed left-[50%] top-[50%] z-50 grid w-full max-w-[90vw] md:max-w-[800px] translate-x-[-50%] translate-y-[-50%] gap-4 border border-[#333333] bg-[#1F2023] p-0 shadow-xl duration-300 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 rounded-2xl",
        className
      )}
      {...props}
    >
      {children}
      <DialogPrimitive.Close className="absolute right-4 top-4 z-10 rounded-full bg-[#2E3033]/80 p-2 hover:bg-[#2E3033] transition-all">
        <X className="h-5 w-5 text-gray-200 hover:text-white" />
        <span className="sr-only">Close</span>
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </DialogPortal>
))
DialogContent.displayName = DialogPrimitive.Content.displayName

const DialogTitle = React.forwardRef(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn("text-lg font-semibold leading-none tracking-tight text-gray-100", className)}
    {...props}
  />
))
DialogTitle.displayName = DialogPrimitive.Title.displayName

// ── Button ────────────────────────────────────────────────────────
const Button = React.forwardRef(({ className, variant = "default", size = "default", ...props }, ref) => {
  const variantClasses = {
    default: "bg-white hover:bg-white/80 text-black",
    outline: "border border-[#444444] bg-transparent hover:bg-[#3A3A40]",
    ghost: "bg-transparent hover:bg-[#3A3A40]",
  }
  const sizeClasses = {
    default: "h-10 px-4 py-2",
    sm: "h-8 px-3 text-sm",
    lg: "h-12 px-6",
    icon: "h-8 w-8 rounded-full aspect-[1/1]",
  }
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50",
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      ref={ref}
      {...props}
    />
  )
})
Button.displayName = "Button"

// ── VoiceRecorder ─────────────────────────────────────────────────
function VoiceRecorder({ isRecording, analyser, onStopRecording, bars = 40 }) {
  const [time, setTime] = React.useState(0)
  const [heights, setHeights] = React.useState(() => Array(bars).fill(4))
  const timerRef = React.useRef(null)
  const rafRef = React.useRef(null)

  // Timer
  React.useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => setTime(t => t + 1), 1000)
    } else {
      clearInterval(timerRef.current)
      setTime(0)
    }
    return () => clearInterval(timerRef.current)
  }, [isRecording])

  // Live frequency visualiser driven by AnalyserNode
  React.useEffect(() => {
    if (!isRecording || !analyser) return

    const dataArr = new Uint8Array(analyser.frequencyBinCount)
    const SPEECH_THRESHOLD = 20  // avg frequency energy to consider as voice

    const draw = () => {
      analyser.getByteFrequencyData(dataArr)
      const avg = dataArr.reduce((a, b) => a + b, 0) / dataArr.length
      const isSpeaking = avg > SPEECH_THRESHOLD

      const step = Math.floor(dataArr.length / bars)
      const newHeights = Array.from({ length: bars }, (_, i) => {
        if (!isSpeaking) return 4  // flat when silent
        const bin = dataArr[i * step] ?? 0
        return Math.max(4, Math.round((bin / 255) * 100))
      })
      setHeights(newHeights)
      rafRef.current = requestAnimationFrame(draw)
    }

    rafRef.current = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(rafRef.current)
  }, [isRecording, analyser, bars])

  const formatTime = (s) =>
    `${Math.floor(s / 60).toString().padStart(2, "0")}:${(s % 60).toString().padStart(2, "0")}`

  if (!isRecording) return null

  return (
    <div className="flex flex-col items-center justify-center w-full py-3 gap-3">
      {/* Timer + stop hint */}
      <div className="flex items-center gap-2">
        <div className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
        <span className="font-mono text-sm text-white/70">{formatTime(time)}</span>
        <button
          onClick={onStopRecording}
          className="ml-2 text-xs text-white/30 hover:text-white/60 transition-colors"
        >
          tap to stop
        </button>
      </div>

      {/* Live frequency bars */}
      <div className="w-full h-12 flex items-end justify-center gap-[2px] px-4">
        {heights.map((h, i) => {
          // Colour: purple in the middle, fading to blue/pink at edges
          const mid = bars / 2
          const dist = Math.abs(i - mid) / mid          // 0 at centre, 1 at edges
          const r = Math.round(139 + dist * 80)         // 139→219
          const g = Math.round(92  - dist * 40)         // 92→52
          const b = Math.round(246 - dist * 60)         // 246→186
          return (
            <div
              key={i}
              style={{
                height: `${h}%`,
                backgroundColor: `rgb(${r},${g},${b})`,
                transition: "height 60ms ease-out",
                width: "3px",
                borderRadius: "2px",
                opacity: 0.85 + dist * 0.15,
              }}
            />
          )
        })}
      </div>
    </div>
  )
}

// ── ImageViewDialog ───────────────────────────────────────────────
function ImageViewDialog({ imageUrl, onClose }) {
  if (!imageUrl) return null
  return (
    <Dialog open={!!imageUrl} onOpenChange={onClose}>
      <DialogContent className="p-0 border-none bg-transparent shadow-none max-w-[90vw] md:max-w-[800px]">
        <DialogTitle className="sr-only">Image Preview</DialogTitle>
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} transition={{ duration: 0.2 }}
          className="relative bg-[#1F2023] rounded-2xl overflow-hidden shadow-2xl">
          <img src={imageUrl} alt="Full preview" className="w-full max-h-[80vh] object-contain rounded-2xl" />
        </motion.div>
      </DialogContent>
    </Dialog>
  )
}

// ── PromptInput Context ───────────────────────────────────────────
const PromptInputContext = React.createContext({
  isLoading: false, value: "", setValue: () => {}, maxHeight: 240,
})
const usePromptInput = () => React.useContext(PromptInputContext)

// ── PromptInput ───────────────────────────────────────────────────
const PromptInput = React.forwardRef(
  ({ className, isLoading = false, maxHeight = 240, value, onValueChange, onSubmit, children, disabled = false, onDragOver, onDragLeave, onDrop }, ref) => {
    const [internal, setInternal] = React.useState(value || "")
    return (
      <TooltipProvider>
        <PromptInputContext.Provider value={{ isLoading, value: value ?? internal, setValue: onValueChange ?? setInternal, maxHeight, onSubmit, disabled: false }}>
          <div ref={ref}
            className={cn("rounded-3xl border border-[#444444] bg-[#1F2023] p-2 shadow-[0_8px_30px_rgba(0,0,0,0.24)] transition-all duration-300", isLoading && "border-red-500/70", className)}
            onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}>
            {children}
          </div>
        </PromptInputContext.Provider>
      </TooltipProvider>
    )
  }
)
PromptInput.displayName = "PromptInput"

// ── PromptInputTextarea ───────────────────────────────────────────
function PromptInputTextarea({ className, onKeyDown, disableAutosize = false, placeholder, ...props }) {
  const { value, setValue, maxHeight, onSubmit, disabled } = usePromptInput()
  const ref = React.useRef(null)

  React.useEffect(() => {
    if (disableAutosize || !ref.current) return
    ref.current.style.height = "auto"
    ref.current.style.height = typeof maxHeight === "number"
      ? `${Math.min(ref.current.scrollHeight, maxHeight)}px`
      : `min(${ref.current.scrollHeight}px, ${maxHeight})`
  }, [value, maxHeight, disableAutosize])

  return (
    <Textarea ref={ref} value={value} onChange={e => setValue(e.target.value)}
      onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onSubmit?.() } onKeyDown?.(e) }}
      className={cn("text-base", className)} disabled={disabled} placeholder={placeholder} {...props} />
  )
}

function PromptInputActions({ children, className, ...props }) {
  return <div className={cn("flex items-center gap-2", className)} {...props}>{children}</div>
}

function PromptInputAction({ tooltip, children, className, side = "top", ...props }) {
  const { disabled } = usePromptInput()
  return (
    <Tooltip {...props}>
      <TooltipTrigger asChild disabled={disabled}>{children}</TooltipTrigger>
      <TooltipContent side={side} className={className}>{tooltip}</TooltipContent>
    </Tooltip>
  )
}

function CustomDivider() {
  return (
    <div className="relative h-6 w-[1.5px] mx-1">
      <div className="absolute inset-0 bg-gradient-to-t from-transparent via-[#9b87f5]/70 to-transparent rounded-full" />
    </div>
  )
}

// ── PromptInputBox (main export) ──────────────────────────────────
export const PromptInputBox = React.forwardRef((props, ref) => {
  const { onSend = () => {}, onVoiceResponse = () => {}, isLoading = false, placeholder = "Type your message here...", className, sessionId = null, userContext = "", draftValue = "", onDraftChange = null } = props

  const [input, setInput] = React.useState(draftValue)

  // Sync input when switching sessions (draftValue changes from parent)
  const prevSessionId = React.useRef(sessionId)
  React.useEffect(() => {
    if (prevSessionId.current !== sessionId) {
      prevSessionId.current = sessionId
      setInput(draftValue)
    }
  }, [sessionId, draftValue])

  // Notify parent of every keystroke so draft is preserved
  function handleInputChange(val) {
    setInput(val)
    onDraftChange?.(val)
  }
  const [files, setFiles] = React.useState([])
  const [filePreviews, setFilePreviews] = React.useState({})
  const [selectedImage, setSelectedImage] = React.useState(null)
  const [isRecording, setIsRecording] = React.useState(false)
  const [isVoiceLoading, setIsVoiceLoading] = React.useState(false)
  const [micError, setMicError] = React.useState(null)
  const [showSearch, setShowSearch] = React.useState(false)
  const [showThink, setShowThink] = React.useState(false)
  const [showCanvas, setShowCanvas] = React.useState(false)
  const uploadRef = React.useRef(null)
  const mediaRecorderRef = React.useRef(null)
  const audioChunksRef = React.useRef([])
  const audioPlayerRef = React.useRef(null)

  const ALLOWED_TYPES = [
    'image/jpeg', 'image/png', 'image/webp',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  ]
  const MAX_SIZE = 50 * 1024 * 1024 // 50MB

  // ── Voice recording ───────────────────────────────────────────
  const silenceTimerRef = React.useRef(null)
  const hardCapTimerRef = React.useRef(null)
  const analyserRef = React.useRef(null)
  const audioCtxRef = React.useRef(null)
  const [voiceElapsed, setVoiceElapsed] = React.useState(0)
  const voiceElapsedRef = React.useRef(null)

  const startRecording = async () => {
    setMicError(null)
    try {
      // Try ideal constraints first, fall back to bare minimum
      let stream
      try {
        // First check if any audio devices exist at all
        const devices = await navigator.mediaDevices.enumerateDevices()
        const mics = devices.filter(d => d.kind === 'audioinput')
        console.log("[MIC] Available audio inputs:", mics.length, mics.map(d => d.label))

        stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: false,  // disable AGC — it's causing clipping
            sampleRate: 16000,
            channelCount: 1,
          }
        })
        console.log("[MIC] Stream tracks:", stream.getAudioTracks().map(t => `${t.label} state=${t.readyState}`))
      } catch (e1) {
        console.warn("[MIC] Ideal constraints failed:", e1.message, "— trying bare audio:true")
        try {
          stream = await navigator.mediaDevices.getUserMedia({ audio: true })
          console.log("[MIC] Fallback stream tracks:", stream.getAudioTracks().map(t => `${t.label} state=${t.readyState}`))
        } catch (e2) {
          throw e2  // re-throw to outer catch for error display
        }
      }
      audioChunksRef.current = []

      // ── Silence detection via AnalyserNode ──────────────────
      const audioCtx = new AudioContext()
      audioCtxRef.current = audioCtx
      const source = audioCtx.createMediaStreamSource(stream)
      const analyser = audioCtx.createAnalyser()
      analyser.fftSize = 512
      source.connect(analyser)
      analyserRef.current = analyser

      // Pick the best supported codec — Firefox on Linux works best with ogg/opus
      const preferredTypes = [
        "audio/ogg;codecs=opus",
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/ogg",
      ]
      const mimeType = preferredTypes.find(t => MediaRecorder.isTypeSupported(t)) || ""
      console.log("[MIC] Using mimeType:", mimeType || "(browser default)")

      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream)
      mediaRecorderRef.current = recorder

      recorder.ondataavailable = (e) => {
        // Skip tiny initialization chunks (< 100 bytes = mic warmup artifact)
        if (e.data.size > 100) {
          console.log("[MIC] data chunk:", e.data.size, "bytes")
          audioChunksRef.current.push(e.data)
        }
      }

      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        audioCtx.close()
        clearInterval(silenceTimerRef.current)
        // Guard: don't send if no audio was captured
        if (audioChunksRef.current.length === 0) {
          setMicError("No audio captured. Please speak and try again.")
          return
        }
        const blob = new Blob(audioChunksRef.current, { type: mimeType })
        if (blob.size < 1000) {
          setMicError("Recording too short. Please speak clearly and try again.")
          return
        }
        await sendVoiceToServer(blob, mimeType)
      }

      recorder.start(250)  // larger timeslice = fewer, bigger chunks
      setIsRecording(true)

      // Hard cap: stop after 30s regardless
      hardCapTimerRef.current = setTimeout(() => stopRecording(), 30_000)

      // ── Silence detection — wait 1s before starting, require speech first ──
      const dataArr = new Uint8Array(analyser.frequencyBinCount)
      let silentMs = 0
      let speechDetected = false
      let elapsedMs = 0
      const SILENCE_THRESHOLD = 8

      silenceTimerRef.current = setInterval(() => {
        elapsedMs += 500
        // Don't start detecting until 1s in (mic warmup)
        if (elapsedMs < 1000) return

        analyser.getByteFrequencyData(dataArr)
        const avg = dataArr.reduce((a, b) => a + b, 0) / dataArr.length
        if (avg >= SILENCE_THRESHOLD) {
          speechDetected = true
          silentMs = 0
        } else if (speechDetected) {
          silentMs += 500
          if (silentMs >= 3_500) {
            clearInterval(silenceTimerRef.current)
            stopRecording()
          }
        }
      }, 500)

    } catch (err) {
      console.error("Mic access denied:", err)
      if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        setMicError("No microphone found. Please connect a mic and try again.")
      } else if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setMicError("Microphone access denied. Allow mic access in your browser settings.")
      } else {
        setMicError("Could not access microphone. Please try again.")
      }
    }
  }

  const stopRecording = () => {
    clearInterval(silenceTimerRef.current)
    clearTimeout(hardCapTimerRef.current)
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop()
    }
    setIsRecording(false)
  }

  const sendVoiceToServer = async (blob, mimeType) => {
    setIsVoiceLoading(true)
    setVoiceElapsed(0)
    voiceElapsedRef.current = setInterval(() => setVoiceElapsed(s => s + 1), 1000)
    try {
      const ext = mimeType.includes("ogg") ? ".ogg" : ".webm"
      const sendMime = mimeType || "audio/webm"
      const formData = new FormData()
      formData.append("audio", blob, `voice${ext}`)

      // ── Full pipeline: STT → RAG+LLM → TTS, returns audio/wav ──
      const res = await fetch("/api/voice/speak", {
        method: "POST",
        credentials: "include",
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        console.error("Voice error:", err)
        if (err.detail?.includes("hear speech") || err.detail?.includes("make out") || res.status === 422) {
          setMicError("Couldn't hear you clearly — please speak directly into the mic and try again.")
        } else {
          setMicError(err.detail || "Could not process voice. Please try again.")
        }
        return
      }

      const contentType = res.headers.get("content-type") || ""

      // ── TTS failed fallback — JSON response with text only ───
      if (contentType.includes("application/json")) {
        const data = await res.json()
        if (data.transcript?.trim()) {
          setMicError(null)
          onVoiceResponse(data.transcript, null, data.reply || undefined)
        }
        return
      }

      // ── Normal path: audio/wav response ─────────────────────
      const transcript = decodeURIComponent(res.headers.get("X-Transcript") || "")
      const reply      = decodeURIComponent(res.headers.get("X-Reply") || "")

      // ── Play the TTS audio ───────────────────────────────────
      const audioBlob = await res.blob()
      const audioUrl  = URL.createObjectURL(audioBlob)
      if (audioPlayerRef.current) {
        audioPlayerRef.current.src = audioUrl
        audioPlayerRef.current.onended = () => URL.revokeObjectURL(audioUrl)
        audioPlayerRef.current.play().catch(e => console.error("Audio play failed:", e))
      }

      // ── Add both bubbles to the chat UI ─────────────────────
      if (transcript?.trim()) {
        setMicError(null)
        onVoiceResponse(transcript, null, reply || undefined)
      }

    } catch (err) {
      console.error("Voice send failed:", err)
    } finally {
      clearInterval(voiceElapsedRef.current)
      setIsVoiceLoading(false)
      setVoiceElapsed(0)
    }
  }

  const processFile = (file) => {
    if (!ALLOWED_TYPES.includes(file.type)) return
    if (file.size > MAX_SIZE) return
    // Allow multiple files — append instead of replace
    setFiles(prev => [...prev, file])
    if (file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = (e) => setFilePreviews(prev => ({ ...prev, [file.name]: e.target?.result }))
      reader.readAsDataURL(file)
    }
  }

  const removeFile = (name) => {
    setFiles(prev => prev.filter(f => f.name !== name))
    setFilePreviews(prev => { const n = { ...prev }; delete n[name]; return n })
  }

  const handleDrop = React.useCallback((e) => {
    e.preventDefault()
    Array.from(e.dataTransfer.files).filter(f => f.type.startsWith("image/")).slice(0, 1).forEach(processFile)
  }, [])

  const handlePaste = React.useCallback((e) => {
    const items = e.clipboardData?.items
    if (!items) return
    for (let i = 0; i < items.length; i++) {
      if (items[i].type.startsWith("image/")) {
        const f = items[i].getAsFile()
        if (f) { e.preventDefault(); processFile(f); break }
      }
    }
  }, [])

  React.useEffect(() => {
    document.addEventListener("paste", handlePaste)
    return () => document.removeEventListener("paste", handlePaste)
  }, [handlePaste])

  const handleSubmit = () => {
    if (!input.trim() && files.length === 0) return
    const prefix = showSearch ? "[Search: " : showThink ? "[Think: " : showCanvas ? "[Canvas: " : ""
    onSend(prefix ? `${prefix}${input}]` : input, [...files])
    handleInputChange(""); setFiles([]); setFilePreviews({})
  }

  const hasContent = input.trim() !== "" || files.length > 0

  return (
    <>
      {/* Hidden audio player for TTS playback */}
      <audio ref={audioPlayerRef} className="hidden" />

      <PromptInput value={input} onValueChange={handleInputChange} isLoading={isLoading} onSubmit={handleSubmit}
        className={cn("w-full bg-[#1F2023] border-[#444444]", (isRecording || isVoiceLoading) && "border-red-500/70", className)}
        disabled={isRecording || isVoiceLoading} ref={ref}
        onDragOver={e => e.preventDefault()} onDragLeave={e => e.preventDefault()} onDrop={handleDrop}>

        {files.length > 0 && !isRecording && (
          <div className="flex flex-wrap gap-2 p-0 pb-1">
            {files.map((file, idx) => (
              <div key={idx} className="relative group">
                {file.type.startsWith('image/') && filePreviews[file.name] ? (
                  <div className="w-16 h-16 rounded-xl overflow-hidden cursor-pointer relative"
                    onClick={() => setSelectedImage(filePreviews[file.name])}>
                    <img src={filePreviews[file.name]} alt={file.name} className="h-full w-full object-cover" />
                    <button onClick={e => { e.stopPropagation(); removeFile(file.name) }}
                      className="absolute top-1 right-1 rounded-full bg-black/70 p-0.5">
                      <X className="h-3 w-3 text-white" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 bg-white/[0.06] border border-white/10 rounded-xl px-3 py-2 max-w-[180px]">
                    <Paperclip className="h-4 w-4 text-white/50 flex-shrink-0" />
                    <span className="text-xs text-white/70 truncate">{file.name}</span>
                    <button onClick={() => removeFile(file.name)}
                      className="flex-shrink-0 text-white/30 hover:text-white/70">
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        <div className={cn("transition-all duration-300", isRecording ? "h-0 overflow-hidden opacity-0" : "opacity-100")}>
          <PromptInputTextarea placeholder={
            showSearch ? "Search the web..." : showThink ? "Think deeply..." : showCanvas ? "Create on canvas..." : placeholder
          } className="text-base" />
        </div>

        {isRecording && (
          <VoiceRecorder
            isRecording={isRecording}
            analyser={analyserRef.current}
            onStopRecording={stopRecording}
          />
        )}

        {isVoiceLoading && !isRecording && (
          <div className="flex items-center justify-center gap-2 py-3 text-white/50 text-sm">
            <div className="h-2 w-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: '0ms' }} />
            <div className="h-2 w-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: '150ms' }} />
            <div className="h-2 w-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: '300ms' }} />
            <span className="ml-1">Processing voice... {voiceElapsed > 0 && <span className="text-white/30 font-mono">{voiceElapsed}s</span>}</span>
          </div>
        )}

        {micError && !isRecording && !isVoiceLoading && (
          <div className="flex items-center gap-2 px-3 py-2 text-xs text-rose-400 bg-rose-500/10 rounded-xl mx-1 mb-1">
            <span>🎤 {micError}</span>
            <button onClick={() => setMicError(null)} className="ml-auto text-rose-400/60 hover:text-rose-400">✕</button>
          </div>
        )}

        <PromptInputActions className="flex items-center justify-between gap-2 p-0 pt-2">
          <div className={cn("flex items-center gap-1 transition-opacity duration-300", isRecording ? "opacity-0 invisible h-0" : "opacity-100 visible")}>

            <PromptInputAction tooltip="Attach file">
              <button onClick={() => uploadRef.current?.click()} disabled={isRecording}
                className="flex h-8 w-8 text-[#9CA3AF] cursor-pointer items-center justify-center rounded-full transition-colors hover:bg-gray-600/30 hover:text-[#D1D5DB]">
                <Paperclip className="h-5 w-5" />
                <input ref={uploadRef} type="file" className="hidden"
                  accept="image/*,.pdf,.doc,.docx"
                  multiple
                  onChange={e => {
                    if (e.target.files) Array.from(e.target.files).forEach(processFile)
                    if (e.target) e.target.value = ""
                  }} />
              </button>
            </PromptInputAction>

            <div className="flex items-center">
              <button type="button" onClick={() => { setShowSearch(p => !p); setShowThink(false) }}
                className={cn("rounded-full transition-all flex items-center gap-1 px-2 py-1 border h-8",
                  showSearch ? "bg-[#1EAEDB]/15 border-[#1EAEDB] text-[#1EAEDB]" : "bg-transparent border-transparent text-[#9CA3AF] hover:text-[#D1D5DB]")}>
                <div className="w-5 h-5 flex items-center justify-center flex-shrink-0">
                  <motion.div animate={{ rotate: showSearch ? 360 : 0, scale: showSearch ? 1.1 : 1 }}
                    whileHover={{ rotate: 15, scale: 1.1 }} transition={{ type: "spring", stiffness: 260, damping: 25 }}>
                    <Globe className={cn("w-4 h-4", showSearch ? "text-[#1EAEDB]" : "text-inherit")} />
                  </motion.div>
                </div>
                <AnimatePresence>
                  {showSearch && (
                    <motion.span initial={{ width: 0, opacity: 0 }} animate={{ width: "auto", opacity: 1 }} exit={{ width: 0, opacity: 0 }} transition={{ duration: 0.2 }}
                      className="text-xs overflow-hidden whitespace-nowrap text-[#1EAEDB] flex-shrink-0">Search</motion.span>
                  )}
                </AnimatePresence>
              </button>

              <CustomDivider />

              <button type="button" onClick={() => { setShowThink(p => !p); setShowSearch(false) }}
                className={cn("rounded-full transition-all flex items-center gap-1 px-2 py-1 border h-8",
                  showThink ? "bg-[#8B5CF6]/15 border-[#8B5CF6] text-[#8B5CF6]" : "bg-transparent border-transparent text-[#9CA3AF] hover:text-[#D1D5DB]")}>
                <div className="w-5 h-5 flex items-center justify-center flex-shrink-0">
                  <motion.div animate={{ rotate: showThink ? 360 : 0, scale: showThink ? 1.1 : 1 }}
                    whileHover={{ rotate: 15, scale: 1.1 }} transition={{ type: "spring", stiffness: 260, damping: 25 }}>
                    <BrainCog className={cn("w-4 h-4", showThink ? "text-[#8B5CF6]" : "text-inherit")} />
                  </motion.div>
                </div>
                <AnimatePresence>
                  {showThink && (
                    <motion.span initial={{ width: 0, opacity: 0 }} animate={{ width: "auto", opacity: 1 }} exit={{ width: 0, opacity: 0 }} transition={{ duration: 0.2 }}
                      className="text-xs overflow-hidden whitespace-nowrap text-[#8B5CF6] flex-shrink-0">Think</motion.span>
                  )}
                </AnimatePresence>
              </button>

              <CustomDivider />

              <button type="button" onClick={() => setShowCanvas(p => !p)}
                className={cn("rounded-full transition-all flex items-center gap-1 px-2 py-1 border h-8",
                  showCanvas ? "bg-[#F97316]/15 border-[#F97316] text-[#F97316]" : "bg-transparent border-transparent text-[#9CA3AF] hover:text-[#D1D5DB]")}>
                <div className="w-5 h-5 flex items-center justify-center flex-shrink-0">
                  <motion.div animate={{ rotate: showCanvas ? 360 : 0, scale: showCanvas ? 1.1 : 1 }}
                    whileHover={{ rotate: 15, scale: 1.1 }} transition={{ type: "spring", stiffness: 260, damping: 25 }}>
                    <FolderCode className={cn("w-4 h-4", showCanvas ? "text-[#F97316]" : "text-inherit")} />
                  </motion.div>
                </div>
                <AnimatePresence>
                  {showCanvas && (
                    <motion.span initial={{ width: 0, opacity: 0 }} animate={{ width: "auto", opacity: 1 }} exit={{ width: 0, opacity: 0 }} transition={{ duration: 0.2 }}
                      className="text-xs overflow-hidden whitespace-nowrap text-[#F97316] flex-shrink-0">Canvas</motion.span>
                  )}
                </AnimatePresence>
              </button>
            </div>
          </div>

          <PromptInputAction tooltip={isLoading ? "Stop" : isRecording ? "Stop recording" : isVoiceLoading ? "Processing..." : hasContent ? "Send message" : "Voice message"}>
            <Button variant="default" size="icon"
              className={cn("h-8 w-8 rounded-full transition-all duration-200",
                isRecording ? "bg-transparent hover:bg-gray-600/30 text-red-500" :
                isVoiceLoading ? "bg-transparent text-purple-400 cursor-not-allowed" :
                hasContent ? "bg-white hover:bg-white/80 text-[#1F2023]" :
                "bg-transparent hover:bg-gray-600/30 text-[#9CA3AF] hover:text-[#D1D5DB]")}
              onClick={() => {
                if (isRecording) stopRecording()
                else if (isVoiceLoading) return
                else if (hasContent) handleSubmit()
                else startRecording()
              }}
              disabled={(isLoading && !isRecording) || isVoiceLoading}>
              {isLoading ? <Square className="h-4 w-4 fill-[#1F2023] animate-pulse" />
                : isRecording ? <StopCircle className="h-5 w-5 text-red-500" />
                : isVoiceLoading ? <Square className="h-4 w-4 text-purple-400 animate-pulse" />
                : hasContent ? <ArrowUp className="h-4 w-4 text-[#1F2023]" />
                : <Mic className="h-5 w-5 text-[#9CA3AF]" />}
            </Button>
          </PromptInputAction>
        </PromptInputActions>
      </PromptInput>

      <ImageViewDialog imageUrl={selectedImage} onClose={() => setSelectedImage(null)} />
    </>
  )
})
PromptInputBox.displayName = "PromptInputBox"
