// Full literal class names so Tailwind's scanner finds them even though
// they're selected dynamically at runtime (lane number is only known then).
const SECONDARY_BRANCH_COLORS = [
  { text: 'text-branch-blue', border: 'border-branch-blue' },
  { text: 'text-branch-purple', border: 'border-branch-purple' },
  { text: 'text-branch-teal', border: 'border-branch-teal' },
]

export function branchColorClasses(lane: number, isCurrent: boolean): { text: string; border: string } {
  if (isCurrent) return { text: 'text-accent', border: 'border-accent' }
  return SECONDARY_BRANCH_COLORS[lane % SECONDARY_BRANCH_COLORS.length]
}
