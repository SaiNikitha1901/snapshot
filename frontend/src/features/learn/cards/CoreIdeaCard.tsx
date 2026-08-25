export function CoreIdeaCard({ text }: { text: string }) {
  return (
    <div>
      <div className="mb-1 text-[10px] font-medium tracking-wide text-fg-subtle uppercase">Core Idea</div>
      <p className="text-fg">{text}</p>
    </div>
  )
}
