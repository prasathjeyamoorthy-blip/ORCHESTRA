import { useEffect, useRef } from "react"

export function SpotlightBackground({ children }: { children?: React.ReactNode }) {
  const spotlightRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const spotlight = spotlightRef.current
    if (!spotlight) return

    // Disable mouse tracking on touch devices — no cursor, wastes paint
    if (window.matchMedia("(pointer: coarse)").matches) return

    const move = (e: MouseEvent) => {
      const r = window.innerWidth < 768 ? 300 : 600
      spotlight.style.background =
        `radial-gradient(${r}px circle at ${e.clientX}px ${e.clientY}px, rgba(120,100,255,0.12), rgba(80,60,200,0.06) 40%, transparent 70%)`
    }

    window.addEventListener("mousemove", move, { passive: true })
    return () => window.removeEventListener("mousemove", move)
  }, [])

  return (
    <div
      className="relative min-h-[100svh] w-full overflow-hidden"
      style={{ backgroundColor: "#050508" }}
    >
      {/* Spotlight — cursor follower, hidden on touch */}
      <div
        ref={spotlightRef}
        className="pointer-events-none fixed inset-0 z-0 hidden sm:block"
        style={{
          background: "radial-gradient(600px circle at 50% 30%, rgba(120,100,255,0.10), transparent 70%)",
        }}
      />

      {/* Static top glow for mobile */}
      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          background: "radial-gradient(ellipse 80% 40% at 50% 0%, rgba(160,140,255,0.07) 0%, transparent 70%)",
        }}
      />

      {/* Bottom fade */}
      <div
        className="pointer-events-none fixed bottom-0 left-0 right-0 h-24 sm:h-40 z-0"
        style={{ background: "linear-gradient(to top, #050508, transparent)" }}
      />

      <div className="relative z-10 w-full h-full">
        {children}
      </div>
    </div>
  )
}
