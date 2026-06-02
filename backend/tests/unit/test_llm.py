import logging
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace


class _FakeCompletions:
    def __init__(self, captured_kwargs):
        self.captured_kwargs = captured_kwargs

    async def create(self, **kwargs):
        self.captured_kwargs.update(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content="ok"))
            ]
        )


class _FakeChat:
    def __init__(self, captured_kwargs):
        self.completions = _FakeCompletions(captured_kwargs)


class _FakeClient:
    def __init__(self, captured_kwargs):
        self.chat = _FakeChat(captured_kwargs)


async def test_try_azure_uses_max_completion_tokens(monkeypatch):
    from app.services import llm

    captured_kwargs = {}

    class FakeAzureOpenAI:
        def __init__(self, **kwargs):
            pass

        @property
        def chat(self):
            return _FakeChat(captured_kwargs)

    monkeypatch.setattr(llm.settings, "azure_openai_endpoint", "https://example.openai.azure.com")
    monkeypatch.setattr(llm.settings, "azure_openai_api_key", "key")
    monkeypatch.setattr("openai.AsyncAzureOpenAI", FakeAzureOpenAI)

    result = await llm._try_azure("prompt", "system", "gpt-5-nano")

    assert result == "ok"
    assert captured_kwargs["max_completion_tokens"] == 1024
    assert "max_tokens" not in captured_kwargs


async def test_try_azure_omits_temperature_for_default_only_models(monkeypatch):
    from app.services import llm

    captured_kwargs = {}

    class FakeAzureOpenAI:
        def __init__(self, **kwargs):
            pass

        @property
        def chat(self):
            return _FakeChat(captured_kwargs)

    monkeypatch.setattr(llm.settings, "azure_openai_endpoint", "https://example.openai.azure.com")
    monkeypatch.setattr(llm.settings, "azure_openai_api_key", "key")
    monkeypatch.setattr("openai.AsyncAzureOpenAI", FakeAzureOpenAI)

    result = await llm._try_azure("prompt", "system", "gpt-5-nano")

    assert result == "ok"
    assert "temperature" not in captured_kwargs


async def test_try_openrouter_uses_max_completion_tokens(monkeypatch):
    from app.services import llm

    captured_kwargs = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            pass

        @property
        def chat(self):
            return _FakeChat(captured_kwargs)

    monkeypatch.setattr(llm.settings, "openrouter_api_key", "key")
    monkeypatch.setattr(llm.settings, "openrouter_model", "deepseek/deepseek-chat-v4")
    monkeypatch.setattr("openai.AsyncOpenAI", FakeOpenAI)

    result = await llm._try_openrouter("prompt", "system")

    assert result == "ok"
    assert captured_kwargs["max_completion_tokens"] == 1024
    assert "max_tokens" not in captured_kwargs


async def test_complete_returns_none_when_all_providers_fail():
    from app.services.llm import complete
    with patch("app.services.llm._try_azure", new=AsyncMock(return_value=None)):
        with patch("app.services.llm._try_openrouter", new=AsyncMock(return_value=None)):
            result = await complete("prompt", "system")
    assert result is None


async def test_rank_first_nine_logs_warning_when_llm_fallback_used(caplog):
    from app.services.llm import rank_first_nine

    caplog.set_level(logging.WARNING)
    with patch("app.services.llm.complete", new=AsyncMock(return_value=None)):
        result = await rank_first_nine(["ST001", "ST002"], "A", "note")

    assert result is None
    assert "LLM ranking unavailable" in caplog.text
    assert "using deterministic recommendation order" in caplog.text


async def test_rank_first_nine_times_out_to_none(caplog):
    from app.services.llm import rank_first_nine
    import asyncio

    async def slow(*args, **kwargs):
        await asyncio.sleep(10)
        return None

    caplog.set_level(logging.WARNING)
    with patch("app.services.llm.complete", new=slow):
        result = await rank_first_nine(
            ["ST001", "ST002"], "A", "some note", timeout_s=0.05
        )
    assert result is None
    assert "LLM ranking timed out" in caplog.text
    assert "using deterministic recommendation order" in caplog.text


async def test_rank_first_nine_rejects_ids_not_in_candidates():
    from app.services.llm import rank_first_nine

    async def bad_llm(*args, **kwargs):
        return '["ST001", "UNKNOWN"]'

    with patch("app.services.llm.complete", new=bad_llm):
        result = await rank_first_nine(["ST001", "ST002"], "A", "note")
    assert result is None


async def test_generate_key_features_fallback_is_none():
    from app.services.llm import generate_key_features
    with patch("app.services.llm.complete", new=AsyncMock(return_value=None)):
        result = await generate_key_features({"id": "ST001", "name": "x"}, "A")
    assert result is None


async def test_generate_key_features_logs_warning_when_fallback_used(caplog):
    from app.services.llm import generate_key_features

    caplog.set_level(logging.WARNING)
    with patch("app.services.llm.complete", new=AsyncMock(return_value=None)):
        result = await generate_key_features({"id": "ST001", "name": "x"}, "A")

    assert result is None
    assert "LLM key features unavailable" in caplog.text
    assert "ST001" in caplog.text


async def test_generate_talking_points_logs_warning_when_fallback_used(caplog):
    from app.services.llm import generate_talking_points

    caplog.set_level(logging.WARNING)
    with patch("app.services.llm.complete", new=AsyncMock(return_value=None)):
        result = await generate_talking_points({"session_id": "S1"})

    assert result is None
    assert "LLM talking points unavailable" in caplog.text


async def test_rank_similar_strollers_logs_warning_when_fallback_used(caplog):
    from app.services.llm import rank_similar_strollers

    caplog.set_level(logging.WARNING)
    with patch("app.services.llm.complete", new=AsyncMock(return_value=None)):
        result = await rank_similar_strollers(
            [{"id": "ST001", "name": "Fav", "description": "desc"}],
            [{"id": "ST002", "name": "Pool", "description": "desc"}],
        )

    assert result is None
    assert "LLM similarity ranking unavailable" in caplog.text


async def test_rank_similar_strollers_times_out_fast(caplog):
    from app.services.llm import rank_similar_strollers
    import asyncio

    async def slow(*args, **kwargs):
        await asyncio.sleep(10)
        return None

    caplog.set_level(logging.WARNING)
    with patch("app.services.llm.complete", new=slow):
        result = await rank_similar_strollers(
            [{"id": "ST001", "name": "Fav", "description": "desc"}],
            [{"id": "ST002", "name": "Pool", "description": "desc"}],
            timeout_s=0.05,
        )
    assert result is None
    assert "LLM similarity ranking timed out" in caplog.text


async def test_rank_similar_strollers_rejects_incomplete_list(caplog):
    from app.services.llm import rank_similar_strollers

    caplog.set_level(logging.WARNING)
    with patch("app.services.llm.complete", new=AsyncMock(return_value='["ST002"]')):
        result = await rank_similar_strollers(
            [{"id": "ST001", "name": "Fav", "description": "desc"}],
            [
                {"id": "ST002", "name": "Pool A", "description": "desc"},
                {"id": "ST003", "name": "Pool B", "description": "desc"},
            ],
        )
    assert result is None
    assert "LLM similarity ranking incomplete list" in caplog.text


async def test_generate_talking_points_limits_to_top_three():
    from app.services.llm import generate_talking_points

    async def mock_complete(*args, **kwargs):
        return '["Point 1", "Point 2", "Point 3", "Point 4"]'

    with patch("app.services.llm.complete", new=mock_complete):
        result = await generate_talking_points({})
    assert result is not None
    assert len(result) <= 3


async def test_rerank_by_note_sends_name_so_colour_is_visible():
    from app.services.llm import rerank_by_note

    captured = {}

    async def fake_try_azure(prompt, system, model):
        captured["prompt"] = prompt
        captured["system"] = system
        # Model favours the black stroller for a "zwart" note.
        return '["ST_BLACK", "ST_BEIGE"]'

    candidates = [
        {"id": "ST_BEIGE", "name": "Kinderwagen Fox 5 - desert taupe", "brand": "bugaboo", "description": "Comfortabel."},
        {"id": "ST_BLACK", "name": "Kinderwagen Fox 5 - rich black", "brand": "bugaboo", "description": "Comfortabel."},
    ]

    with patch("app.services.llm._try_azure", new=fake_try_azure):
        result = await rerank_by_note(candidates, "Ik zoek een zwarte kinderwagen")

    # Colour lives in the name — it must be in the payload, else the LLM is blind to it.
    assert "rich black" in captured["prompt"]
    assert "desert taupe" in captured["prompt"]
    # LLM verdict is honoured verbatim (no keyword post-processing).
    assert result == ["ST_BLACK", "ST_BEIGE"]


async def test_format_description_markdown_strips_code_fences():
    from app.services.llm import format_description_markdown

    async def fake_complete(prompt, system, timeout_s=20.0):
        return "```markdown\n## Specificaties\n- Gewicht: 6 kg\n```"

    with patch("app.services.llm.complete", new=fake_complete):
        out = await format_description_markdown("Buggy", "Specificaties:Gewicht: 6 kg")
    assert out == "## Specificaties\n- Gewicht: 6 kg"


async def test_format_description_markdown_none_without_provider():
    from app.services.llm import format_description_markdown

    with patch("app.services.llm.complete", new=AsyncMock(return_value=None)):
        out = await format_description_markdown("Buggy", "desc")
    assert out is None


async def test_format_description_markdown_empty_input_returns_none():
    from app.services.llm import format_description_markdown

    out = await format_description_markdown("Buggy", "   ")
    assert out is None


async def test_rerank_by_note_accepts_subset_and_drops_unknown_ids():
    from app.services.llm import rerank_by_note

    async def fake_try_azure(prompt, system, model):
        # Model returns only the matches (a subset), plus a hallucinated id + a dupe.
        return '["ST_BLACK", "BOGUS", "ST_BLACK"]'

    candidates = [
        {"id": "ST_BLACK", "name": "Fox 5 rich black", "brand": "bugaboo", "description": "x"},
        {"id": "ST_BEIGE", "name": "Fox 5 desert taupe", "brand": "bugaboo", "description": "x"},
    ]
    with patch("app.services.llm._try_azure", new=fake_try_azure):
        result = await rerank_by_note(candidates, "zwart")

    # Subset kept, unknown id dropped, de-duplicated. Caller front-loads the rest.
    assert result == ["ST_BLACK"]


async def test_rerank_by_note_returns_none_without_provider(caplog):
    from app.services.llm import rerank_by_note

    caplog.set_level(logging.WARNING)
    with patch("app.services.llm._try_azure", new=AsyncMock(return_value=None)), patch(
        "app.services.llm._try_openrouter", new=AsyncMock(return_value=None)
    ):
        result = await rerank_by_note(
            [{"id": "ST1", "name": "A", "brand": "b", "description": "d"}],
            "zwart",
        )
    assert result is None
