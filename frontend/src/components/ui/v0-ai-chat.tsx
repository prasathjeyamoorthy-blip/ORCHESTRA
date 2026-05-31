import { useEffect, useRef, useCallback, useState } from "react"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { ArrowUpIcon, Paperclip, PlusIcon } from "lucide-react"

interface UseAutoResizeTextareaProps {
  minHeight: number
  maxHeight?: number
}

function useAutoResizeTextarea({ minHeight, maxHeight }: UseAutoResizeTextareaProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const adjustHeight = useCallback(
    (reset?: boolean) => {
      const textarea = textareaRef.current
      if (!textarea) return
      if (reset) { textarea.style.height = `${minHeight}px`; return }
      textarea.style.height = `${minHeight}px`
      const newHeight = Math.max(minHeight, Math.min(textarea.scrollHeight, maxHeight ?? Number.POSITIVE_INFINITY))
      textarea.style.height = `${newHeight}px`
    },
    [minHeight, maxHeight]
  )

  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) textarea.style.height = `${minHeight}px`
  }, [minHeight])

  useEffect(() => {
    const handleResize = () => adjustHeight()
    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [adjustHeight])

  return { textareaRef, adjustHeight }
}

interface V0AIChatProps {
  onSend: (message: string) => void
  isLoading?: boolean
}

export function V0AIChat({ onSend, isLoading = false }: V0AIChatProps) {
  const [value, setValue] = useState("")
  const { textareaRef, adjustHeight } = useAutoResizeTextarea({ minHeight: 60, maxHeight: 200 })

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit() }
  }

  const handleSubmit = () => {
    if (value.trim() && !isLoading) {
      onSend(value.trim())
      setValue("")
      adjustHeight(true)
    }
  }

  return (
    <div className="relative bg-neutral-900 rounded-xl border border-neutral-800 shadow-lg">
      <div className="overflow-y-auto">
        <Textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => { setValue(e.target.value); adjustHeight() }}
          onKeyDown={handleKeyDown}
          placeholder="Ask about PAN cards, Aadhaar linking, TAN..."
          className={cn(
            "w-full px-4 py-3 resize-none bg-transparent border-none text-white text-sm",
            "focus:outline-none focus-visible:ring-0 focus-visible:ring-offset-0",
            "placeholder:text-neutral-500 placeholder:text-sm min-h-[60px]"
          )}
          style={{ overflow: "hidden" }}
        />
      </div>

      <div className="flex items-center justify-between p-3">
        <button type="button" className="group p-2 hover:bg-neutral-800 rounded-lg transition-colors flex items-center gap-1">
          <Paperclip className="w-4 h-4 text-white" />
          <span className="text-xs text-zinc-400 hidden group-hover:inline transition-opacity">Attach</span>
        </button>

        <div className="flex items-center gap-2">
          <button type="button" className="px-2 py-1 rounded-lg text-sm text-zinc-400 transition-colors border border-dashed border-zinc-700 hover:border-zinc-600 hover:bg-zinc-800 flex items-center gap-1">
            <PlusIcon className="w-4 h-4" />
            Project
          </button>
          <button type="button" onClick={handleSubmit} disabled={isLoading || !value.trim()}
            className={cn(
              "px-1.5 py-1.5 rounded-lg text-sm transition-colors border border-zinc-700 hover:border-zinc-600 hover:bg-zinc-800 flex items-center gap-1 disabled:opacity-40 disabled:cursor-not-allowed",
              value.trim() ? "bg-white text-black" : "text-zinc-400"
            )}>
            <ArrowUpIcon className={cn("w-4 h-4", value.trim() ? "text-black" : "text-zinc-400")} />
            <span className="sr-only">Send</span>
          </button>
        </div>
      </div>
    </div>
  )
}
