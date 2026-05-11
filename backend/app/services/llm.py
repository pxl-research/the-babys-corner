import asyncio
import json
import logging
from app.config import settings

logger = logging.getLogger(__name__)


async def _try_azure(prompt: str, system: str, model: str) -> str | None:
    if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
        return None
    try:
        from openai import AsyncAzureOpenAI
        client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version="2024-02-01",
        )
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            max_completion_tokens=1024,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.warning("Azure LLM error: %s", e)
        return None


async def _try_openrouter(prompt: str, system: str) -> str | None:
    if not settings.openrouter_api_key:
        return None
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        resp = await client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            temperature=0.3,
            max_completion_tokens=1024,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.warning("OpenRouter LLM error: %s", e)
        return None


async def complete(prompt: str, system: str, timeout_s: float = 10.0) -> str | None:
    result = await _try_azure(prompt, system, settings.azure_openai_deployment_nano)
    if result is not None:
        return result
    result = await _try_azure(prompt, system, settings.azure_openai_deployment_mini)
    if result is not None:
        return result
    result = await _try_openrouter(prompt, system)
    return result


async def rank_first_nine(
    candidates: list[str],
    profile: str,
    note: str,
    timeout_s: float = 4.0,
) -> list[str] | None:
    system = (
        "You are a stroller advisor assistant. "
        "Reorder the given stroller IDs by relevance to the customer note. "
        "Return ONLY a JSON array of the same IDs in your preferred order. "
        "Do not add, remove, or invent any IDs."
    )
    prompt = (
        f"Customer profile: {profile}\n"
        f"Customer note: {note}\n"
        f"Stroller IDs to reorder: {json.dumps(candidates)}\n"
        "Return JSON array only."
    )
    try:
        raw = await asyncio.wait_for(complete(prompt, system), timeout=timeout_s)
    except asyncio.TimeoutError:
        logger.info("rank_first_nine timed out; using deterministic order")
        return None

    if not raw:
        return None

    try:
        ordered = json.loads(raw)
        if not isinstance(ordered, list):
            return None
        candidate_set = set(candidates)
        if any(id_ not in candidate_set for id_ in ordered):
            return None
        if set(ordered) != candidate_set:
            return None
        return ordered
    except (json.JSONDecodeError, TypeError):
        return None


async def generate_key_features(stroller: dict, profile: str) -> str | None:
    system = (
        "You are a stroller advisor. Generate 2-3 key selling points for the given stroller "
        "based only on the provided product description. Use Dutch. No invented specs."
    )
    prompt = (
        f"Stroller: {stroller.get('name')}\n"
        f"Description: {stroller.get('description')}\n"
        f"Profile: {profile}\n"
        "Return 2-3 bullet points in Dutch."
    )
    return await complete(prompt, system)


async def generate_talking_points(session_context: dict) -> list[str] | None:
    system = (
        "You are a baby store advisor. Generate 3 conversation starters for a staff member "
        "meeting this customer. Use Dutch. Base only on provided context."
    )
    prompt = f"Session context: {json.dumps(session_context, ensure_ascii=False)}\nReturn JSON array of 3 strings."
    raw = await complete(prompt, system)
    if not raw:
        return None
    try:
        points = json.loads(raw)
        if isinstance(points, list):
            return points[:3]
        return None
    except (json.JSONDecodeError, TypeError):
        return None


async def rank_similar_strollers(
    favorites: list[dict],
    pool: list[dict],
) -> list[str] | None:
    if not favorites or not pool:
        return None
    system = (
        "You are a stroller advisor. Given favorited strollers, reorder the pool by similarity. "
        "Return ONLY a JSON array of IDs from the pool in reordered sequence. No new IDs."
    )
    fav_descs = [{"id": s["id"], "name": s.get("name"), "desc": s.get("description")} for s in favorites]
    pool_ids = [s["id"] for s in pool]
    prompt = (
        f"Favorited strollers: {json.dumps(fav_descs, ensure_ascii=False)}\n"
        f"Pool IDs to reorder: {json.dumps(pool_ids)}\nReturn JSON array only."
    )
    raw = await complete(prompt, system)
    if not raw:
        return None
    try:
        ordered = json.loads(raw)
        pool_set = set(pool_ids)
        if not isinstance(ordered, list) or any(id_ not in pool_set for id_ in ordered):
            return None
        return ordered
    except (json.JSONDecodeError, TypeError):
        return None
