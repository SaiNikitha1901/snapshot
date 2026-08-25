import type { ReactNode } from 'react'

interface PanelProps {
  title: string
  headerRight?: ReactNode
  className?: string
  bodyClassName?: string
  children: ReactNode
}

/** The one shared shell every one of the five regions renders inside.
 * Deliberately NOT a bordered/rounded "card" -- the Studio is meant
 * to read as one continuous technical workspace divided by hairline
 * rules (the grid itself supplies those, see StudioLayout.css), not a
 * dashboard of independent panels. This is just a label row over a
 * flush content area. */
export function Panel({ title, headerRight, className = '', bodyClassName = '', children }: PanelProps) {
  return (
    <section className={`flex min-h-0 flex-col overflow-hidden bg-canvas ${className}`}>
      <header className="flex shrink-0 items-center justify-between gap-2 border-b border-border px-4 py-2.5">
        <h2 className="text-[11px] font-medium tracking-[0.15em] text-fg-subtle uppercase">{title}</h2>
        {headerRight}
      </header>
      <div className={`min-h-0 flex-1 overflow-y-auto ${bodyClassName}`}>{children}</div>
    </section>
  )
}
