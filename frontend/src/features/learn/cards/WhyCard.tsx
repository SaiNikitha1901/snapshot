export function WhyCard({ text }: { text: string }) {
  return (
    <div>
      <div className="mb-1 text-[10px] font-medium tracking-wide text-fg-subtle uppercase">Why</div>
      <p className="text-fg-muted">{text}</p>
    </div>
  )
}
