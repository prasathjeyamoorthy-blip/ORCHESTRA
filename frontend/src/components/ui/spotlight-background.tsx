import { useEffect, useRef } from "react"

export function SpotlightBackground({ children }: { children?: React.ReactNode }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const spotlightRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = containerRef.current
    const spotlight = spotlightRef.current
    if (!container || !spotlight) return

    const move = (e: MouseEvent) => {
      const { clientX, clientY } = e
      spotlight.style.background = `radial-gradient(600px circle at ${clientX}px ${clientY}px, rgba(120,100,255,0.12), rgba(80,60,200,0.06) 40%, transparent 70%)`
    }

    window.addEventListener("mousemove", move)
    return () => window.removeEventListener("mousemove", move)
  }, [])

  return (
    <div
      ref={containerRef}
      className="relative min-h-screen w-full overflow-hidden"
      style={{ backgroundColor: "#050508" }}
    >
      {/* Spotlight layer — follows cursor */}
      <div
        ref={spotlightRef}
        className="pointer-events-none fixed inset-0 z-0 transition-none"
        style={{
          background: "radial-gradient(600px circle at 50% 30%, rgba(120,100,255,0.10), transparent 70%)",
        }}
      />

      {/* Subtle top vignette like the screenshot */}
      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          background: "radial-gradient(ellipse 80% 40% at 50% 0%, rgba(160,140,255,0.07) 0%, transparent 70%)",
        }}
      />

      {/* Bottom fade */}
      <div
        className="pointer-events-none fixed bottom-0 left-0 right-0 h-40 z-0"
        style={{ background: "linear-gradient(to top, #050508, transparent)" }}
      />

      <div className="relative z-10 w-full h-full">
        {children}
      </div>
    </div>
  )
}
