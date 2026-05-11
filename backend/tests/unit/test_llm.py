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


async def test_rank_first_nine_times_out_to_none():
    from app.services.llm import rank_first_nine
    import asyncio

    async def slow(*args, **kwargs):
        await asyncio.sleep(10)
        return None

    with patch("app.services.llm.complete", new=slow):
        result = await rank_first_nine(
            ["ST001", "ST002"], "A", "some note", timeout_s=0.05
        )
    assert result is None


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


async def test_generate_talking_points_limits_to_top_three():
    from app.services.llm import generate_talking_points

    async def mock_complete(*args, **kwargs):
        return '["Point 1", "Point 2", "Point 3", "Point 4"]'

    with patch("app.services.llm.complete", new=mock_complete):
        result = await generate_talking_points({})
    assert result is not None
    assert len(result) <= 3
