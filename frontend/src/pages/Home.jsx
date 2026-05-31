import { InteractiveRobotSpline } from '../components/ui/interactive-3d-robot'
import { CinematicHero } from '../components/ui/cinematic-landing-hero'
import { ShapeBackground } from '../components/ui/shape-landing-hero'

const ROBOT_SCENE_URL = "https://prod.spline.design/PyzDhpQ9E5f1E3MT/scene.splinecode"

export default function Home({ onRobotClick }) {
  return (
    <ShapeBackground>
      <CinematicHero
        tagline1="Too many steps,"
        tagline2="made simple."
        robotSlot={
          <div
            className="absolute inset-0 w-full h-full cursor-pointer group"
            onClick={onRobotClick}
            title="Click to get started"
          >
            {/* Cover Spline watermark */}
            <div className="absolute bottom-0 right-0 w-44 sm:w-52 h-14 sm:h-16 z-10 bg-[#030303]" />
            <InteractiveRobotSpline
              scene={ROBOT_SCENE_URL}
              className="absolute inset-0 w-full h-full z-0 pointer-events-none"
            />
            {/* Subtle click hint */}
            <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none">
              <span className="text-white/40 text-xs tracking-widest uppercase font-medium">
                click to begin
              </span>
            </div>
          </div>
        }
      />
    </ShapeBackground>
  )
}
