export function ProductionGitCard({ text }: { text: string }) {
  return (
    <div className="border-l border-border-strong pl-3">
      <div className="mb-1 text-[10px] font-medium tracking-wide text-fg-subtle uppercase">📘 In Production Git</div>
      <p className="text-fg-muted">{text}</p>
    </div>
  )
}
