import { useAnimationApi, useAnimationState, type AnimationSpeed } from '../../state/AnimationContext'

const SPEED_OPTIONS: AnimationSpeed[] = [0.5, 1, 2]

export function AnimationSpeedControl() {
  const { speed } = useAnimationState()
  const { setSpeed } = useAnimationApi()

  return (
    <div className="flex items-center gap-1">
      {SPEED_OPTIONS.map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => setSpeed(option)}
          className={`rounded-sm px-1.5 py-0.5 font-mono text-[10px] transition-colors ${
            speed === option ? 'bg-accent-soft text-accent' : 'text-fg-subtle hover:text-fg-muted'
          }`}
        >
          {option}×
        </button>
      ))}
    </div>
  )
}
