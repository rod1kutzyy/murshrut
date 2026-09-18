from dataclasses import dataclass
from datetime import date
from uuid import UUID

from .entities import Preferences


@dataclass(frozen=True)
class SavePreferencesCommand:
    city: str
    preferences: Preferences


@dataclass(frozen=True)
class ReactCommand:
    event_id: UUID
    reaction: str


@dataclass(frozen=True)
class CatalogQuery:
    q: str = ""
    date_mode: str = "any"
    selected_date: date | None = None
    categories: tuple[str, ...] = ()
    free_only: bool = False
    budget_max: int | None = None
    evening: bool = False
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class EveningQuery:
    vibe: str
    duration_hours: int
    budget_max: int | None
    excluded_plan_ids: tuple[UUID, ...] = ()
