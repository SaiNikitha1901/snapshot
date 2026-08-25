import { useAnimationState } from '../../state/AnimationContext'
import type { AnimationStep } from '../../types/snapshot'

type StepState = 'done' | 'active' | 'pending'

function StepChip({ step, state }: { step: AnimationStep; state: StepState }) {
  const classes =
    state === 'active'
      ? 'border-accent bg-accent-soft text-accent scale-105'
      : state === 'done'
        ? 'border-border-strong bg-surface-raised text-fg-muted'
        : 'border-border bg-canvas text-fg-subtle opacity-40'

  return (
    <div
      className={`rounded-sm border px-2.5 py-1.5 text-[11px] whitespace-nowrap transition-all duration-300 ${classes}`}
      title={step.detail ?? undefined}
    >
      {step.label}
    </div>
  )
}

/** Temporary overlay on top of the permanent Commit Graph: plays the
 * backend's ordered internal-operations timeline like a mechanical
 * assembly line -- each step's own label lights up as Git reaches it,
 * previous steps stay visible in a settled state. The backend decides
 * *what* happened (step kinds, labels, order); this only decides how
 * to sequence and pace showing it. */
export function AnimationStage() {
  const { sequence, currentStepIndex } = useAnimationState()

  if (!sequence) return null

  return (
    <div className="pointer-events-none absolute inset-0 flex items-end justify-center">
      <div className="pointer-events-auto mb-6 flex max-w-[92%] flex-wrap items-center justify-center gap-2 rounded-sm border border-border bg-canvas/95 px-4 py-2.5 backdrop-blur-sm">
        {sequence.steps.map((step, i) => {
          const state: StepState = i < currentStepIndex ? 'done' : i === currentStepIndex ? 'active' : 'pending'
          return (
            <div key={`${step.kind}-${i}`} className="flex items-center gap-2">
              {i > 0 && <span className="h-px w-4 shrink-0 bg-border-strong" />}
              <StepChip step={step} state={state} />
            </div>
          )
        })}
      </div>
    </div>
  )
}
