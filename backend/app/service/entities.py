from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True)
class Identity:
    max_user_id: int
    first_name: str = "Друг"
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None


@dataclass(frozen=True)
class User:
    id: UUID
    first_name: str
    city: str
    onboarding_completed: bool


@dataclass(frozen=True)
class Preferences:
    categories: tuple[str, ...]
    budget_max: int | None
    companion: str
    preferred_days: str
    preferred_time: str


@dataclass(frozen=True)
class Category:
    id: str
    name: str


@dataclass(frozen=True, kw_only=True)
class EventDraft:
    external_id: str
    title: str
    description: str
    category: str
    category_name: str
    tags: tuple[str, ...]
    image_url: str | None
    image_credit: str | None
    start_date: datetime
    end_date: datetime
    timezone: str
    price_min: float | None
    price_max: float | None
    is_free: bool
    city: str
    location_name: str
    address: str
    latitude: float | None
    longitude: float | None
    source_url: str | None
    provider: str


@dataclass(frozen=True, kw_only=True)
class Event(EventDraft):
    id: UUID


@dataclass(frozen=True)
class Reaction:
    event_id: UUID
    category: str
    reaction: str


@dataclass(frozen=True)
class ServiceConfig:
    demo_mode: bool
    event_provider: str
    max_bot_name: str
    demo_cities: tuple[str, ...]
    sync_interval_seconds: int
    admin_sync_token: str


@dataclass(frozen=True)
class ReactionCounts:
    likes: int
    total: int


@dataclass(frozen=True)
class EveningTransfer:
    distance_km: float
    minutes: int


@dataclass(frozen=True)
class EveningStop:
    event: Event
    estimated_price: int | None
    next_transfer: EveningTransfer | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class EveningScore:
    interests_match: float
    swipe_history_match: float
    category_match: float
    budget_match: float
    distance_match: float
    popularity: float


@dataclass(frozen=True)
class EveningRoute:
    city: str
    date: date
    vibe: str
    duration_hours: int
    budget_max: int | None
    events: tuple[EveningStop, ...]
    total_cost: int
    cost_complete: bool
    duration_minutes: int
    score: float
    score_components: EveningScore
    reasons: tuple[str, ...]

    @property
    def event_count(self) -> int:
        return len(self.events)


@dataclass(frozen=True)
class EveningPlan:
    id: UUID
    user_id: UUID
    route: EveningRoute
    created_at: datetime
    saved: bool = False
