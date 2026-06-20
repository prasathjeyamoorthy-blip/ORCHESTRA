import { motion } from "framer-motion"
import { cn } from "@/lib/utils"

function ElegantShape({ className, delay = 0, width = 400, height = 100, rotate = 0, gradient = "from-white/[0.08]" }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 1.6, delay, ease: [0.23, 0.86, 0.39, 0.96] }}
      className={cn("absolute will-change-transform", className)}
      style={{ rotate }}
    >
      <motion.div
        animate={{ y: [0, 10, 0] }}
        transition={{ duration: 16, repeat: Infinity, ease: "easeInOut" }}
        style={{ width, height }}
        className="relative will-change-transform"
      >
        <div className={cn("absolute inset-0 rounded-full bg-gradient-to-r to-transparent border border-white/[0.08]", gradient)} />
      </motion.div>
    </motion.div>
  )
}

export function ShapeBackground({ children }) {
  return (
    <div className="relative min-h-[100svh] w-full overflow-hidden" style={{ backgroundColor: '#030303' }}>
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/[0.03] via-transparent to-rose-500/[0.03] pointer-events-none" />

      <div className="absolute inset-0 overflow-hidden pointer-events-none hidden md:block">
        <ElegantShape delay={0.3} width={500} height={120} rotate={12} gradient="from-indigo-500/[0.12]" className="left-[-5%] top-[20%]" />
        <ElegantShape delay={0.5} width={400} height={100} rotate={-15} gradient="from-rose-500/[0.12]" className="right-[0%] top-[72%]" />
        <ElegantShape delay={0.4} width={260} height={70} rotate={-8} gradient="from-violet-500/[0.12]" className="left-[8%] bottom-[8%]" />
        <ElegantShape delay={0.6} width={180} height={50} rotate={20} gradient="from-amber-500/[0.12]" className="right-[18%] top-[12%]" />
      </div>

      <div className="absolute inset-0 overflow-hidden pointer-events-none block md:hidden">
        <ElegantShape delay={0.3} width={260} height={70} rotate={12} gradient="from-indigo-500/[0.10]" className="left-[-8%] top-[18%]" />
        <ElegantShape delay={0.5} width={200} height={55} rotate={-15} gradient="from-rose-500/[0.10]" className="right-[-4%] top-[65%]" />
      </div>

      <div className="absolute inset-0 bg-gradient-to-t from-[#030303] via-transparent to-[#030303]/80 pointer-events-none" />

      <div className="relative z-10 w-full h-full">
        {children}
      </div>
    </div>
  )
}
