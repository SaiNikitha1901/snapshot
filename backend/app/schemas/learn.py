"""Learn panel DTOs. The frontend renders structured sections only --
it never treats LLM output as raw markdown. `in_production_git` is
omitted (None) whenever Snapshot's behavior doesn't actually differ
from production Git in a way that matters.

Two-phase generation: `command_dispatcher` fills `StudioResponse.learn`
with deterministic, template-generated cards synchronously -- no
network call, so command latency never depends on an LLM. Each card
carries a `generation_context` the frontend can send back to
POST /api/learn/generate to ask for a richer, Gemini-generated version
of that same card. That endpoint always returns *a* card -- either
Gemini's, or (on any failure/missing key) the same deterministic
template card again -- so the panel never has nothing to show.
"""

from typing import Literal

from pydantic import BaseModel


class LearnGenerationContext(BaseModel):
    """Everything needed to (re)build one card, without any server-side session state."""

    trigger: str
    command_name: str
    subject_oid: str | None = None
    branch_name: str | None = None
    target_branch: str | None = None
    extra: dict[str, str] = {}


class LearnCard(BaseModel):
    trigger: str
    title: str
    core_idea: str
    why: str
    in_production_git: str | None = None
    explore_next: list[str] = []
    generation_context: LearnGenerationContext | None = None


class LearnCardSet(BaseModel):
    cards: list[LearnCard]


class LearnGenerateRequest(BaseModel):
    context: LearnGenerationContext


class LearnGenerateResponse(BaseModel):
    card: LearnCard
    source: Literal["gemini", "template"]
