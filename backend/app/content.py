import json
import os
from functools import lru_cache

_QUIZ_PATH = os.path.join(os.path.dirname(__file__), "..", "content", "quiz_questions.json")
_TAG_QUESTIONS_PATH = os.path.join(os.path.dirname(__file__), "..", "content", "tag_questions.json")
_CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "..", "content", "categories.json")


@lru_cache(maxsize=None)
def load_quiz_config() -> dict:
    with open(_QUIZ_PATH, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=None)
def load_tag_questions() -> dict:
    with open(_TAG_QUESTIONS_PATH, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=None)
def load_categories() -> dict:
    with open(_CATEGORIES_PATH, encoding="utf-8") as f:
        return json.load(f)


def category_label(category_id: str) -> str:
    cats = {c["id"]: c["label"] for c in load_categories()["categories"]}
    return cats.get(category_id, category_id)


def category_labels(category_ids: list[str]) -> list[str]:
    cats = {c["id"]: c["label"] for c in load_categories()["categories"]}
    return [cats.get(cid, cid) for cid in category_ids]
