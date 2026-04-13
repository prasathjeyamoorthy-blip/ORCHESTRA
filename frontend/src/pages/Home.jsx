import { InteractiveRobotSpline } from '../components/ui/interactive-3d-robot'
import { StarButton } from '../components/ui/star-button'
import { CinematicHero } from '../components/ui/cinematic-landing-hero'
import { ShapeBackground } from '../components/ui/shape-landing-hero'

const ROBOT_SCENE_URL = "https://prod.spline.design/PyzDhpQ9E5f1E3MT/scene.splinecode"

export default function Home({ onGetStarted }) {
  return (
    <ShapeBackground>
      <CinematicHero
        tagline1="Too many steps,"
        tagline2="made simple."
        robotSlot={
          <>
            {/* Cover Spline watermark */}
            <div className="absolute bottom-0 right-0 w-44 sm:w-52 h-14 sm:h-16 z-10 bg-[#030303]" />
            <InteractiveRobotSpline
              scene={ROBOT_SCENE_URL}
              className="absolute inset-0 w-full h-full z-0"
            />
          </>
        }
        getStartedSlot={
          <StarButton onClick={onGetStarted} className="px-[32px] py-[12px] text-[16px]">Get Started  ➜</StarButton>
        }
      />
    </ShapeBackground>
  )
}
