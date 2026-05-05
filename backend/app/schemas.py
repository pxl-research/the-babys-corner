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


class QuizAnswerIn(BaseModel):
    question_id: int
    option_index: int


class QuizSubmitRequest(BaseModel):
    answers: list[QuizAnswerIn]
    optional_note: str = ""


class QuizSubmitResponse(BaseModel):
    profile: str
    transition_phrase: str


class AccessoryItem(BaseModel):
    id: str
    name: str
    brand: str
    price: float
    description: str
    image_url: str
    availability: str
    is_available: bool


class StrollerItem(BaseModel):
    id: str
    name: str
    brand: str
    price: float
    description: str
    image_url: str
    availability: str
    is_available: bool
    key_features: str
    cross_sell_items: list[AccessoryItem]
    show_cross_sell_chips: bool = False


class RecommendationBatchResponse(BaseModel):
    batch: int
    favorites_adaptation_active: bool
    products: list[StrollerItem]


class FavoriteToggleRequest(BaseModel):
    item_id: str
    item_type: str  # "stroller" | "accessory"


class FavoriteToggleResponse(BaseModel):
    stroller_favorites: list[str]
    accessory_favorites: list[str]


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
    email_status: str = "not_sent"
    favorites_adaptation_active: bool = False


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


class StaffSessionDetail(BaseModel):
    session_id: str
    session_code: str
    source: str
    status: str
    started_at: str
    handoff_at: Optional[str] = None
    profile: Optional[str] = None
    quiz_answers: list[dict] = []
    optional_note: Optional[str] = None
    shown_products: list[list[str]] = []
    stroller_favorites: list[str] = []
    accessory_favorites: list[str] = []
    talking_points: Optional[list[str]] = None
    email_status: Optional[str] = None
    email_failed_warning: bool = False
