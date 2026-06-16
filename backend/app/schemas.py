from enum import Enum
from pydantic import BaseModel
from typing import Optional


class SessionStatus(str, Enum):
    active = "active"
    handed_off = "handed_off"
    abandoned = "abandoned"


class SessionSource(str, Enum):
    store = "store"
    home = "home"


class EmailStatus(str, Enum):
    not_sent = "not_sent"
    pending = "pending"
    sent = "sent"
    failed = "failed"


class QuizOption(BaseModel):
    index: int
    text: str


class QuizQuestion(BaseModel):
    id: int
    text: str
    options: list[QuizOption]


class OptionalNoteConfig(BaseModel):
    text: str
    skip_label: str
    continue_label: str
    max_length: int


class QuizConfigResponse(BaseModel):
    questions: list[QuizQuestion]
    optional_note: OptionalNoteConfig


class TagQuestionOption(BaseModel):
    index: int
    text: str


class TagQuestion(BaseModel):
    id: str
    text: str
    subtitle: Optional[str] = None
    multi: bool
    options: list[TagQuestionOption]


class TagConfigResponse(BaseModel):
    questions: list[TagQuestion]


class TagAnswerIn(BaseModel):
    question_id: str
    option_indices: list[int] = []


class TagQuizRequest(BaseModel):
    answers: list[TagAnswerIn] = []


class TagQuizResponse(BaseModel):
    stroller_count: int
    accessory_count: int
    match_mode: str  # "all" | "partial" (some tags dropped) | "none" (all dropped)
    strict_count: int  # AND of all selected tags, before any relaxation
    dropped_count: int  # number of tags relaxed away to find matches


class TagCountResponse(BaseModel):
    strict_count: int  # AND across selected tags
    relaxed_count: int  # OR across selected tags
    total_count: int  # all strollers (no tag filter)


class QuizAnswerIn(BaseModel):
    question_id: int
    option_index: int


class QuizSubmitRequest(BaseModel):
    answers: list[QuizAnswerIn]
    optional_note: str = ""


class QuizSubmitResponse(BaseModel):
    profile: str
    transition_phrase: str


class VariantSummary(BaseModel):
    id: str
    name: str
    image_url: str
    price: float
    availability: str
    is_available: bool
    colour_label: str


class AccessoryItem(BaseModel):
    id: str
    name: str
    brand: str
    price: float
    description: str
    image_url: str
    availability: str
    is_available: bool
    reason: str = ""  # why this accessory is shown (e.g. "Uit de collectie")


class StrollerItem(BaseModel):
    id: str
    name: str
    brand: str
    price: float
    description: str
    formatted_description: Optional[str] = None
    image_url: str
    availability: str
    is_available: bool
    key_features: str
    cross_sell_items: list[AccessoryItem]
    show_cross_sell_chips: bool = False
    variant_count: int = 1  # number of colour/size variants of this product (incl. itself)
    variant_ids: list[str] = []  # ids of all variants, available-first; this product included
    variant_summaries: list[VariantSummary] = []  # compact data for the colour picker


class TierInfo(BaseModel):
    label: str  # customer-facing heading; never names a hidden tag
    start_index: int  # index into the flat product order where this tier begins


class RecommendationBatchResponse(BaseModel):
    batch: int
    favorites_adaptation_active: bool
    products: list[StrollerItem]
    tiers: list[TierInfo] = []


class FavoriteToggleRequest(BaseModel):
    item_id: str
    item_type: str  # "stroller" | "accessory"


class FavoriteToggleResponse(BaseModel):
    stroller_favorites: list[str]
    accessory_favorites: list[str]


class NamedItem(BaseModel):
    """Minimal product identity for staff-facing views: an ID, label, and thumbnail."""
    id: str
    name: str
    brand: str
    image_url: str = ""
    price: float | None = None


class ShortlistItem(BaseModel):
    id: str
    name: str
    brand: str
    price: float
    image_url: str
    availability: str
    is_available: bool


class FavoriteItemsResponse(BaseModel):
    strollers: list[ShortlistItem]
    accessories: list[ShortlistItem]


class SessionCreateResponse(BaseModel):
    session_id: str
    session_code: str


class SessionCurrentResponse(BaseModel):
    session_id: str
    session_code: str
    source: str
    status: str
    started_at: str
    quiz_submitted_at: Optional[str] = None
    handoff_at: Optional[str] = None
    quiz_answers: list[dict] = []
    optional_note: Optional[str] = None
    profile: Optional[str] = None
    transition_phrase: Optional[str] = None
    shown_products: list[list[str]] = []
    stroller_favorites: list[str] = []
    accessory_favorites: list[str] = []
    shown_products_named: list[list[NamedItem]] = []
    stroller_favorites_named: list[NamedItem] = []
    accessory_favorites_named: list[NamedItem] = []
    email_status: str = "not_sent"
    favorites_adaptation_active: bool = False
    contact_name: Optional[str] = None
    contact_surname: Optional[str] = None
    contact_email: Optional[str] = None
    talking_points: Optional[list[str]] = None


class HandoffRequest(BaseModel):
    """Optional contact details a customer may fill in before handoff. All optional —
    a customer can hand off with just the session code and no contact info."""
    name: Optional[str] = None
    surname: Optional[str] = None
    email: Optional[str] = None


class HandoffResponse(BaseModel):
    session_code: str
    handoff_at: str
    email_status: str


class StaffSessionItem(BaseModel):
    session_id: str
    session_code: str
    source: str
    status: str
    started_at: str
    handoff_at: Optional[str] = None
    profile: Optional[str] = None
    email_status: Optional[str] = None


class TagsListResponse(BaseModel):
    tags: list[str]


class FilterTagsRequest(BaseModel):
    tags: list[str] = []


class FilterTagsResponse(BaseModel):
    brands: list[str]


class FilterBrandsRequest(BaseModel):
    brands: list[str] = []


class BrandCollections(BaseModel):
    brand: str
    collections: list[str]


class FilterBrandsResponse(BaseModel):
    brands: list[BrandCollections]


class CollectionSelection(BaseModel):
    brand: str
    collection: Optional[str] = None


class FilterCollectionsRequest(BaseModel):
    selections: list[CollectionSelection] = []


class FilterCollectionsResponse(BaseModel):
    stroller_count: int
    accessory_count: int


class NoteRequest(BaseModel):
    note: str = ""


class StaffSessionDetail(BaseModel):
    session_id: str
    session_code: str
    source: str
    status: str
    started_at: str
    handoff_at: Optional[str] = None
    profile: Optional[str] = None
    quiz_answers: list[dict] = []
    tag_answers: list[dict] = []
    optional_note: Optional[str] = None
    shown_products: list[list[str]] = []
    stroller_favorites: list[str] = []
    accessory_favorites: list[str] = []
    shown_products_named: list[list[NamedItem]] = []
    stroller_favorites_named: list[NamedItem] = []
    accessory_favorites_named: list[NamedItem] = []
    talking_points: Optional[list[str]] = None
    email_status: Optional[str] = None
    email_failed_warning: bool = False
    contact_name: Optional[str] = None
    contact_surname: Optional[str] = None
    contact_email: Optional[str] = None
