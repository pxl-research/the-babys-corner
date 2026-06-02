import json
import uuid
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Cookie, HTTPException, BackgroundTasks, Query
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
    NoteRequest,
)
from app.services.catalog import get_catalog, is_available
from app.services.profile import compute_profile
from app.services.recommendations import (
    compute_first_nine,
    compute_filtered_order,
    compute_progressive_tag_order,
    diversify_llm_order,
    get_batch,
    get_cross_sell_items,
)
from app.services.session_code import generate_session_code
from app.services.email import send_handoff_email
from app.services.llm import generate_key_features, generate_talking_points

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

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
        raise HTTPException(409, detail="Session is locked after handoff.")
    if session["status"] == "abandoned":
        raise HTTPException(409, detail="Session is abandoned.")


@router.post("", response_model=SessionCreateResponse)
async def create_session(source: str = Query(default="home")):
    session_id = str(uuid.uuid4())
    session_code = generate_session_code()
    now = _now()
    db = await get_db()
    await db.execute(
        """INSERT INTO sessions (session_id, session_code, source, status, started_at,
            stroller_favorites, accessory_favorites, shown_products)
           VALUES (?, ?, ?, 'active', ?, '[]', '[]', '[]')""",
        (session_id, session_code, source, now),
    )
    await db.commit()
    return _make_session_cookie_response(session_id, session_code)


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
    return TagConfigResponse(questions=questions)


@router.get("/current", response_model=SessionCurrentResponse)
async def get_current(session_id: Optional[str] = Cookie(default=None)):
    if not session_id:
        raise HTTPException(401, detail="No session cookie.")
    session = await _get_session(session_id)

    profile = session.get("derived_profile")
    return SessionCurrentResponse(
        session_id=session["session_id"],
        session_code=session["session_code"],
        source=session["source"],
        status=session["status"],
        started_at=session["started_at"],
        quiz_submitted_at=session.get("quiz_submitted_at"),
        handoff_at=session.get("handoff_at"),
        quiz_answers=json.loads(session["quiz_answers"]) if session.get("quiz_answers") else [],
        optional_note=session.get("optional_note"),
        profile=profile,
        transition_phrase=TRANSITION_PHRASES.get(profile) if profile else None,
        shown_products=json.loads(session["shown_products"]) if session.get("shown_products") else [],
        stroller_favorites=json.loads(session["stroller_favorites"]) if session.get("stroller_favorites") else [],
        accessory_favorites=json.loads(session["accessory_favorites"]) if session.get("accessory_favorites") else [],
        email_status=session.get("email_status", "not_sent"),
        favorites_adaptation_active=bool(session.get("favorites_adaptation_active", 0)),
        talking_points=json.loads(session["llm_talking_points"]) if session.get("llm_talking_points") else None,
    )


@router.post("/current/quiz", response_model=QuizSubmitResponse)
async def submit_quiz(
    body: QuizSubmitRequest,
    session_id: Optional[str] = Cookie(default=None),
):
    if not session_id:
        raise HTTPException(401, detail="No session cookie.")
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
    first_nine = compute_first_nine(profile, catalog, optional_note=body.optional_note or "")
    reco_order = [s["id"] for s in first_nine]

    if body.optional_note and body.optional_note.strip():
        from app.services.llm import rank_first_nine as llm_rank
        llm_result = await llm_rank(reco_order, profile, body.optional_note.strip())
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


@router.get("/current/recommendations", response_model=RecommendationBatchResponse)
async def get_recommendations(
    background_tasks: BackgroundTasks,
    batch: int = Query(default=1, ge=1),
    session_id: Optional[str] = Cookie(default=None),
):
    if not session_id:
        raise HTTPException(401, detail="No session cookie.")
    session = await _get_session(session_id)

    if not session.get("quiz_submitted_at"):
        raise HTTPException(422, detail="Quiz not submitted yet.")

    reco_order: list[str] = json.loads(session["reco_order"]) if session.get("reco_order") else []
    shown_raw: list[list[str]] = json.loads(session["shown_products"]) if session.get("shown_products") else []
    shown_batches_count = len(shown_raw)
    extra_reco_order: list[str] = json.loads(session["extra_reco_order"]) if session.get("extra_reco_order") else []
    stroller_favs: list[str] = json.loads(session["stroller_favorites"]) if session.get("stroller_favorites") else []
    accessory_favs: list[str] = json.loads(session["accessory_favorites"]) if session.get("accessory_favorites") else []
    profile = session.get("derived_profile", "B")

    # Lock check: if handed_off, only allow already-shown batches
    if session["status"] == "handed_off":
        if batch > shown_batches_count:
            raise HTTPException(409, detail="Session is locked after handoff.")
        # Return cached batch
        batch_ids = shown_raw[batch - 1] if batch <= len(shown_raw) else []
        catalog = get_catalog()
        products = _build_products(batch_ids, profile, catalog)
        return RecommendationBatchResponse(
            batch=batch,
            favorites_adaptation_active=bool(session.get("favorites_adaptation_active", 0)),
            products=products,
        )

    catalog = get_catalog()
    acc_favs_list = accessory_favs

    # Handle favorites-based adaptation for batch 4+
    favorites_adaptation_active = bool(session.get("favorites_adaptation_active", 0))
    if batch >= 4 and stroller_favs and not extra_reco_order:
        from app.services.llm import rank_similar_strollers
        shown_flat = {id_ for b in shown_raw for id_ in b}
        if len(reco_order) > 9:
            # Full filtered order stored — remaining is reco_order[9:]
            remaining_ids = [id_ for id_ in reco_order[9:] if id_ not in shown_flat]
        else:
            reco_set = set(reco_order)
            remaining_ids = [
                s["id"] for s in catalog.get_all_strollers()
                if s["id"] not in shown_flat and s["id"] not in reco_set
            ]
        remaining_pool = [catalog.get_stroller(id_) for id_ in remaining_ids]
        remaining_pool = [s for s in remaining_pool if s]
        fav_strollers = [catalog.get_stroller(id_) for id_ in stroller_favs]
        fav_strollers = [s for s in fav_strollers if s]
        llm_order = await rank_similar_strollers(fav_strollers, remaining_pool)
        if llm_order:
            extra_reco_order = llm_order
            favorites_adaptation_active = True

    batch_products = get_batch(
        batch, reco_order, acc_favs_list, catalog,
        stroller_favorites=stroller_favs,
        extra_reco_order=extra_reco_order or None,
    )
    batch_ids = [p["id"] for p in batch_products]

    # Update shown_products and other state
    db = await get_db()
    updates = {}

    if batch > shown_batches_count:
        shown_raw.append(batch_ids)
        updates["shown_products"] = json.dumps(shown_raw)

    if batch == 1 and not session.get("first_reco_at"):
        updates["first_reco_at"] = _now()

    if extra_reco_order and not session.get("extra_reco_order"):
        updates["extra_reco_order"] = json.dumps(extra_reco_order)
        updates["favorites_adaptation_active"] = 1 if favorites_adaptation_active else 0

    if updates:
        set_clause = ", ".join(f"{k}=?" for k in updates)
        await db.execute(
            f"UPDATE sessions SET {set_clause} WHERE session_id=?",
            (*updates.values(), session_id),
        )
        await db.commit()

    llm_kf = json.loads(session["llm_key_features"]) if session.get("llm_key_features") else {}

    products = _build_products(batch_ids, profile, catalog, llm_kf)
    missing_key_features = [id_ for id_ in batch_ids if id_ not in llm_kf]
    if missing_key_features:
        background_tasks.add_task(_generate_key_features_for_products, session_id, missing_key_features, profile)

    return RecommendationBatchResponse(
        batch=batch,
        favorites_adaptation_active=favorites_adaptation_active,
        products=products,
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


def _extract_features_from_text(text: str | None) -> str:
    if not text:
        return ""
    clean = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in clean.split("\n")]
    if not any(lines):
        return ""

    start = -1
    for i, line in enumerate(lines):
        lowered = line.lower().strip(" :")
        if any(lowered.startswith(h) for h in _FEATURE_HEADINGS):
            start = i + 1
            break

    collected: list[str] = []
    if start >= 0:
        for line in lines[start:]:
            lowered = line.lower().strip(" :")
            if any(lowered.startswith(h) for h in _STOP_HEADINGS):
                break
            if line and _looks_like_feature_line(line):
                collected.append(line)
            elif collected and not line:
                break

    if not collected:
        # Fallback: capture inline "Specificaties: ..." style text
        m = re.search(
            r"(belangrijkste kenmerken|technische specificaties|specificaties|kenmerken)\s*:?\s*(.+)",
            clean,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if m:
            tail = m.group(2).strip()
            tail = re.split(r"\b(onderhoud|wat zit er in de doos)\b", tail, flags=re.IGNORECASE)[0]
            parts = [p.strip(" •-\n\t") for p in re.split(r"[.;]\s+|\n+", tail) if p.strip()]
            collected = [p for p in parts if _looks_like_feature_line(p)][:8]

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

    return "\n".join(normalized)


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
    cached = json.loads(session["llm_key_features"]) if session.get("llm_key_features") else {}
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
        "quiz_answers": json.loads(session["quiz_answers"]) if session.get("quiz_answers") else [],
        "optional_note": session.get("optional_note"),
        "shown_products": json.loads(session["shown_products"]) if session.get("shown_products") else [],
        "stroller_favorites": json.loads(session["stroller_favorites"]) if session.get("stroller_favorites") else [],
        "accessory_favorites": json.loads(session["accessory_favorites"]) if session.get("accessory_favorites") else [],
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
    session_id: Optional[str] = Cookie(default=None),
):
    if not session_id:
        raise HTTPException(401, detail="No session cookie.")
    session = await _get_session(session_id)
    _require_active(session)
    if not session.get("quiz_submitted_at"):
        raise HTTPException(422, detail="Quiz not submitted yet.")

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
    session_id: Optional[str] = Cookie(default=None),
):
    if not session_id:
        raise HTTPException(401, detail="No session cookie.")
    session = await _get_session(session_id)
    _require_active(session)
    if not session.get("quiz_submitted_at"):
        raise HTTPException(422, detail="Quiz not submitted yet.")

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
    session_id: Optional[str] = Cookie(default=None),
):
    if not session_id:
        raise HTTPException(401, detail="No session cookie.")
    session = await _get_session(session_id)
    _require_active(session)
    if not session.get("quiz_submitted_at"):
        raise HTTPException(422, detail="Quiz not submitted yet.")

    tags = json.loads(session["filter_tags"]) if session.get("filter_tags") else []
    brands = json.loads(session["filter_brands"]) if session.get("filter_brands") else []
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
        "UPDATE sessions SET filter_collections=?, reco_order=?, extra_reco_order=NULL WHERE session_id=?",
        (json.dumps(selections), json.dumps(reco_order), session_id),
    )
    await db.commit()

    return FilterCollectionsResponse(stroller_count=stroller_count, accessory_count=accessory_count)


def _tags_from_answers(body: TagQuizRequest) -> list[str]:
    """Map answer indices to catalog tags server-side; tags never travel to the client."""
    config = load_tag_questions()
    question_map = {q["id"]: q for q in config["questions"]}

    tags: list[str] = []
    seen: set[str] = set()
    for ans in body.answers:
        q = question_map.get(ans.question_id)
        if not q:
            raise HTTPException(422, detail=f"Unknown question_id: {ans.question_id}")
        if not q["multi"] and len(ans.option_indices) > 1:
            raise HTTPException(422, detail=f"Question {ans.question_id} accepts one answer.")
        opt_map = {o["index"]: o for o in q["options"]}
        for idx in ans.option_indices:
            opt = opt_map.get(idx)
            if opt is None:
                raise HTTPException(422, detail=f"Invalid option_index {idx} for {ans.question_id}.")
            for tag in opt.get("tags", []):
                if tag not in seen:
                    seen.add(tag)
                    tags.append(tag)
    return tags


@router.post("/current/tag-quiz/count", response_model=TagCountResponse)
async def tag_quiz_count(
    body: TagQuizRequest,
    session_id: Optional[str] = Cookie(default=None),
):
    """Preview match counts for the currently-selected tags. Does not mutate the session.

    Test/debug aid: lets us watch how many strollers remain after each selection.
    """
    if not session_id:
        raise HTTPException(401, detail="No session cookie.")
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
    session_id: Optional[str] = Cookie(default=None),
):
    if not session_id:
        raise HTTPException(401, detail="No session cookie.")
    session = await _get_session(session_id)
    _require_active(session)
    if not session.get("quiz_submitted_at"):
        raise HTTPException(422, detail="Quiz not submitted yet.")

    tags = _tags_from_answers(body)
    catalog = get_catalog()
    profile = session.get("derived_profile")

    # Strict AND, with progressive tag-drop fallback so a combination never dead-ends.
    strict_count = len(catalog.get_filtered_strollers(tags or None, tag_match="all"))
    reco_order, kept, dropped = compute_progressive_tag_order(catalog, profile, tags)

    if not dropped:
        match_mode = "all"
    elif kept:
        match_mode = "partial"
    else:
        match_mode = "none"

    stroller_count = len(reco_order)
    accessory_count = len(catalog.get_filtered_accessories(kept or None, tag_match="all"))

    logger.info(
        "tag-quiz submit | session=%s selected=%s kept=%s dropped=%s | strict(AND)=%d used=%d mode=%s",
        session_id, tags, kept, dropped, strict_count, stroller_count, match_mode,
    )

    # Store the effective (kept) tags so reco_order and filter_tags stay consistent.
    db = await get_db()
    await db.execute(
        """UPDATE sessions SET filter_tags=?, filter_brands=NULL, filter_collections=NULL,
           reco_order=?, extra_reco_order=NULL WHERE session_id=?""",
        (json.dumps(kept), json.dumps(reco_order), session_id),
    )
    await db.commit()

    return TagQuizResponse(
        stroller_count=stroller_count,
        accessory_count=accessory_count,
        match_mode=match_mode,
        strict_count=strict_count,
        dropped_count=len(dropped),
    )


@router.post("/current/note")
async def save_note(
    body: NoteRequest,
    session_id: Optional[str] = Cookie(default=None),
):
    if not session_id:
        raise HTTPException(401, detail="No session cookie.")
    session = await _get_session(session_id)
    _require_active(session)
    if not session.get("quiz_submitted_at"):
        raise HTTPException(422, detail="Quiz not submitted yet.")

    note = body.note[:1000] if body.note else None
    reco_order: list[str] = json.loads(session["reco_order"]) if session.get("reco_order") else []

    if note and reco_order:
        from app.services.llm import rerank_by_note
        catalog = get_catalog()
        stroller_dicts = [s for id_ in reco_order if (s := catalog.get_stroller(id_))]
        llm_result = await rerank_by_note(stroller_dicts, note)
        if llm_result:
            llm_set = set(llm_result)
            missing = [id_ for id_ in reco_order if id_ not in llm_set]
            reco_order = llm_result + missing

    db = await get_db()
    await db.execute(
        "UPDATE sessions SET optional_note=?, reco_order=? WHERE session_id=?",
        (note, json.dumps(reco_order) if reco_order else None, session_id),
    )
    await db.commit()

    return {"note": note}


@router.post("/current/favorites", response_model=FavoriteToggleResponse)
async def toggle_favorite(
    body: FavoriteToggleRequest,
    session_id: Optional[str] = Cookie(default=None),
):
    if not session_id:
        raise HTTPException(401, detail="No session cookie.")
    session = await _get_session(session_id)
    _require_active(session)

    catalog = get_catalog()
    stroller_favs: list[str] = json.loads(session["stroller_favorites"]) if session.get("stroller_favorites") else []
    accessory_favs: list[str] = json.loads(session["accessory_favorites"]) if session.get("accessory_favorites") else []

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


@router.post("/current/handoff", response_model=HandoffResponse)
async def handoff(
    background_tasks: BackgroundTasks,
    session_id: Optional[str] = Cookie(default=None),
):
    if not session_id:
        raise HTTPException(401, detail="No session cookie.")
    session = await _get_session(session_id)

    if session["status"] == "handed_off":
        raise HTTPException(409, detail="Session already handed off.")
    if not session.get("quiz_submitted_at"):
        raise HTTPException(422, detail="Quiz not submitted yet.")
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
async def abandon(session_id: Optional[str] = Cookie(default=None)):
    if not session_id:
        raise HTTPException(401, detail="No session cookie.")
    session = await _get_session(session_id)

    if session["status"] == "handed_off":
        raise HTTPException(409, detail="Session is locked after handoff.")

    db = await get_db()
    await db.execute(
        "UPDATE sessions SET status='abandoned' WHERE session_id=?",
        (session_id,),
    )
    await db.commit()
    return {"status": "abandoned"}
