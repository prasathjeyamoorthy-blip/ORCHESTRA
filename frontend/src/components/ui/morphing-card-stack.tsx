"use client"
import { useState, type ReactNode } from "react"
import { motion, AnimatePresence, LayoutGroup, type PanInfo } from "framer-motion"
import { cn } from "@/lib/utils"
import { Grid3X3, Layers, LayoutList } from "lucide-react"

export type LayoutMode = "stack" | "grid" | "list"

export interface CardData {
  id: string
  title: string
  description: string
  icon?: ReactNode
  color?: string
}

export interface MorphingCardStackProps {
  cards?: CardData[]
  className?: string
  defaultLayout?: LayoutMode
  onCardClick?: (card: CardData) => void
  onCardDoubleTap?: (card: CardData) => void
}

const layoutIcons = { stack: Layers, grid: Grid3X3, list: LayoutList }
const SWIPE_THRESHOLD = 50

export function MorphingCardStack({
  cards = [],
  className,
  defaultLayout = "stack",
  onCardClick,
  onCardDoubleTap,
}: MorphingCardStackProps) {
  const [layout, setLayout] = useState<LayoutMode>(defaultLayout)
  const [expandedCard, setExpandedCard] = useState<string | null>(null)
  const [activeIndex, setActiveIndex] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const [lastTap, setLastTap] = useState<{ id: string; time: number } | null>(null)

  if (!cards || cards.length === 0) return null

  const handleDragEnd = (_: unknown, info: PanInfo) => {
    const { offset, velocity } = info
    const swipe = Math.abs(offset.x) * velocity.x
    if (offset.x < -SWIPE_THRESHOLD || swipe < -1000) {
      setActiveIndex(prev => (prev + 1) % cards.length)
    } else if (offset.x > SWIPE_THRESHOLD || swipe > 1000) {
      setActiveIndex(prev => (prev - 1 + cards.length) % cards.length)
    }
    setIsDragging(false)
  }

  const getStackOrder = () => {
    const reordered = []
    for (let i = 0; i < cards.length; i++) {
      const index = (activeIndex + i) % cards.length
      reordered.push({ ...cards[index], stackPosition: i })
    }
    return reordered.reverse()
  }

  const getLayoutStyles = (stackPosition: number) => {
    switch (layout) {
      case "stack": return { top: stackPosition * 8, left: stackPosition * 8, zIndex: cards.length - stackPosition, rotate: (stackPosition - 1) * 2 }
      default: return { top: 0, left: 0, zIndex: 1, rotate: 0 }
    }
  }

  const containerStyles = {
    stack: "relative h-64 w-64",
    grid: "grid grid-cols-2 gap-3",
    list: "flex flex-col gap-3",
  }

  const displayCards = layout === "stack"
    ? getStackOrder()
    : cards.map((c, i) => ({ ...c, stackPosition: i }))

  const handleCardInteraction = (card: CardData & { stackPosition: number }) => {
    if (isDragging) return
    const now = Date.now()
    if (lastTap && lastTap.id === card.id && now - lastTap.time < 400) {
      // Double tap
      onCardDoubleTap?.(card)
      setLastTap(null)
    } else {
      setLastTap({ id: card.id, time: now })
      setExpandedCard(expandedCard === card.id ? null : card.id)
      onCardClick?.(card)
    }
  }

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex items-center justify-center gap-1 rounded-lg bg-white/[0.04] border border-white/[0.07] p-1 w-fit mx-auto">
        {(Object.keys(layoutIcons) as LayoutMode[]).map(mode => {
          const Icon = layoutIcons[mode]
          return (
            <button key={mode} onClick={() => setLayout(mode)}
              className={cn("rounded-md p-2 transition-all",
                layout === mode ? "bg-violet-600 text-white" : "text-white/30 hover:text-white/70 hover:bg-white/[0.05]"
              )} aria-label={`Switch to ${mode} layout`}>
              <Icon className="h-4 w-4" />
            </button>
          )
        })}
      </div>

      <LayoutGroup>
        <motion.div layout className={cn(containerStyles[layout], "mx-auto")}>
          <AnimatePresence mode="popLayout">
            {displayCards.map(card => {
              const styles = getLayoutStyles(card.stackPosition)
              const isExpanded = expandedCard === card.id
              const isTopCard = layout === "stack" && card.stackPosition === 0
              return (
                <motion.div key={card.id} layoutId={card.id}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: isExpanded ? 1.05 : 1, x: 0, ...styles }}
                  exit={{ opacity: 0, scale: 0.8, x: -200 }}
                  transition={{ type: "spring", stiffness: 300, damping: 25 }}
                  drag={isTopCard ? "x" : false}
                  dragConstraints={{ left: 0, right: 0 }}
                  dragElastic={0.7}
                  onDragStart={() => setIsDragging(true)}
                  onDragEnd={handleDragEnd}
                  whileDrag={{ scale: 1.02, cursor: "grabbing" }}
                  onClick={() => handleCardInteraction(card)}
                  className={cn(
                    "cursor-pointer rounded-xl border border-white/[0.07] p-4 select-none",
                    "bg-white/[0.03] hover:bg-white/[0.06] transition-colors",
                    layout === "stack" && "absolute w-56 h-48",
                    layout === "stack" && isTopCard && "cursor-grab active:cursor-grabbing",
                    layout === "grid" && "w-full aspect-square",
                    layout === "list" && "w-full",
                    isExpanded && "ring-2 ring-violet-500/50",
                  )}
                  style={{ backgroundColor: card.color || undefined }}>
                  <div className="flex items-start gap-3">
                    {card.icon && (
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white/[0.06] text-white/70">
                        {card.icon}
                      </div>
                    )}
                    <div className="min-w-0 flex-1">
                      <h3 className="font-semibold text-white truncate text-sm">{card.title}</h3>
                      <p className={cn("text-xs text-white/40 mt-1",
                        layout === "stack" && "line-clamp-3",
                        layout === "grid" && "line-clamp-2",
                        layout === "list" && "line-clamp-1",
                      )}>{card.description}</p>
                    </div>
                  </div>
                  {isTopCard && (
                    <div className="absolute bottom-2 left-0 right-0 text-center">
                      <span className="text-[10px] text-white/20">Swipe to navigate · Double-tap to open</span>
                    </div>
                  )}
                </motion.div>
              )
            })}
          </AnimatePresence>
        </motion.div>
      </LayoutGroup>

      {layout === "stack" && cards.length > 1 && (
        <div className="flex justify-center gap-1.5">
          {cards.map((_, index) => (
            <button key={index} onClick={() => setActiveIndex(index)}
              className={cn("h-1.5 rounded-full transition-all",
                index === activeIndex ? "w-4 bg-violet-500" : "w-1.5 bg-white/20 hover:bg-white/40"
              )} aria-label={`Go to card ${index + 1}`} />
          ))}
        </div>
      )}
    </div>
  )
}
