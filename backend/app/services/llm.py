import asyncio
import json
import logging
import re
from app.config import settings

logger = logging.getLogger(__name__)


def _extract_json_array(raw: str):
    """Parse a JSON array from a model reply, tolerating markdown fences / surrounding
    prose. Returns the list, or None if no array can be recovered. Pure parsing — does
    not interpret or score content."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else None
    except (json.JSONDecodeError, TypeError):
        pass
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, list) else None
    except (json.JSONDecodeError, TypeError):
        return None


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


async def complete(prompt: str, system: str) -> str | None:
    # Timeout ownership is left to callers (via asyncio.wait_for), since complete()
    # tries multiple providers in sequence.
    result = await _try_azure(prompt, system, settings.azure_openai_deployment_mini)
    if result is not None:
        return result
    result = await _try_azure(prompt, system, settings.azure_openai_deployment_nano)
    if result is not None:
        return result
    result = await _try_openrouter(prompt, system)
    return result


async def format_description_markdown(name: str, description: str) -> str | None:
    """Reformat a glued product description into clean Markdown without changing facts.

    The feed ships descriptions as delimiter-less walls of text; only an LLM can
    recover the structure reliably. The prompt forbids inventing or dropping content,
    so this is purely a reformat. Returns None if no provider is available.
    """
    if not description or not description.strip():
        return None
    system = (
        "You are a copy editor for a Dutch baby-store catalog. Reformat the product "
        "description into clean Markdown WITHOUT changing the wording or the facts.\n"
        "Rules:\n"
        "- Keep every sentence and every spec exactly as written. You MAY split words "
        "that are glued together and fix HTML entities (e.g. '&amp;' -> '&').\n"
        "- Put the opening marketing text as one short paragraph.\n"
        "- Turn section labels such as 'Specificaties', 'Afmetingen en gewicht', "
        "'Onderhoud', 'Kenmerken' into '## ' headings.\n"
        "- Turn each listed item or spec into a '- ' bullet; use 'label: value' inside "
        "the bullet when the source does.\n"
        "- Do NOT invent, add, summarise away, or remove any information.\n"
        "- Output Markdown only, in Dutch, with no code fences."
    )
    prompt = f"Title: {name}\n\nDescription:\n{description}\n\nReturn the reformatted Markdown."
    raw = await complete(prompt, system)
    if not raw:
        logger.warning("LLM description formatting unavailable for %r; keeping raw text.", name)
        return None
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    return text or None


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
    """Pick the strollers matching the note, best-first, via the LLM.

    Returns a subset of candidate IDs (the matches) for the caller to front-load,
    not a full permutation — full ordering of a large pool is brittle and silently
    fails validation. The product name carries colour/variant (e.g. "rich black");
    the description carries features. Both are sent so notes like "zwart" work.
    Returns None only on provider/parse failure; [] means no matches.
    """
    if not candidates or not note.strip():
        return None

    system = (
        "You are a stroller advisor assistant. "
        "From the given strollers, pick the ones that match the customer's note and "
        "return their IDs ordered best match first. "
        "The product name often encodes colour and variant (e.g. 'rich black', "
        "'desert taupe', 'forest green'); the Dutch description covers features and use. "
        "Use BOTH the name and the description to judge relevance. "
        "Return ONLY a JSON array of matching IDs, best match first. Include only "
        "strollers that genuinely match the note and omit the rest; if none match, "
        "return an empty array []. Do not invent IDs."
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
        "Return a JSON array of matching IDs (best first); [] if none match."
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

    ordered = _extract_json_array(raw)
    if ordered is None:
        logger.warning("LLM note rerank returned unparseable output; keeping deterministic order.")
        return None

    # Accept a subset (the matches), best-first. Drop anything not in the pool and
    # de-duplicate; the caller front-loads these and keeps the rest in place.
    candidate_ids = {c["id"] for c in candidates}
    seen: set[str] = set()
    matches: list[str] = []
    for id_ in ordered:
        sid = str(id_)
        if sid in candidate_ids and sid not in seen:
            seen.add(sid)
            matches.append(sid)
    logger.info("LLM note rerank | note=%r | matched %d/%d strollers", note, len(matches), len(candidates))
    return matches


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
