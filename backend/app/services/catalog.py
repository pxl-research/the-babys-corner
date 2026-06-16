import json
import logging
import os
from app.config import settings

logger = logging.getLogger(__name__)

REQUIRED_STROLLER_FIELDS = {"id", "name", "brand", "price", "description", "image_url", "availability"}
REQUIRED_ACCESSORY_FIELDS = {"id", "name", "brand", "price", "description", "image_url", "availability"}


def is_available(item: dict) -> bool:
    return item.get("availability") == "Op voorraad"


def _id_sort_key(id_: str) -> tuple[int, object]:
    """Sort numeric ids numerically, fall back to string for non-numeric ids."""
    return (0, int(id_)) if id_.isdigit() else (1, id_)


def group_id_of(item: dict) -> str:
    """Variant-group key for an item: the feed's groep_id, or the item's own id when
    it belongs to no group. Items sharing a group are colour/size variants of one
    product."""
    return (item.get("group_id") or "").strip() or item.get("id", "")


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

        # Map each variant group to its member ids (available-first, then lowest id),
        # so the stroller assortment can be shown one representative per product
        # instead of once per colour/size. Accessories are left ungrouped — cross-sell
        # already de-dupes them by name.
        self._variant_members: dict[str, list[str]] = {}
        for s in self._strollers.values():
            self._variant_members.setdefault(group_id_of(s), []).append(s["id"])
        for ids in self._variant_members.values():
            ids.sort(key=lambda i: (not is_available(self._strollers[i]), _id_sort_key(i)))

    @staticmethod
    def _load_file() -> dict:
        path = settings.catalog_path
        if not os.path.exists(path):
            # fallback for dev
            path = os.path.join(os.path.dirname(__file__), "..", "..", "catalog", "catalog.json")
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _colour_label(name: str, common_prefix: str) -> str:
        """Strip the shared product-name prefix from a variant name to get the colour label.
        Falls back to the full name when nothing remains after stripping."""
        suffix = name[len(common_prefix):].strip(" -–—")
        return suffix if suffix else name.strip()

    @staticmethod
    def _common_prefix(names: list[str]) -> str:
        """Longest common prefix of all variant names, trimmed to a word boundary."""
        if not names:
            return ""
        prefix = names[0]
        for n in names[1:]:
            while not n.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix:
                    return ""
        # Already ends on a word boundary (trailing space) — return as-is.
        if prefix.endswith(" "):
            return prefix
        # Otherwise trim back to the last space.
        last_space = prefix.rfind(" ")
        return prefix[: last_space + 1] if last_space >= 0 else ""

    def _build_variant_summaries(self, member_ids: list[str]) -> list[dict]:
        """Compact per-variant data for the colour picker (id, name, image, price,
        availability, colour_label). Sorted available-first, then lowest id."""
        names = [self._strollers[i]["name"] for i in member_ids if i in self._strollers]
        prefix = self._common_prefix(names)
        summaries = []
        for i in member_ids:
            s = self._strollers.get(i)
            if not s:
                continue
            summaries.append({
                "id": i,
                "name": s["name"],
                "image_url": s["image_url"],
                "price": s["price"],
                "availability": s["availability"],
                "is_available": is_available(s),
                "colour_label": self._colour_label(s["name"], prefix),
            })
        return summaries

    def _with_variants(self, item: dict) -> dict:
        """Annotate a stroller with its variant group: `variant_ids` (all members,
        available-first), `variant_count`, and `variant_summaries` (compact per-variant
        data for the colour picker). Returns a shallow copy so the stored item stays
        pristine."""
        members = self._variant_members.get(group_id_of(item), [item["id"]])
        return {
            **item,
            "group_id": group_id_of(item),
            "variant_ids": members,
            "variant_count": len(members),
            "variant_summaries": self._build_variant_summaries(members),
        }

    def _representative_id(self, member_ids: list[str]) -> str:
        """Pick the representative of a variant group among the given members:
        the group leader (id == group_id) first, then an available item, then lowest id."""
        return min(
            member_ids,
            key=lambda i: (
                group_id_of(self._strollers[i]) != i,
                not is_available(self._strollers[i]),
                _id_sort_key(i),
            ),
        )

    def _collapse(self, items: list[dict]) -> list[dict]:
        """Collapse variants to one representative per group, preserving first-seen
        group order. The representative is chosen among the items actually present
        (so a filtered-out colour never becomes the representative)."""
        by_group: dict[str, list[str]] = {}
        order: list[str] = []
        for it in items:
            g = group_id_of(it)
            if g not in by_group:
                by_group[g] = []
                order.append(g)
            by_group[g].append(it["id"])
        return [self._with_variants(self._strollers[self._representative_id(by_group[g])]) for g in order]

    def get_stroller(self, id_: str) -> dict | None:
        s = self._strollers.get(id_)
        return self._with_variants(s) if s else None

    def get_accessory(self, id_: str) -> dict | None:
        return self._accessories.get(id_)

    def get_all_strollers(self) -> list[dict]:
        return self._collapse(list(self._strollers.values()))

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
        return self._collapse(
            [s for s in self._strollers.values() if self._matches_filter(s, t, b, c, tag_match)]
        )

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
