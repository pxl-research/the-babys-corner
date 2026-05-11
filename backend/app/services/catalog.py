import json
import logging
import os
from app.config import settings

logger = logging.getLogger(__name__)

REQUIRED_STROLLER_FIELDS = {"id", "name", "brand", "price", "description", "image_url", "availability"}
REQUIRED_ACCESSORY_FIELDS = {"id", "name", "brand", "price", "description", "image_url", "availability"}


def is_available(item: dict) -> bool:
    return item.get("availability") == "Op voorraad"


def _validate_item(item: dict, required: set[str]) -> bool:
    missing = required - item.keys()
    if missing:
        logger.warning("Catalog item %s missing fields: %s — skipped", item.get("id", "?"), missing)
        return False
    return True


class CatalogService:
    def __init__(self, strollers: list[dict] | None = None, accessories: list[dict] | None = None):
        if strollers is None and accessories is None:
            data = self._load_file()
            strollers = data.get("strollers", [])
            accessories = data.get("accessories", [])

        self._strollers: dict[str, dict] = {}
        for s in (strollers or []):
            if _validate_item(s, REQUIRED_STROLLER_FIELDS):
                self._strollers[s["id"]] = s

        self._accessories: dict[str, dict] = {}
        for a in (accessories or []):
            if _validate_item(a, REQUIRED_ACCESSORY_FIELDS):
                self._accessories[a["id"]] = a

    @staticmethod
    def _load_file() -> dict:
        path = settings.catalog_path
        if not os.path.exists(path):
            # fallback for dev
            path = os.path.join(os.path.dirname(__file__), "..", "..", "catalog", "catalog.json")
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def get_stroller(self, id_: str) -> dict | None:
        return self._strollers.get(id_)

    def get_accessory(self, id_: str) -> dict | None:
        return self._accessories.get(id_)

    def get_all_strollers(self) -> list[dict]:
        return list(self._strollers.values())

    def get_all_accessories(self) -> list[dict]:
        return list(self._accessories.values())


_catalog: CatalogService | None = None


def get_catalog() -> CatalogService:
    global _catalog
    if _catalog is None:
        _catalog = CatalogService()
    return _catalog
