import json
import uuid
import logging
import re
from datetime import datetime, timezone
from sqlite3 import IntegrityError
from typing import Annotated, Optional

from fastapi import APIRouter, Cookie, HTTPException, BackgroundTasks, Query, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.content import load_quiz_config, load_tag_questions
from app.database import get_db
from app.schemas import (
    SessionCreateResponse,
    SessionCurrentResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
    RecommendationBatchResponse,
    StrollerItem,
    AccessoryItem,
    FavoriteToggleRequest,
    FavoriteToggleResponse,
    ShortlistItem,
    FavoriteItemsResponse,
    HandoffResponse,
    FilterTagsRequest,
    FilterTagsResponse,
    FilterBrandsRequest,
    FilterBrandsResponse,
    BrandCollections,
    FilterCollectionsRequest,
    FilterCollectionsResponse,
    TagConfigResponse,
    TagQuizRequest,
    TagQuizResponse,
    TagCountResponse,
    TierInfo,
    NoteRequest,
)
from app.services.catalog import get_catalog, is_available
from app.services.profile import compute_profile
from app.services.recommendations import (
    BATCH_SIZE,
    PRIMARY_BATCHES,
    PRIMARY_POOL,
    compute_first_nine,
    compute_filtered_order,
    compute_tiered_tag_order,
    reorder_within_tiers,
    diversify_llm_order,
    get_batch,
    get_cross_sell_items,
    tiered_batch_ids,
)
from app.services.session_code import generate_session_code
from app.services.session_service import (
    parse_json_field,
    resolve_strollers,
    resolve_accessories,
    resolve_stroller_batches,
)
from app.services.email import send_handoff_email
from app.services.rate_limit import check_rate_limit, client_ip
from app.services.llm import (
    generate_key_features,
    generate_talking_points,
    rank_first_nine,
    rank_similar_strollers,
    rerank_by_note,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# Shared HTTP error details (referenced from many endpoints).
NO_SESSION_DETAIL = "No session cookie."
QUIZ_NOT_SUBMITTED_DETAIL = "Quiz not submitted yet."
LOCKED_DETAIL = "Session is locked after handoff."

TRANSITION_PHRASES = {
    "A": "Helder. Ik hou het compact en stel enkel de essentials voor.",
    "B": "Top. Ik leid jullie door de meest gekozen combinaties, stap voor stap.",
    "C": "Fijn! We bekijken alles tot in detail, inclusief de matching accessoires.",
}

KEY_FEATURES_FALLBACK = "Meer info binnenkort beschikbaar."


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_session_cookie_response(session_id: str, session_code: str) -> JSONResponse:
    response = JSONResponse(content={"session_id": session_id, "session_code": session_code})
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
    )
    return response


async def _get_session(session_id: str) -> dict:
    db = await get_db()
    async with db.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, detail="Session not found.")
    return dict(row)


def _require_active(session: dict):
    if session["status"] == "handed_off":
        raise HTTPException(409, detail=LOCKED_DETAIL)
    if session["status"] == "abandoned":
        raise HTTPException(409, detail="Session is abandoned.")


@router.post("", response_model=SessionCreateResponse)
async def create_session(request: Request, source: Annotated[str, Query()] = "home"):
    check_rate_limit(f"sessions:create:{client_ip(request)}", limit=60, window_seconds=300)
    session_id = str(uuid.uuid4())
    now = _now()
    db = await get_db()
    # Retry on the rare session_code collision (UNIQUE index enforces uniqueness).
    for _ in range(5):
        session_code = generate_session_code()
        try:
            await db.execute(
                """INSERT INTO sessions (session_id, session_code, source, status, started_at,
                    stroller_favorites, accessory_favorites, shown_products)
                   VALUES (?, ?, ?, 'active', ?, '[]', '[]', '[]')""",
                (session_id, session_code, source, now),
            )
            await db.commit()
            return _make_session_cookie_response(session_id, session_code)
        except IntegrityError:
            await db.rollback()
    raise HTTPException(500, detail="Could not allocate a unique session code.")


@router.get("/quiz-config")
async def quiz_config():
    config = load_quiz_config()
    # Strip internal profile labels from customer response
    questions = []
    for q in config["questions"]:
        questions.append({
            "id": q["id"],
            "text": q["text"],
            "options": [{"index": o["index"], "text": o["text"]} for o in q["options"]],
        })
    return {"questions": questions, "optional_note": config["optional_note"]}


@router.get("/tag-config", response_model=TagConfigResponse)
async def tag_config():
    config = load_tag_questions()
    # Strip internal tag mappings — tags must never reach the customer.
    questions = [
        {
            "id": q["id"],
            "text": q["text"],
            "subtitle": q.get("subtitle"),
            "multi": q["multi"],
            "options": [{"index": o["index"], "text": o["text"]} for o in q["options"]],
        }
        for q in config["questions"]
    ]
    return TagConfigResponse.model_validate({"questions": questions})


@router.get("/current", response_model=SessionCurrentResponse)
async def get_current(session_id: Annotated[Optional[str], Cookie()] = None):
    if not session_id:
        raise HTTPException(401, detail=NO_SESSION_DETAIL)
    session = await _get_session(session_id)

    profile = session.get("derived_profile")
    shown = parse_json_field(session.get("shown_products"), [])
    stroller_favs = parse_json_field(session.get("stroller_favorites"), [])
    accessory_favs = parse_json_field(session.get("accessory_favorites"), [])
    catalog = get_catalog()
    return SessionCurrentResponse(
        session_id=session["session_id"],
        session_code=session["session_code"],
        source=session["source"],
        status=session["status"],
        started_at=session["started_at"],
        quiz_submitted_at=session.get("quiz_submitted_at"),
        handoff_at=session.get("handoff_at"),
        quiz_answers=parse_json_field(session.get("quiz_answers"), []),
        optional_note=session.get("optional_note"),
        profile=profile,
        transition_phrase=TRANSITION_PHRASES.get(profile) if profile else None,
        shown_products=shown,
        stroller_favorites=stroller_favs,
        accessory_favorites=accessory_favs,
        shown_products_named=resolve_stroller_batches(shown, catalog),
        stroller_favorites_named=resolve_strollers(stroller_favs, catalog),
        accessory_favorites_named=resolve_accessories(accessory_favs, catalog),
        email_status=session.get("email_status", "not_sent"),
        favorites_adaptation_active=bool(session.get("favorites_adaptation_active", 0)),
        talking_points=parse_json_field(session.get("llm_talking_points"), None),
    )


@router.post("/current/quiz", response_model=QuizSubmitResponse)
async def submit_quiz(
    body: QuizSubmitRequest,
    session_id: Annotated[Optional[str], Cookie()] = None,
):
    if not session_id:
        raise HTTPException(401, detail=NO_SESSION_DETAIL)
    session = await _get_session(session_id)
    _require_active(session)

    if session.get("quiz_submitted_at"):
        raise HTTPException(409, detail="Quiz already submitted.")

    config = load_quiz_config()
    question_map = {q["id"]: q for q in config["questions"]}

    if len(body.answers) != 3:
        raise HTTPException(422, detail="Exactly 3 answers required.")

    enriched_answers = []
    for ans in body.answers:
        q = question_map.get(ans.question_id)
        if not q:
            raise HTTPException(422, detail=f"Unknown question_id: {ans.question_id}")
        opts = {o["index"]: o for o in q["options"]}
        opt = opts.get(ans.option_index)
        if not opt:
            raise HTTPException(422, detail=f"Invalid option_index: {ans.option_index}")
        enriched_answers.append({
            "q": ans.question_id,
            "question_text": q["text"],
            "opt": ans.option_index,
            "option_text": opt["text"],
            "profile": opt["profile"],
        })

    profile = compute_profile(enriched_answers)
    catalog = get_catalog()
    first_nine = compute_first_nine(profile, catalog)
    reco_order = [s["id"] for s in first_nine]

    if body.optional_note and body.optional_note.strip():
        llm_result = await rank_first_nine(reco_order, profile, body.optional_note.strip())
        if llm_result:
            reco_order = diversify_llm_order(llm_result, profile, catalog, keep_top_n=1)

    now = _now()
    note = body.optional_note[:1000] if body.optional_note else None
    db = await get_db()
    await db.execute(
        """UPDATE sessions SET quiz_submitted_at=?, derived_profile=?, quiz_answers=?,
           optional_note=?, reco_order=? WHERE session_id=?""",
        (now, profile, json.dumps(enriched_answers), note, json.dumps(reco_order), session_id),
    )
    await db.commit()

    return QuizSubmitResponse(
        profile=profile,
        transition_phrase=TRANSITION_PHRASES[profile],
    )


def _handed_off_batch_response(
    session: dict, batch: int, shown_raw: list[list[str]], shown_batches_count: int,
    profile: str, tier_infos: list[TierInfo], catalog,
) -> RecommendationBatchResponse:
    """After handoff the session is locked: serve only already-shown batches, from cache."""
    if batch > shown_batches_count:
        raise HTTPException(409, detail=LOCKED_DETAIL)
    batch_ids = shown_raw[batch - 1] if batch <= len(shown_raw) else []
    products = _build_products(batch_ids, profile, catalog)
    return RecommendationBatchResponse(
        batch=batch,
        favorites_adaptation_active=bool(session.get("favorites_adaptation_active", 0)),
        products=products,
        tiers=tier_infos,
    )


async def _adapt_order_to_favorites(
    reco_order: list[str], stroller_favs: list[str], shown_raw: list[list[str]], catalog,
) -> list[str]:
    """Rerank the not-yet-shown tail by similarity to the user's favorites (LLM).

    Returns the reranked id list, or [] when the LLM yields nothing.
    """
    shown_flat = {id_ for b in shown_raw for id_ in b}
    if len(reco_order) > PRIMARY_POOL:
        # Full filtered order stored — remaining is reco_order[PRIMARY_POOL:]
        remaining_ids = [id_ for id_ in reco_order[PRIMARY_POOL:] if id_ not in shown_flat]
    else:
        reco_set = set(reco_order)
        remaining_ids = [
            s["id"] for s in catalog.get_all_strollers()
            if s["id"] not in shown_flat and s["id"] not in reco_set
        ]
    remaining_pool = [s for id_ in remaining_ids if (s := catalog.get_stroller(id_))]
    fav_strollers = [s for id_ in stroller_favs if (s := catalog.get_stroller(id_))]
    return await rank_similar_strollers(fav_strollers, remaining_pool) or []


def _select_batch_ids(
    batch: int, reco_order: list[str], reco_tiers: list[dict],
    extra_reco_order: list[str], shown_raw: list[list[str]], catalog,
) -> list[str]:
    """Stroller ids for this batch: row-filled tier slices, or the paged get_batch."""
    if reco_tiers:
        # Tiered sessions are plain contiguous slices of the full assortment; row-fill the
        # last tier so its grid section doesn't end on an orphan card.
        already_shown = sum(len(b) for b in shown_raw[:batch - 1])
        return tiered_batch_ids(reco_order, reco_tiers, already_shown, BATCH_SIZE)
    products = get_batch(batch, reco_order, catalog, extra_reco_order=extra_reco_order or None)
    return [p["id"] for p in products]


async def _persist_batch_state(
    session: dict, session_id: str, batch: int, batch_ids: list[str],
    shown_raw: list[list[str]], shown_batches_count: int,
    extra_reco_order: list[str], favorites_adaptation_active: bool,
) -> None:
    """Record a freshly shown batch plus any first-reco / favorites-adaptation state."""
    updates: dict = {}
    if batch > shown_batches_count:
        shown_raw.append(batch_ids)
        updates["shown_products"] = json.dumps(shown_raw)
    if batch == 1 and not session.get("first_reco_at"):
        updates["first_reco_at"] = _now()
    if extra_reco_order and not session.get("extra_reco_order"):
        updates["extra_reco_order"] = json.dumps(extra_reco_order)
        updates["favorites_adaptation_active"] = 1 if favorites_adaptation_active else 0
    if not updates:
        return
    db = await get_db()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    await db.execute(
        f"UPDATE sessions SET {set_clause} WHERE session_id=?",
        (*updates.values(), session_id),
    )
    await db.commit()


@router.get("/current/recommendations", response_model=RecommendationBatchResponse)
async def get_recommendations(
    background_tasks: BackgroundTasks,
    batch: Annotated[int, Query(ge=1)] = 1,
    session_id: Annotated[Optional[str], Cookie()] = None,
):
    if not session_id:
        raise HTTPException(401, detail=NO_SESSION_DETAIL)
    session = await _get_session(session_id)
    if not session.get("quiz_submitted_at"):
        raise HTTPException(422, detail=QUIZ_NOT_SUBMITTED_DETAIL)

    reco_order: list[str] = parse_json_field(session.get("reco_order"), [])
    reco_tiers: list[dict] = parse_json_field(session.get("reco_tiers"), [])
    tier_infos = [TierInfo(label=t["label"], start_index=t["start"]) for t in reco_tiers]
    shown_raw: list[list[str]] = parse_json_field(session.get("shown_products"), [])
    shown_batches_count = len(shown_raw)
    extra_reco_order: list[str] = parse_json_field(session.get("extra_reco_order"), [])
    stroller_favs: list[str] = parse_json_field(session.get("stroller_favorites"), [])
    profile = session.get("derived_profile", "B")
    catalog = get_catalog()

    if session["status"] == "handed_off":
        return _handed_off_batch_response(
            session, batch, shown_raw, shown_batches_count, profile, tier_infos, catalog
        )

    # Once past the primary pool, rerank the tail by favorite similarity — but not for
    # tiered sessions, where it would scramble the exact→relaxed tier headings.
    favorites_adaptation_active = bool(session.get("favorites_adaptation_active", 0))
    if batch > PRIMARY_BATCHES and stroller_favs and not extra_reco_order and not reco_tiers:
        adapted = await _adapt_order_to_favorites(reco_order, stroller_favs, shown_raw, catalog)
        if adapted:
            extra_reco_order = adapted
            favorites_adaptation_active = True

    batch_ids = _select_batch_ids(
        batch, reco_order, reco_tiers, extra_reco_order, shown_raw, catalog
    )
    await _persist_batch_state(
        session, session_id, batch, batch_ids, shown_raw, shown_batches_count,
        extra_reco_order, favorites_adaptation_active,
    )

    llm_kf = parse_json_field(session.get("llm_key_features"), {})
    products = _build_products(batch_ids, profile, catalog, llm_kf)
    missing_key_features = [id_ for id_ in batch_ids if id_ not in llm_kf]
    if missing_key_features:
        background_tasks.add_task(
            _generate_key_features_for_products, session_id, missing_key_features, profile
        )

    return RecommendationBatchResponse(
        batch=batch,
        favorites_adaptation_active=favorites_adaptation_active,
        products=products,
        tiers=tier_infos,
    )


def _build_products(
    batch_ids: list[str],
    profile: str,
    catalog,
    llm_kf: dict | None = None,
) -> list[StrollerItem]:
    products = []
    for id_ in batch_ids:
        s = catalog.get_stroller(id_)
        if not s:
            continue
        cross_sell = get_cross_sell_items(s, profile, catalog)
        show_chips = profile in ("B", "C")
        key_features = _pick_key_features(s, (llm_kf or {}).get(id_))
        products.append(StrollerItem(
            id=s["id"],
            name=s["name"],
            brand=s["brand"],
            price=s["price"],
            description=s["description"],
            formatted_description=s.get("formatted_description"),
            image_url=s["image_url"],
            availability=s["availability"],
            is_available=is_available(s),
            key_features=key_features,
            cross_sell_items=[
                AccessoryItem(
                    id=a["id"],
                    name=a["name"],
                    brand=a["brand"],
                    price=a["price"],
                    description=a["description"],
                    image_url=a["image_url"],
                    availability=a["availability"],
                    is_available=is_available(a),
                )
                for a in cross_sell
            ],
            show_cross_sell_chips=show_chips,
        ))
    return products


_FEATURE_HEADINGS = (
    "belangrijkste kenmerken",
    "kenmerken",
    "technische specificaties",
    "specificaties",
)
_STOP_HEADINGS = (
    "wat zit er in de doos",
    "onderhoud",
    "kenmerken:",
)


def _looks_like_feature_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if s.startswith(("•", "-", "*")):
        return True
    if ":" in s and len(s) <= 140:
        return True
    if re.search(r"\b(kg|cm|mm|liter|jaar|maanden|positie|posities|upf)\b", s.lower()):
        return True
    return False


def _collect_heading_features(lines: list[str]) -> list[str]:
    """Lines under a 'kenmerken/specificaties' heading, until a stop-heading or blank gap."""
    start = -1
    for i, line in enumerate(lines):
        lowered = line.lower().strip(" :")
        if any(lowered.startswith(h) for h in _FEATURE_HEADINGS):
            start = i + 1
            break
    if start < 0:
        return []

    collected: list[str] = []
    for line in lines[start:]:
        lowered = line.lower().strip(" :")
        if any(lowered.startswith(h) for h in _STOP_HEADINGS):
            break
        if line and _looks_like_feature_line(line):
            collected.append(line)
        elif collected and not line:
            break
    return collected


def _fallback_inline_features(clean: str) -> list[str]:
    """Fallback when no heading block: capture inline 'Specificaties: ...' style text."""
    m = re.search(
        r"(belangrijkste kenmerken|technische specificaties|specificaties|kenmerken)\s*:?\s*(.+)",
        clean,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return []
    tail = m.group(2).strip()
    tail = re.split(r"\b(onderhoud|wat zit er in de doos)\b", tail, flags=re.IGNORECASE)[0]
    parts = [p.strip(" •-\n\t") for p in re.split(r"[.;]\s+|\n+", tail) if p.strip()]
    return [p for p in parts if _looks_like_feature_line(p)][:8]


def _normalize_feature_lines(collected: list[str]) -> list[str]:
    """Strip bullet glyphs, dedupe by alphanumeric key, prefix '• ', cap at 8."""
    normalized: list[str] = []
    seen: set[str] = set()
    for line in collected:
        item = line.strip()
        if item.startswith(("•", "-", "*")):
            item = item[1:].strip()
        key = re.sub(r"[^a-z0-9]+", "", item.lower())
        if not item or not key or key in seen:
            continue
        seen.add(key)
        normalized.append(f"• {item}")
        if len(normalized) == 8:
            break
    return normalized


def _extract_features_from_text(text: str | None) -> str:
    if not text:
        return ""
    clean = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in clean.split("\n")]
    if not any(lines):
        return ""
    collected = _collect_heading_features(lines) or _fallback_inline_features(clean)
    return "\n".join(_normalize_feature_lines(collected))


def _pick_key_features(stroller: dict, llm_key_features: str | None) -> str:
    if llm_key_features and llm_key_features.strip() and llm_key_features != KEY_FEATURES_FALLBACK:
        return llm_key_features.strip()
    from_formatted = _extract_features_from_text(stroller.get("formatted_description"))
    if from_formatted:
        return from_formatted
    from_description = _extract_features_from_text(stroller.get("description"))
    if from_description:
        return from_description
    return ""


async def _generate_key_features_for_products(session_id: str, product_ids: list[str], profile: str):
    session = await _get_session(session_id)
    cached = parse_json_field(session.get("llm_key_features"), {})
    catalog = get_catalog()

    changed = False
    for product_id in product_ids:
        if product_id in cached:
            continue
        stroller = catalog.get_stroller(product_id)
        if not stroller:
            continue
        features = await generate_key_features(stroller, profile)
        if features:
            cached[product_id] = features
            changed = True

    if changed:
        db = await get_db()
        await db.execute(
            "UPDATE sessions SET llm_key_features=? WHERE session_id=?",
            (json.dumps(cached), session_id),
        )
        await db.commit()


async def _generate_talking_points_for_session(session_id: str):
    session = await _get_session(session_id)
    if session.get("llm_talking_points"):
        return

    context = {
        "source": session.get("source"),
        "profile": session.get("derived_profile"),
        "quiz_answers": parse_json_field(session.get("quiz_answers"), []),
        "optional_note": session.get("optional_note"),
        "shown_products": parse_json_field(session.get("shown_products"), []),
        "stroller_favorites": parse_json_field(session.get("stroller_favorites"), []),
        "accessory_favorites": parse_json_field(session.get("accessory_favorites"), []),
    }
    points = await generate_talking_points(context)
    if not points:
        return

    db = await get_db()
    await db.execute(
        "UPDATE sessions SET llm_talking_points=? WHERE session_id=?",
        (json.dumps(points[:3]), session_id),
    )
    await db.commit()


@router.post("/current/filters/tags", response_model=FilterTagsResponse)
async def save_filter_tags(
    body: FilterTagsRequest,
    session_id: Annotated[Optional[str], Cookie()] = None,
):
    if not session_id:
        raise HTTPException(401, detail=NO_SESSION_DETAIL)
    session = await _get_session(session_id)
    _require_active(session)
    if not session.get("quiz_submitted_at"):
        raise HTTPException(422, detail=QUIZ_NOT_SUBMITTED_DETAIL)

    db = await get_db()
    await db.execute(
        "UPDATE sessions SET filter_tags=?, filter_brands=NULL, filter_collections=NULL WHERE session_id=?",
        (json.dumps(body.tags), session_id),
    )
    await db.commit()

    catalog = get_catalog()
    return FilterTagsResponse(brands=catalog.get_brands_for_tags(body.tags))


@router.post("/current/filters/brands", response_model=FilterBrandsResponse)
async def save_filter_brands(
    body: FilterBrandsRequest,
    session_id: Annotated[Optional[str], Cookie()] = None,
):
    if not session_id:
        raise HTTPException(401, detail=NO_SESSION_DETAIL)
    session = await _get_session(session_id)
    _require_active(session)
    if not session.get("quiz_submitted_at"):
        raise HTTPException(422, detail=QUIZ_NOT_SUBMITTED_DETAIL)

    db = await get_db()
    await db.execute(
        "UPDATE sessions SET filter_brands=?, filter_collections=NULL WHERE session_id=?",
        (json.dumps(body.brands), session_id),
    )
    await db.commit()

    catalog = get_catalog()
    coll_map = catalog.get_collections_for_brands(body.brands)
    brands_response = [
        BrandCollections(brand=brand, collections=colls)
        for brand, colls in sorted(coll_map.items())
    ]
    return FilterBrandsResponse(brands=brands_response)


@router.post("/current/filters/collections", response_model=FilterCollectionsResponse)
async def save_filter_collections(
    body: FilterCollectionsRequest,
    session_id: Annotated[Optional[str], Cookie()] = None,
):
    if not session_id:
        raise HTTPException(401, detail=NO_SESSION_DETAIL)
    session = await _get_session(session_id)
    _require_active(session)
    if not session.get("quiz_submitted_at"):
        raise HTTPException(422, detail=QUIZ_NOT_SUBMITTED_DETAIL)

    tags = parse_json_field(session.get("filter_tags"), [])
    brands = parse_json_field(session.get("filter_brands"), [])
    selections = [s.model_dump() for s in body.selections]

    catalog = get_catalog()
    reco_order = compute_filtered_order(
        catalog,
        session.get("derived_profile"),
        tags or None,
        brands or None,
        selections or None,
    )
    stroller_count = len(reco_order)
    accessory_count = len(catalog.get_filtered_accessories(tags or None, brands or None, selections or None))

    db = await get_db()
    await db.execute(
        "UPDATE sessions SET filter_collections=?, reco_order=?, reco_tiers=NULL, extra_reco_order=NULL WHERE session_id=?",
        (json.dumps(selections), json.dumps(reco_order), session_id),
    )
    await db.commit()

    return FilterCollectionsResponse(stroller_count=stroller_count, accessory_count=accessory_count)


def _answer_tags(ans, question_map: dict) -> list[str]:
    """Validate one answer against its question and return the tags its options carry."""
    q = question_map.get(ans.question_id)
    if not q:
        raise HTTPException(422, detail=f"Unknown question_id: {ans.question_id}")
    if not q["multi"] and len(ans.option_indices) > 1:
        raise HTTPException(422, detail=f"Question {ans.question_id} accepts one answer.")
    opt_map = {o["index"]: o for o in q["options"]}
    tags: list[str] = []
    for idx in ans.option_indices:
        opt = opt_map.get(idx)
        if opt is None:
            raise HTTPException(422, detail=f"Invalid option_index {idx} for {ans.question_id}.")
        tags.extend(opt.get("tags", []))
    return tags


def _tags_from_answers(body: TagQuizRequest) -> list[str]:
    """Map answer indices to catalog tags server-side; tags never travel to the client."""
    config = load_tag_questions()
    question_map = {q["id"]: q for q in config["questions"]}

    tags: list[str] = []
    seen: set[str] = set()
    for ans in body.answers:
        for tag in _answer_tags(ans, question_map):
            if tag not in seen:
                seen.add(tag)
                tags.append(tag)
    return tags


@router.post("/current/tag-quiz/count", response_model=TagCountResponse)
async def tag_quiz_count(
    body: TagQuizRequest,
    session_id: Annotated[Optional[str], Cookie()] = None,
):
    """Preview match counts for the currently-selected tags. Does not mutate the session.

    Test/debug aid: lets us watch how many strollers remain after each selection.
    """
    if not session_id:
        raise HTTPException(401, detail=NO_SESSION_DETAIL)
    await _get_session(session_id)

    tags = _tags_from_answers(body)
    catalog = get_catalog()
    total_count = len(catalog.get_all_strollers())
    strict_count = len(catalog.get_filtered_strollers(tags or None, tag_match="all"))
    relaxed_count = len(catalog.get_filtered_strollers(tags or None, tag_match="any"))

    logger.info(
        "tag-quiz count | tags=%s | strict(AND)=%d relaxed(OR)=%d total=%d",
        tags, strict_count, relaxed_count, total_count,
    )
    return TagCountResponse(
        strict_count=strict_count,
        relaxed_count=relaxed_count,
        total_count=total_count,
    )


@router.post("/current/tag-quiz", response_model=TagQuizResponse)
async def submit_tag_quiz(
    body: TagQuizRequest,
    session_id: Annotated[Optional[str], Cookie()] = None,
):
    if not session_id:
        raise HTTPException(401, detail=NO_SESSION_DETAIL)
    session = await _get_session(session_id)
    _require_active(session)
    if not session.get("quiz_submitted_at"):
        raise HTTPException(422, detail=QUIZ_NOT_SUBMITTED_DETAIL)

    tags = _tags_from_answers(body)
    catalog = get_catalog()
    profile = session.get("derived_profile")

    # Build tiered results: exact AND first, then progressively relaxed tiers.
    strict_count = len(catalog.get_filtered_strollers(tags or None, tag_match="all"))
    reco_order, tiers, primary_kept = compute_tiered_tag_order(catalog, profile, tags)

    # primary_kept is the first non-empty tier's tag set; the dropped count reflects how
    # many wishes had to be relaxed before any stroller matched.
    dropped_count = len(tags) - len(primary_kept)
    if dropped_count == 0:
        match_mode = "all"
    elif primary_kept:
        match_mode = "partial"
    else:
        match_mode = "none"

    # Report the primary (top) tier size as the headline match count; reco_order itself
    # spans every tier down to the full assortment for browsing.
    stroller_count = tiers[0]["count"] if tiers else 0
    accessory_count = len(catalog.get_filtered_accessories(primary_kept or None, tag_match="all"))

    logger.info(
        "tag-quiz submit | session=%s selected=%s primary_kept=%s tiers=%d | strict(AND)=%d used=%d mode=%s",
        session_id, tags, primary_kept, len(tiers), strict_count, stroller_count, match_mode,
    )

    # Store the primary (kept) tags so accessory filtering stays consistent, plus the
    # flat tier-ordered reco_order and the tier boundaries for headings.
    db = await get_db()
    await db.execute(
        """UPDATE sessions SET filter_tags=?, filter_brands=NULL, filter_collections=NULL,
           reco_order=?, reco_tiers=?, extra_reco_order=NULL WHERE session_id=?""",
        (json.dumps(primary_kept), json.dumps(reco_order), json.dumps(tiers), session_id),
    )
    await db.commit()

    return TagQuizResponse(
        stroller_count=stroller_count,
        accessory_count=accessory_count,
        match_mode=match_mode,
        strict_count=strict_count,
        dropped_count=dropped_count,
    )


@router.post("/current/note")
async def save_note(
    body: NoteRequest,
    session_id: Annotated[Optional[str], Cookie()] = None,
):
    if not session_id:
        raise HTTPException(401, detail=NO_SESSION_DETAIL)
    session = await _get_session(session_id)
    _require_active(session)
    if not session.get("quiz_submitted_at"):
        raise HTTPException(422, detail=QUIZ_NOT_SUBMITTED_DETAIL)

    note = body.note[:1000] if body.note else None
    reco_order: list[str] = parse_json_field(session.get("reco_order"), [])
    reco_tiers: list[dict] = parse_json_field(session.get("reco_tiers"), [])

    if note and reco_order:
        catalog = get_catalog()
        stroller_dicts = [s for id_ in reco_order if (s := catalog.get_stroller(id_))]
        llm_result = await rerank_by_note(stroller_dicts, note)
        if llm_result:
            llm_set = set(llm_result)
            missing = [id_ for id_ in reco_order if id_ not in llm_set]
            new_order = llm_result + missing
            # Honour the note ordering only within each tier, so the exact→relaxed
            # tier headings stay aligned with the products beneath them.
            if reco_tiers:
                new_order, reco_tiers = reorder_within_tiers(reco_order, reco_tiers, new_order)
            reco_order = new_order

    db = await get_db()
    await db.execute(
        "UPDATE sessions SET optional_note=?, reco_order=?, reco_tiers=? WHERE session_id=?",
        (
            note,
            json.dumps(reco_order) if reco_order else None,
            json.dumps(reco_tiers) if reco_tiers else None,
            session_id,
        ),
    )
    await db.commit()

    return {"note": note}


@router.post("/current/favorites", response_model=FavoriteToggleResponse)
async def toggle_favorite(
    body: FavoriteToggleRequest,
    session_id: Annotated[Optional[str], Cookie()] = None,
):
    if not session_id:
        raise HTTPException(401, detail=NO_SESSION_DETAIL)
    session = await _get_session(session_id)
    _require_active(session)

    catalog = get_catalog()
    stroller_favs: list[str] = parse_json_field(session.get("stroller_favorites"), [])
    accessory_favs: list[str] = parse_json_field(session.get("accessory_favorites"), [])

    if body.item_type == "stroller":
        item = catalog.get_stroller(body.item_id)
        if not item:
            raise HTTPException(404, detail="Stroller not found.")
        if body.item_id in stroller_favs:
            stroller_favs.remove(body.item_id)
        else:
            stroller_favs.append(body.item_id)
    elif body.item_type == "accessory":
        item = catalog.get_accessory(body.item_id)
        if not item:
            raise HTTPException(404, detail="Accessory not found.")
        if body.item_id in accessory_favs:
            accessory_favs.remove(body.item_id)
        else:
            accessory_favs.append(body.item_id)
    else:
        raise HTTPException(422, detail="item_type must be 'stroller' or 'accessory'.")

    db = await get_db()
    await db.execute(
        "UPDATE sessions SET stroller_favorites=?, accessory_favorites=? WHERE session_id=?",
        (json.dumps(stroller_favs), json.dumps(accessory_favs), session_id),
    )
    await db.commit()

    return FavoriteToggleResponse(stroller_favorites=stroller_favs, accessory_favorites=accessory_favs)


@router.get("/current/favorites/items", response_model=FavoriteItemsResponse)
async def get_favorite_items(session_id: Annotated[Optional[str], Cookie()] = None):
    """Resolve favorite IDs to product details straight from the catalog.

    The shortlist must not depend on which recommendation batches are still loaded
    client-side, so favorites are resolved server-side here.
    """
    if not session_id:
        raise HTTPException(401, detail=NO_SESSION_DETAIL)
    session = await _get_session(session_id)
    catalog = get_catalog()

    def _lite(item: dict) -> ShortlistItem:
        return ShortlistItem(
            id=item["id"],
            name=item["name"],
            brand=item["brand"],
            price=item["price"],
            image_url=item["image_url"],
            availability=item["availability"],
            is_available=is_available(item),
        )

    stroller_favs = parse_json_field(session.get("stroller_favorites"), [])
    accessory_favs = parse_json_field(session.get("accessory_favorites"), [])
    strollers = [_lite(s) for id_ in stroller_favs if (s := catalog.get_stroller(id_))]
    accessories = [_lite(a) for id_ in accessory_favs if (a := catalog.get_accessory(id_))]
    return FavoriteItemsResponse(strollers=strollers, accessories=accessories)


@router.post("/current/handoff", response_model=HandoffResponse)
async def handoff(
    request: Request,
    background_tasks: BackgroundTasks,
    session_id: Annotated[Optional[str], Cookie()] = None,
):
    check_rate_limit(f"sessions:handoff:{client_ip(request)}", limit=20, window_seconds=300)
    if not session_id:
        raise HTTPException(401, detail=NO_SESSION_DETAIL)
    session = await _get_session(session_id)

    if session["status"] == "handed_off":
        raise HTTPException(409, detail="Session already handed off.")
    # Reject abandoned (and any non-active) sessions — handoff must start from active.
    _require_active(session)
    if not session.get("quiz_submitted_at"):
        raise HTTPException(422, detail=QUIZ_NOT_SUBMITTED_DETAIL)
    if not session.get("first_reco_at"):
        raise HTTPException(422, detail="No recommendations shown yet.")

    now = _now()
    db = await get_db()
    await db.execute(
        "UPDATE sessions SET status='handed_off', handoff_at=?, email_status='pending' WHERE session_id=?",
        (now, session_id),
    )
    await db.commit()

    # Reload session for email
    updated = await _get_session(session_id)
    background_tasks.add_task(send_handoff_email, updated)
    background_tasks.add_task(_generate_talking_points_for_session, session_id)

    return HandoffResponse(
        session_code=session["session_code"],
        handoff_at=now,
        email_status="pending",
    )


@router.post("/current/abandon")
async def abandon(session_id: Annotated[Optional[str], Cookie()] = None):
    if not session_id:
        raise HTTPException(401, detail=NO_SESSION_DETAIL)
    session = await _get_session(session_id)

    if session["status"] == "handed_off":
        raise HTTPException(409, detail=LOCKED_DETAIL)

    db = await get_db()
    await db.execute(
        "UPDATE sessions SET status='abandoned' WHERE session_id=?",
        (session_id,),
    )
    await db.commit()
    return {"status": "abandoned"}
