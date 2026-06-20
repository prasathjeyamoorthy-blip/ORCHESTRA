import { useEffect, useRef } from "react"

export function SpotlightBackground({ children }) {
  const spotlightRef = useRef(null)

  useEffect(() => {
    const spotlight = spotlightRef.current
    if (!spotlight) return
    if (window.matchMedia("(pointer: coarse)").matches) return

    let raf
    const move = (e) => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        const r = window.innerWidth < 768 ? 280 : 520
        spotlight.style.background =
          `radial-gradient(${r}px circle at ${e.clientX}px ${e.clientY}px, rgba(120,100,255,0.10), rgba(80,60,200,0.05) 40%, transparent 70%)`
      })
    }

    window.addEventListener("mousemove", move, { passive: true })
    return () => {
      window.removeEventListener("mousemove", move)
      cancelAnimationFrame(raf)
    }
  }, [])

  return (
    <div className="relative min-h-[100svh] w-full overflow-hidden" style={{ backgroundColor: "#050508" }}>
      <div
        ref={spotlightRef}
        className="pointer-events-none fixed inset-0 z-0 hidden sm:block"
        style={{ willChange: "background" }}
      />
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-[40vh] z-0"
        style={{ background: "radial-gradient(ellipse 80% 100% at 50% 0%, rgba(140,120,255,0.06) 0%, transparent 70%)" }}
      />
      <div
        className="pointer-events-none absolute bottom-0 left-0 right-0 h-24 sm:h-36 z-0"
        style={{ background: "linear-gradient(to top, #050508, transparent)" }}
      />
      <div className="relative z-10 w-full h-full">
        {children}
      </div>
    </div>
  )
}
