import pytest
from unittest.mock import AsyncMock, patch, MagicMock


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
