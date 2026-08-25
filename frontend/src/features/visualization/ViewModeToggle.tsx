export type ViewMode = 'commits' | 'objects' | 'reflog'

const MODE_OPTIONS: { value: ViewMode; label: string }[] = [
  { value: 'commits', label: 'Commits' },
  { value: 'objects', label: 'Objects' },
  { value: 'reflog', label: 'Reflog' },
]

interface ViewModeToggleProps {
  mode: ViewMode
  onChange: (mode: ViewMode) => void
}

/** Same small toggle-button pattern as
 * object-animation/AnimationSpeedControl.tsx, so the Visualization
 * panel's header controls read as one consistent family. */
export function ViewModeToggle({ mode, onChange }: ViewModeToggleProps) {
  return (
    <div className="flex items-center gap-1">
      {MODE_OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={`rounded-sm px-1.5 py-0.5 font-mono text-[10px] tracking-wide uppercase transition-colors ${
            mode === option.value ? 'bg-accent-soft text-accent' : 'text-fg-subtle hover:text-fg-muted'
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
