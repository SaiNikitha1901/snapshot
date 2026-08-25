"""Learn panel content: deterministic template cards (used synchronously
by command_dispatcher, and as the fallback for /api/learn/generate),
plus the async Gemini enrichment call.

Trigger selection lives with the caller (command_dispatcher already
knows exactly what just happened -- which command, which kind of
merge, whether this is the first commit -- so it calls the specific
`card_for_*` builder for that situation directly, the same pattern
animation_builder.py uses). `card_for_merge` returns None for
"already up to date," which isn't a teachable moment -- progressive
disclosure means not every command needs a card.
"""

import json
import logging

from app.core import config
from app.schemas.learn import LearnCard, LearnGenerateResponse, LearnGenerationContext

logger = logging.getLogger(__name__)


# --- Public: called synchronously from command_dispatcher (no network) ----


def card_for_init() -> LearnCard:
    return _build_template_card(LearnGenerationContext(trigger="repository_initialized", command_name="init"))


def card_for_first_commit(commit_oid: str, tree_oid: str) -> LearnCard:
    context = LearnGenerationContext(
        trigger="first_commit", command_name="commit", subject_oid=commit_oid, extra={"tree_oid": tree_oid}
    )
    return _build_template_card(context)


def card_for_branch_created(name: str, commit_oid: str) -> LearnCard:
    context = LearnGenerationContext(
        trigger="branch_created", command_name="branch", subject_oid=commit_oid, branch_name=name
    )
    return _build_template_card(context)


def card_for_checkout_branch(name: str) -> LearnCard:
    context = LearnGenerationContext(trigger="checkout_branch", command_name="checkout", branch_name=name)
    return _build_template_card(context)


def card_for_detached_head(commit_oid: str) -> LearnCard:
    context = LearnGenerationContext(trigger="detached_head", command_name="checkout", subject_oid=commit_oid)
    return _build_template_card(context)


def card_for_merge(
    kind: str, current_branch: str, target_branch: str, commit_oid: str | None
) -> LearnCard | None:
    trigger = {
        "fast_forward": "merge_fast_forward",
        "merge_commit": "merge_commit",
        "conflict": "merge_conflict",
    }.get(kind)
    if trigger is None:
        return None
    context = LearnGenerationContext(
        trigger=trigger, command_name="merge", subject_oid=commit_oid,
        branch_name=current_branch, target_branch=target_branch,
    )
    return _build_template_card(context)


def card_for_reflog_viewed() -> LearnCard:
    return _build_template_card(LearnGenerationContext(trigger="reflog_viewed", command_name="reflog"))


def card_for_orphaned_commit(commit_oid: str) -> LearnCard:
    context = LearnGenerationContext(trigger="orphaned_commit", command_name="checkout", subject_oid=commit_oid)
    return _build_template_card(context)


# --- Public: called from POST /api/learn/generate (async, may hit Gemini) --


async def generate_enriched_card(context: LearnGenerationContext) -> LearnGenerateResponse:
    template_card = _build_template_card(context)

    if not config.GEMINI_API_KEY:
        return LearnGenerateResponse(card=template_card, source="template")

    try:
        enriched = await _call_gemini(context, template_card)
        return LearnGenerateResponse(card=enriched, source="gemini")
    except Exception:
        logger.warning("Gemini enrichment failed for trigger=%s; falling back to template", context.trigger, exc_info=True)
        return LearnGenerateResponse(card=template_card, source="template")


async def _call_gemini(context: LearnGenerationContext, template_card: LearnCard) -> LearnCard:
    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(api_key=config.GEMINI_API_KEY)

    response = await client.aio.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=_build_prompt(context, template_card),
        config=genai_types.GenerateContentConfig(
            system_instruction=_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=_RESPONSE_SCHEMA,
            temperature=0.4,
        ),
    )

    data = json.loads(response.text)
    return LearnCard(
        trigger=context.trigger,
        title=str(data.get("title") or template_card.title),
        core_idea=str(data.get("core_idea") or template_card.core_idea),
        why=str(data.get("why") or template_card.why),
        in_production_git=data.get("in_production_git") or None,
        explore_next=list(data.get("explore_next") or template_card.explore_next),
        generation_context=context,
    )


_SYSTEM_INSTRUCTION = (
    "You are the Learn panel of Snapshot, an educational Git internals visualizer. "
    "Snapshot is NOT a chatbot and never takes free-form questions -- you are only ever "
    "elaborating on one specific, already-chosen teaching moment. Write for a learner who "
    "is watching Git build objects on screen and wants a precise, concrete explanation of "
    "what just happened internally and why, not a tutorial or a sales pitch. Keep it tight: "
    "2-4 sentences for core_idea, 1-3 for why. Only fill in_production_git when Snapshot's "
    "behavior genuinely differs from real Git in a way that matters -- omit it (null) "
    "otherwise. explore_next is 1-3 short, concrete suggestions of what to try or inspect "
    "next inside Snapshot Studio."
)

_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "core_idea": {"type": "STRING"},
        "why": {"type": "STRING"},
        "in_production_git": {"type": "STRING", "nullable": True},
        "explore_next": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["title", "core_idea", "why", "explore_next"],
}


def _build_prompt(context: LearnGenerationContext, template_card: LearnCard) -> str:
    facts = {
        "trigger": context.trigger,
        "command": context.command_name,
        "subject_oid": context.subject_oid,
        "branch_name": context.branch_name,
        "target_branch": context.target_branch,
        **context.extra,
    }
    facts_lines = "\n".join(f"- {k}: {v}" for k, v in facts.items() if v is not None)
    return (
        f"Teaching moment: {context.trigger}\n"
        f"Known facts about what just happened:\n{facts_lines}\n\n"
        f"A hand-written baseline version of this card (you may improve on it, but stay "
        f"factually consistent with it -- do not contradict these facts):\n"
        f"title: {template_card.title}\n"
        f"core_idea: {template_card.core_idea}\n"
        f"why: {template_card.why}\n"
        f"in_production_git: {template_card.in_production_git}\n"
        f"explore_next: {template_card.explore_next}\n\n"
        f"Return JSON matching the response schema."
    )


# --- Deterministic template content (no network) ---------------------------


def _build_template_card(context: LearnGenerationContext) -> LearnCard:
    builder = _TEMPLATE_BUILDERS.get(context.trigger)
    if builder is None:
        return LearnCard(
            trigger=context.trigger,
            title="Snapshot internals",
            core_idea="Something notable just happened in the repository's internal state.",
            why="This moment doesn't have a written explanation yet.",
            generation_context=context,
        )
    return builder(context)


def _short(oid: str | None) -> str:
    return oid[:7] if oid else "(unknown)"


def _template_repository_initialized(context: LearnGenerationContext) -> LearnCard:
    return LearnCard(
        trigger=context.trigger,
        title="A repository is just a folder of hashed objects",
        core_idea=(
            "`snapshot init` created .snapshot/objects/ (empty, for now), an empty "
            "refs/heads/ directory, and a HEAD file pointing at 'refs/heads/main' -- a "
            "branch that doesn't exist yet."
        ),
        why=(
            "There's no special magic at the start: no history, no commits, not even a "
            "real 'main' branch object. HEAD just names where main *will* point once it "
            "has a commit."
        ),
        in_production_git=(
            "Real Git also writes hooks/, a config file, and a description file on init -- "
            "none of which affect the object model, so Snapshot omits them."
        ),
        explore_next=[
            "Stage a file with `add` to see the first blob get hashed and stored.",
            "Open HEAD in the Object Inspector -- it already resolves to a branch name, just not a commit yet.",
        ],
        generation_context=context,
    )


def _template_first_commit(context: LearnGenerationContext) -> LearnCard:
    return LearnCard(
        trigger=context.trigger,
        title="A commit is a pointer to a tree, plus a parent",
        core_idea=(
            f"Commit {_short(context.subject_oid)} doesn't store your files directly -- it "
            f"points at root tree {_short(context.extra.get('tree_oid'))}, which points at "
            f"the blobs you staged. This is the first commit, so it has no parent."
        ),
        why=(
            "History isn't stored as a separate list anywhere -- it's reconstructed by "
            "following each commit's parent link backward from a branch tip."
        ),
        in_production_git=(
            "Real Git also records a timezone offset alongside the timestamp and reads your "
            "identity from `git config user.name`/`user.email`; Snapshot hardcodes a single "
            "static author identity and omits the timezone."
        ),
        explore_next=[
            "Open this commit in the Object Inspector and follow tree → blob to see your file's exact stored bytes.",
            "Make a second commit and compare -- this time it will have a parent.",
        ],
        generation_context=context,
    )


def _template_branch_created(context: LearnGenerationContext) -> LearnCard:
    return LearnCard(
        trigger=context.trigger,
        title=f"'{context.branch_name}' is one small file",
        core_idea=(
            f"Creating branch '{context.branch_name}' wrote exactly one file -- "
            f"refs/heads/{context.branch_name} -- containing commit {_short(context.subject_oid)}. "
            "No objects were touched, and HEAD didn't move."
        ),
        why=(
            "Branches are deliberately lightweight pointers, not copies of your project. "
            "That's what makes creating one nearly instantaneous, in Snapshot and in real Git alike."
        ),
        explore_next=[
            "Check out the new branch to see HEAD switch to point at it.",
            "Compare the branch's ref file with the commit it points to in the Object Inspector.",
        ],
        generation_context=context,
    )


def _template_checkout_branch(context: LearnGenerationContext) -> LearnCard:
    return LearnCard(
        trigger=context.trigger,
        title="Why did HEAD move?",
        core_idea=(
            f"Checking out '{context.branch_name}' rewrote the working directory and index "
            f"to match that branch's tip commit, then repointed HEAD at "
            f"refs/heads/{context.branch_name} by name -- not at a raw commit ID."
        ),
        why=(
            "Because HEAD stores a branch *name* here (symbolic), your next commit will "
            "automatically advance this branch. That's the difference from detached HEAD."
        ),
        explore_next=["Check out a commit ID directly instead of a branch name to see detached HEAD."],
        generation_context=context,
    )


def _template_detached_head(context: LearnGenerationContext) -> LearnCard:
    return LearnCard(
        trigger=context.trigger,
        title="HEAD is detached: you're on a commit, not a branch",
        core_idea=(
            f"HEAD now holds commit {_short(context.subject_oid)} directly, instead of "
            "'ref: refs/heads/<name>'. Your working directory matches that commit exactly."
        ),
        why=(
            "Any commit you make from here still works -- it just won't move any branch "
            "pointer, since HEAD isn't following one. Only HEAD itself advances."
        ),
        in_production_git=(
            "This matches real Git closely: a commit made in detached HEAD becomes "
            "unreachable from any branch the moment you check out elsewhere. Both track the "
            "move in a reflog, though -- open the Reflog view after switching away and you "
            "can still recover this exact commit by its oid."
        ),
        explore_next=[
            "Create a branch right now to give this commit a permanent name before switching away.",
            "Check out a branch again and notice HEAD becomes symbolic once more.",
        ],
        generation_context=context,
    )


def _template_merge_fast_forward(context: LearnGenerationContext) -> LearnCard:
    return LearnCard(
        trigger=context.trigger,
        title="Fast-forward: no new commit needed",
        core_idea=(
            f"'{context.branch_name}' was a direct ancestor of '{context.target_branch}', so "
            f"merging just moved the '{context.branch_name}' pointer forward to "
            f"{_short(context.subject_oid)}. No merge commit, no tree merging, no conflict "
            "resolution -- there was nothing to combine."
        ),
        why=(
            "A merge only needs to *combine* histories when they've diverged. If one branch "
            "is simply behind the other, advancing the pointer already contains everything."
        ),
        in_production_git=(
            "Real Git lets you force a merge commit even when a fast-forward is possible "
            "(`git merge --no-ff`), to keep a record that a merge happened. Snapshot always "
            "fast-forwards when it can."
        ),
        explore_next=["Diverge the two branches with separate commits, then merge again to see a real merge commit."],
        generation_context=context,
    )


def _template_merge_commit(context: LearnGenerationContext) -> LearnCard:
    return LearnCard(
        trigger=context.trigger,
        title="Why does this commit have two parents?",
        core_idea=(
            f"'{context.branch_name}' and '{context.target_branch}' had each moved forward "
            f"independently since they diverged, so merging built a new commit "
            f"{_short(context.subject_oid)} with two parents -- one from each branch -- "
            "recording that both histories are now combined."
        ),
        why=(
            "A merge commit is an ordinary commit with one extra field. Everything else "
            "about it -- its tree, its message -- works exactly like any other commit."
        ),
        in_production_git=(
            "Snapshot's line-level merge (via Python's difflib) doesn't handle every rare "
            "ordering ambiguity real Git's merge strategies do -- e.g. both sides inserting "
            "new content at the exact same position in a file that already existed. Ordinary "
            "edits to different lines, the same line, or new files are all handled correctly."
        ),
        explore_next=[
            "Open this commit in the Object Inspector and follow both parent links.",
            "Compare its tree with an ordinary single-parent commit's tree.",
        ],
        generation_context=context,
    )


def _template_merge_conflict(context: LearnGenerationContext) -> LearnCard:
    return LearnCard(
        trigger=context.trigger,
        title="A conflict is Git refusing to guess",
        core_idea=(
            f"Both '{context.branch_name}' and '{context.target_branch}' changed the same "
            "region of the same file(s) differently since they diverged. Rather than pick a "
            "side, Snapshot wrote both versions into the file, separated by <<<<<<<, =======, "
            "and >>>>>>> markers, and stopped before creating a merge commit."
        ),
        why=(
            "Combining two edits automatically is only safe when they don't overlap. When "
            "they do, only a human can decide which change -- or what combination -- is correct."
        ),
        in_production_git=(
            "Real Git records conflicts as special multi-stage entries directly in the index, "
            "so `git status` can precisely list 'both modified' files. Snapshot detects "
            "conflicts by scanning the working directory for marker text instead -- simpler, "
            "but it can't distinguish a real conflict from a file that happens to contain "
            "similar-looking text."
        ),
        explore_next=[
            "Open the conflicted file with `cat` to see the marker format.",
            "Edit the file to resolve it, then `add` and `commit` to finish the merge.",
        ],
        generation_context=context,
    )


def _template_reflog_viewed(context: LearnGenerationContext) -> LearnCard:
    return LearnCard(
        trigger=context.trigger,
        title="Reflog: a log of where HEAD has been",
        core_idea=(
            "Every time HEAD moves -- a commit, a checkout, a merge -- Snapshot appends one "
            "line to .snapshot/logs/HEAD recording the old oid, the new oid, and why. The "
            "Reflog view lists these entries newest-first, exactly as they were recorded."
        ),
        why=(
            "The commit graph only shows what's reachable *right now* from a branch tip or "
            "HEAD. The reflog is different: it's a history of HEAD's own movements, so it "
            "still remembers oids the commit graph has already forgotten."
        ),
        in_production_git=(
            "Real Git also keeps a separate reflog per branch (`refs/<branch>@{n}`); Snapshot "
            "only tracks the one that matters most for this exact situation -- HEAD's."
        ),
        explore_next=[
            "Click an entry marked unreachable to inspect that commit even though no branch points at it.",
            "Compare the reflog's order with the commit graph -- the graph has no idea this commit ever existed.",
        ],
        generation_context=context,
    )


def _template_orphaned_commit(context: LearnGenerationContext) -> LearnCard:
    return LearnCard(
        trigger=context.trigger,
        title="This commit just became unreachable",
        core_idea=(
            f"Commit {_short(context.subject_oid)} was HEAD while detached, with no branch "
            "pointing at it. Checking out elsewhere moved HEAD away, and nothing -- no "
            "branch, no other commit's parent link -- still points back to it."
        ),
        why=(
            "The commit graph is built by walking backward from branch tips and HEAD. A "
            "commit that isn't the ancestor of any of those starting points simply isn't "
            "visited, even though its object is still sitting in .snapshot/objects/ intact."
        ),
        in_production_git=(
            "This is exactly how real Git's garbage collector decides what's eligible for "
            "deletion, too -- unreachable objects aren't deleted immediately, only once `git gc` "
            "runs and nothing (including the reflog) still references them."
        ),
        explore_next=[
            "Open the Reflog view -- the entry for this commit is still there, marked unreachable.",
            "Run `checkout <oid>` with this commit's full oid to make it HEAD again, then `branch` to give it a permanent name.",
        ],
        generation_context=context,
    )


_TEMPLATE_BUILDERS = {
    "repository_initialized": _template_repository_initialized,
    "first_commit": _template_first_commit,
    "branch_created": _template_branch_created,
    "checkout_branch": _template_checkout_branch,
    "detached_head": _template_detached_head,
    "merge_fast_forward": _template_merge_fast_forward,
    "merge_commit": _template_merge_commit,
    "merge_conflict": _template_merge_conflict,
    "reflog_viewed": _template_reflog_viewed,
    "orphaned_commit": _template_orphaned_commit,
}
