import { motion } from "framer-motion"
import { cn } from "@/lib/utils"

function ElegantShape({
  className, delay = 0, width = 400, height = 100, rotate = 0,
  gradient = "from-white/[0.08]",
}: {
  className?: string; delay?: number; width?: number
  height?: number; rotate?: number; gradient?: string
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -80, rotate: rotate - 10 }}
      animate={{ opacity: 1, y: 0, rotate }}
      transition={{ duration: 2, delay, ease: [0.23, 0.86, 0.39, 0.96], opacity: { duration: 1 } }}
      className={cn("absolute", className)}
    >
      <motion.div
        animate={{ y: [0, 12, 0] }}
        transition={{ duration: 14, repeat: Infinity, ease: "easeInOut" }}
        style={{ width, height }}
        className="relative"
      >
        <div className={cn(
          "absolute inset-0 rounded-full bg-gradient-to-r to-transparent",
          gradient,
          "border border-white/[0.10]",
          "shadow-[0_4px_24px_0_rgba(255,255,255,0.06)]",
          "after:absolute after:inset-0 after:rounded-full",
          "after:bg-[radial-gradient(circle_at_50%_50%,rgba(255,255,255,0.15),transparent_70%)]"
        )} />
      </motion.div>
    </motion.div>
  )
}

export function ShapeBackground({ children }: { children?: React.ReactNode }) {
  return (
    <div
      className="relative min-h-[100svh] w-full overflow-hidden"
      style={{ backgroundColor: '#030303' }}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/[0.04] via-transparent to-rose-500/[0.04] blur-3xl pointer-events-none" />

      {/* Shapes — hidden on mobile to save GPU, shown md+ */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none hidden md:block">
        <ElegantShape delay={0.3} width={500} height={120} rotate={12}
          gradient="from-indigo-500/[0.12]"
          className="left-[-5%] top-[20%]" />
        <ElegantShape delay={0.5} width={400} height={100} rotate={-15}
          gradient="from-rose-500/[0.12]"
          className="right-[0%] top-[72%]" />
        <ElegantShape delay={0.4} width={260} height={70} rotate={-8}
          gradient="from-violet-500/[0.12]"
          className="left-[8%] bottom-[8%]" />
        <ElegantShape delay={0.6} width={180} height={50} rotate={20}
          gradient="from-amber-500/[0.12]"
          className="right-[18%] top-[12%]" />
      </div>

      {/* Lighter single shape for sm screens */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none block md:hidden">
        <ElegantShape delay={0.3} width={260} height={70} rotate={12}
          gradient="from-indigo-500/[0.10]"
          className="left-[-8%] top-[18%]" />
        <ElegantShape delay={0.5} width={200} height={55} rotate={-15}
          gradient="from-rose-500/[0.10]"
          className="right-[-4%] top-[65%]" />
      </div>

      <div className="absolute inset-0 bg-gradient-to-t from-[#030303] via-transparent to-[#030303]/80 pointer-events-none" />

      <div className="relative z-10 w-full h-full">
        {children}
      </div>
    </div>
  )
}
