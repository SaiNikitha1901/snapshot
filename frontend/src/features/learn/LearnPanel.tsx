import type { LearnCardEntry } from '../../state/LearnContext'
import { useLearnState } from '../../state/LearnContext'
import { CoreIdeaCard } from './cards/CoreIdeaCard'
import { ExploreNextCard } from './cards/ExploreNextCard'
import { ProductionGitCard } from './cards/ProductionGitCard'
import { WhyCard } from './cards/WhyCard'

function LearnCardBlock({ entry }: { entry: LearnCardEntry }) {
  const { card, source } = entry
  return (
    <div className="animate-[fadein_0.25s_ease-out] border-t border-border pt-4 first:border-t-0 first:pt-0">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-sm font-medium text-fg">{card.title}</h3>
        {source === 'loading' && <span className="h-1.5 w-1.5 shrink-0 animate-pulse rounded-full bg-accent" />}
        {source === 'gemini' && <span className="shrink-0 text-[9px] text-fg-subtle">enriched by Gemini</span>}
      </div>

      <div className="flex flex-col gap-3 text-xs">
        <CoreIdeaCard text={card.core_idea} />
        <WhyCard text={card.why} />
        {card.in_production_git && <ProductionGitCard text={card.in_production_git} />}
        {card.explore_next.length > 0 && <ExploreNextCard items={card.explore_next} />}
      </div>
    </div>
  )
}

/** Not a chatbot: no text input, ever. The backend decides which
 * context-aware cards exist for the command that just ran; this only
 * renders the structured sections it's given. */
export function LearnPanel() {
  const { entries } = useLearnState()

  if (entries.length === 0) {
    return (
      <div className="p-4 text-xs text-fg-subtle">
        Run a command in the terminal to see what Git just did, explained here.
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 p-4">
      {entries.map((entry) => (
        <LearnCardBlock key={entry.card.trigger} entry={entry} />
      ))}
    </div>
  )
}
