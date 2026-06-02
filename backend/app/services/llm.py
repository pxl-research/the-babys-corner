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
            max_completion_tokens=16384,
        )
        content = resp.choices[0].message.content
        if not content:
            logger.warning("Azure model %s returned empty content (finish_reason=%s)", model, resp.choices[0].finish_reason)
            return None
        return content
    except Exception as e:
        logger.warning("Azure LLM error (%s): %s", model, e)
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


async def complete(prompt: str, system: str, timeout_s: float = 20.0) -> str | None:
    result = await _try_azure(prompt, system, settings.azure_openai_deployment_mini)
    if result is not None:
        return result
    result = await _try_azure(prompt, system, settings.azure_openai_deployment_nano)
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
        logger.warning("LLM ranking timed out; using deterministic recommendation order.")
        return None

    if not raw:
        logger.warning("LLM ranking unavailable; using deterministic recommendation order.")
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
    features = await complete(prompt, system)
    if not features:
        logger.warning(
            "LLM key features unavailable for stroller %s; using fallback key features.",
            stroller.get("id", "?"),
        )
        return None
    return features


async def generate_talking_points(session_context: dict) -> list[str] | None:
    system = (
        "You are a baby store advisor. Generate 3 conversation starters for a staff member "
        "meeting this customer. Use Dutch. Base only on provided context."
    )
    prompt = f"Session context: {json.dumps(session_context, ensure_ascii=False)}\nReturn JSON array of 3 strings."
    raw = await complete(prompt, system)
    if not raw:
        logger.warning("LLM talking points unavailable; staff handoff will omit generated talking points.")
        return None
    try:
        points = json.loads(raw)
        if isinstance(points, list):
            return points[:3]
        return None
    except (json.JSONDecodeError, TypeError):
        return None


async def rerank_by_note(
    candidates: list[dict],
    note: str,
    timeout_s: float = 100.0,
) -> list[str] | None:
    """Re-rank strollers by semantic match of the note against name + description.

    The product name carries colour/variant (e.g. "rich black"); the description
    carries features. Both are sent so the model can honour notes like "zwart".
    """
    if not candidates or not note.strip():
        return None

    system = (
        "You are a stroller advisor assistant. "
        "Re-order the given strollers by how well they match the customer's note. "
        "The product name often encodes colour and variant (e.g. 'rich black', "
        "'desert taupe', 'forest green'); the Dutch description covers features and use. "
        "Use BOTH the name and the description to judge relevance. "
        "Return ONLY a JSON array of ALL provided IDs in order from best to worst match. "
        "Do not add, remove, or invent any IDs."
    )
    items = [
        {
            "id": c["id"],
            "name": c.get("name") or "",
            "brand": c.get("brand") or "",
            "desc": c.get("compact_description") or (c.get("description") or "")[:200],
        }
        for c in candidates
    ]
    prompt = (
        f"Customer note: {note}\n\n"
        f"Strollers:\n{json.dumps(items, ensure_ascii=False)}\n\n"
        "Return JSON array of IDs only."
    )

    async def _call() -> str | None:
        # nano (reasoning model) is ~13s for 50 strollers; mini is ~80s for same — use nano first
        result = await _try_azure(prompt, system, settings.azure_openai_deployment_nano)
        if result is not None:
            return result
        result = await _try_azure(prompt, system, settings.azure_openai_deployment_mini)
        if result is not None:
            return result
        return await _try_openrouter(prompt, system)

    try:
        raw = await asyncio.wait_for(_call(), timeout=timeout_s)
    except asyncio.TimeoutError:
        logger.warning("LLM note rerank timed out; keeping deterministic order.")
        return None

    if not raw:
        logger.warning("LLM note rerank unavailable; keeping deterministic order.")
        return None

    try:
        ordered = json.loads(raw)
        if not isinstance(ordered, list):
            return None
        candidate_ids = {c["id"] for c in candidates}
        if set(ordered) != candidate_ids:
            return None
        return [str(id_) for id_ in ordered]
    except (json.JSONDecodeError, TypeError):
        return None


async def rank_similar_strollers(
    favorites: list[dict],
    pool: list[dict],
    timeout_s: float = 2.5,
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
    try:
        raw = await asyncio.wait_for(complete(prompt, system), timeout=timeout_s)
    except asyncio.TimeoutError:
        logger.warning("LLM similarity ranking timed out; using normal recommendation order.")
        return None
    if not raw:
        logger.warning("LLM similarity ranking unavailable; using normal recommendation order.")
        return None
    try:
        ordered = json.loads(raw)
        pool_set = set(pool_ids)
        if not isinstance(ordered, list) or any(id_ not in pool_set for id_ in ordered):
            logger.warning("LLM similarity ranking invalid IDs; using normal recommendation order.")
            return None
        if set(ordered) != pool_set:
            logger.warning("LLM similarity ranking incomplete list; using normal recommendation order.")
            return None
        return ordered
    except (json.JSONDecodeError, TypeError):
        logger.warning("LLM similarity ranking unparseable; using normal recommendation order.")
        return None
