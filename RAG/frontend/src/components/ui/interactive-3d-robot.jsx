import { Suspense, lazy, useEffect, useRef } from 'react'

const Spline = lazy(() => import('@splinetool/react-spline'))

// Suppress the React DevTools "updating from X to Y" fiber warning
// that @react-three/fiber (used internally by Spline) emits during its
// render loop. This is cosmetic — not a real error.
function useSuppressR3FWarning() {
  useEffect(() => {
    const original = console.warn
    console.warn = (...args) => {
      if (
        typeof args[0] === 'string' &&
        (args[0].includes('updating from') || args[0].includes('ReactCurrentBatchConfig'))
      ) return
      original.apply(console, args)
    }
    return () => { console.warn = original }
  }, [])
}

export function InteractiveRobotSpline({ scene, className }) {
  useSuppressR3FWarning()

  return (
    <Suspense
      fallback={
        <div className={`w-full h-full flex items-center justify-center bg-transparent ${className ?? ''}`}>
          <svg className="animate-spin h-6 w-6 text-white/40" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l2-2.647z" />
          </svg>
        </div>
      }
    >
      <Spline scene={scene} className={className} />
    </Suspense>
  )
}
