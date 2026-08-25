import asyncio

from app.core import config
from app.schemas.learn import LearnCard, LearnGenerationContext
from app.services import learn_service


def test_template_cards_are_deterministic():
    a = learn_service.card_for_init()
    b = learn_service.card_for_init()
    assert a == b


def test_card_for_merge_already_up_to_date_is_not_a_teachable_moment():
    assert learn_service.card_for_merge("already_up_to_date", "main", "feature", "deadbeef") is None


def test_card_for_merge_maps_each_kind_to_its_trigger():
    ff = learn_service.card_for_merge("fast_forward", "main", "feature", "a" * 40)
    mc = learn_service.card_for_merge("merge_commit", "main", "feature", "b" * 40)
    conflict = learn_service.card_for_merge("conflict", "main", "feature", None)
    assert ff.trigger == "merge_fast_forward"
    assert mc.trigger == "merge_commit"
    assert conflict.trigger == "merge_conflict"


def test_generate_falls_back_to_template_when_no_api_key(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", None)
    context = LearnGenerationContext(trigger="repository_initialized", command_name="init")

    result = asyncio.run(learn_service.generate_enriched_card(context))

    assert result.source == "template"
    assert result.card == learn_service.card_for_init()


def test_generate_uses_gemini_result_on_success(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake-key-for-test")
    context = LearnGenerationContext(trigger="repository_initialized", command_name="init")

    async def fake_call_gemini(ctx, template_card):
        return LearnCard(
            trigger=ctx.trigger,
            title="Gemini-written title",
            core_idea="Gemini-written core idea.",
            why="Gemini-written why.",
            explore_next=["Try something"],
            generation_context=ctx,
        )

    monkeypatch.setattr(learn_service, "_call_gemini", fake_call_gemini)

    result = asyncio.run(learn_service.generate_enriched_card(context))

    assert result.source == "gemini"
    assert result.card.title == "Gemini-written title"


def test_generate_falls_back_to_template_when_gemini_call_fails(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake-key-for-test")
    context = LearnGenerationContext(trigger="detached_head", command_name="checkout", subject_oid="c" * 40)

    async def failing_call_gemini(ctx, template_card):
        raise RuntimeError("simulated network/API failure")

    monkeypatch.setattr(learn_service, "_call_gemini", failing_call_gemini)

    result = asyncio.run(learn_service.generate_enriched_card(context))

    assert result.source == "template"
    assert result.card == learn_service._build_template_card(context)


def test_unknown_trigger_falls_back_to_generic_card_without_crashing():
    context = LearnGenerationContext(trigger="totally_unknown_trigger", command_name="mystery")
    card = learn_service._build_template_card(context)
    assert card.trigger == "totally_unknown_trigger"
    assert card.title
