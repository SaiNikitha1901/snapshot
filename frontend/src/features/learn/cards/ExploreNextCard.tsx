export function ExploreNextCard({ items }: { items: string[] }) {
  return (
    <div>
      <div className="mb-1 text-[10px] font-medium tracking-wide text-fg-subtle uppercase">💡 Explore Next</div>
      <ul className="list-disc space-y-1 pl-4 text-fg-muted">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  )
}
