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

    def get_tags(self) -> list[str]:
        tags: set[str] = set()
        for item in list(self._strollers.values()) + list(self._accessories.values()):
            tags.update(item.get("tags", []))
        return sorted(tags)

    def get_brands_for_tags(self, tags: list[str]) -> list[str]:
        brands: set[str] = set()
        for item in list(self._strollers.values()) + list(self._accessories.values()):
            if not tags or any(t in item.get("tags", []) for t in tags):
                brands.add(item["brand"])
        return sorted(brands)

    def get_collections_for_brands(self, brands: list[str]) -> dict[str, list[str]]:
        brand_lower = {b.lower(): b for b in brands}
        result: dict[str, list[str]] = {b: [] for b in brands}
        for item in list(self._strollers.values()) + list(self._accessories.values()):
            b_key = item["brand"].lower()
            if b_key in brand_lower:
                b = brand_lower[b_key]
                coll = item.get("collection")
                if coll and coll not in result[b]:
                    result[b].append(coll)
        return {b: sorted(colls) for b, colls in result.items()}

    def _matches_filter(
        self,
        item: dict,
        tags: list[str],
        brands: list[str],
        collections: list[dict],
        tag_match: str = "any",
    ) -> bool:
        if tags:
            item_tags = item.get("tags", [])
            if tag_match == "all":
                if not all(t in item_tags for t in tags):
                    return False
            elif not any(t in item_tags for t in tags):
                return False
        if brands and item.get("brand", "").lower() not in {b.lower() for b in brands}:
            return False
        if collections:
            item_brand = item.get("brand", "").lower()
            item_coll = item.get("collection")
            if not any(
                sel.get("brand", "").lower() == item_brand
                and (sel.get("collection") is None or sel.get("collection") == item_coll)
                for sel in collections
            ):
                return False
        return True

    def get_filtered_strollers(
        self,
        tags: list[str] | None = None,
        brands: list[str] | None = None,
        collections: list[dict] | None = None,
        tag_match: str = "any",
    ) -> list[dict]:
        t, b, c = tags or [], brands or [], collections or []
        if not t and not b and not c:
            return self.get_all_strollers()
        return [s for s in self._strollers.values() if self._matches_filter(s, t, b, c, tag_match)]

    def get_filtered_accessories(
        self,
        tags: list[str] | None = None,
        brands: list[str] | None = None,
        collections: list[dict] | None = None,
        tag_match: str = "any",
    ) -> list[dict]:
        t, b, c = tags or [], brands or [], collections or []
        if not t and not b and not c:
            return self.get_all_accessories()
        return [a for a in self._accessories.values() if self._matches_filter(a, t, b, c, tag_match)]


_catalog: CatalogService | None = None


def get_catalog() -> CatalogService:
    global _catalog
    if _catalog is None:
        _catalog = CatalogService()
    return _catalog
