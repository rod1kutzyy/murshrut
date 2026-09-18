from dataclasses import dataclass

from .entities import Event, Preferences, User


@dataclass(frozen=True)
class AuthenticationResult:
    user: User
    access_token: str


@dataclass(frozen=True)
class PreferencesResult:
    city: str
    preferences: Preferences


@dataclass(frozen=True)
class RecommendedEvent:
    event: Event
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CatalogEvent:
    event: Event
    is_saved: bool


@dataclass(frozen=True)
class CatalogResult:
    items: tuple[CatalogEvent, ...]
    total: int
    has_more: bool


@dataclass(frozen=True)
class ReactionResult:
    reaction: str


@dataclass(frozen=True)
class HealthResult:
    status: str = 'ok'


@dataclass(frozen=True)
class SyncResult:
    synced: int
