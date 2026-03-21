import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

function ElegantShape({
  className,
  delay = 0,
  width = 400,
  height = 100,
  rotate = 0,
  gradient = "from-white/[0.08]",
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -150, rotate: rotate - 15 }}
      animate={{ opacity: 1, y: 0, rotate: rotate }}
      transition={{
        duration: 2.4,
        delay,
        ease: [0.23, 0.86, 0.39, 0.96],
        opacity: { duration: 1.2 },
      }}
      style={{ position: "absolute" }}
      className={className}
    >
      <motion.div
        animate={{ y: [0, 15, 0] }}
        transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
        style={{ width, height, position: "relative" }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "9999px",
            background: `linear-gradient(to right, var(--shape-color, rgba(99,102,241,0.15)), transparent)`,
            backdropFilter: "blur(2px)",
            border: "2px solid rgba(255,255,255,0.15)",
            boxShadow: "0 8px 32px 0 rgba(255,255,255,0.1)",
          }}
        />
      </motion.div>
    </motion.div>
  );
}

function HeroGeometric() {
  const shapes = [
    { delay: 0.3, width: 600, height: 140, rotate: 12,  color: "rgba(99,102,241,0.15)",  style: { left: "-5%",  top: "20%" } },
    { delay: 0.5, width: 500, height: 120, rotate: -15, color: "rgba(244,63,94,0.15)",   style: { right: "0%",  top: "75%" } },
    { delay: 0.4, width: 300, height: 80,  rotate: -8,  color: "rgba(139,92,246,0.15)",  style: { left: "10%", bottom: "10%" } },
    { delay: 0.6, width: 200, height: 60,  rotate: 20,  color: "rgba(245,158,11,0.15)",  style: { right: "20%", top: "15%" } },
    { delay: 0.7, width: 150, height: 40,  rotate: -25, color: "rgba(6,182,212,0.15)",   style: { left: "25%", top: "10%" } },
  ];

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 0,
        overflow: "hidden",
        background: "#030303",
        pointerEvents: "none",
      }}
    >
      {/* Ambient gradient */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(ellipse at 20% 50%, rgba(99,102,241,0.05) 0%, transparent 60%), radial-gradient(ellipse at 80% 50%, rgba(244,63,94,0.05) 0%, transparent 60%)",
          filter: "blur(40px)",
        }}
      />

      {/* Floating shapes */}
      {shapes.map((s, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: -150, rotate: s.rotate - 15 }}
          animate={{ opacity: 1, y: 0, rotate: s.rotate }}
          transition={{
            duration: 2.4,
            delay: s.delay,
            ease: [0.23, 0.86, 0.39, 0.96],
            opacity: { duration: 1.2 },
          }}
          style={{ position: "absolute", ...s.style }}
        >
          <motion.div
            animate={{ y: [0, 15, 0] }}
            transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
            style={{ width: s.width, height: s.height, position: "relative" }}
          >
            <div
              style={{
                position: "absolute",
                inset: 0,
                borderRadius: "9999px",
                background: `linear-gradient(to right, ${s.color}, transparent)`,
                backdropFilter: "blur(2px)",
                border: "2px solid rgba(255,255,255,0.15)",
                boxShadow: "0 8px 32px 0 rgba(255,255,255,0.1)",
              }}
            />
          </motion.div>
        </motion.div>
      ))}

      {/* Top/bottom fade */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "linear-gradient(to bottom, rgba(3,3,3,0.6) 0%, transparent 30%, transparent 70%, rgba(3,3,3,0.8) 100%)",
        }}
      />
    </div>
  );
}

export { HeroGeometric };
