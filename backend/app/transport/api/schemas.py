from datetime import datetime
from uuid import UUID
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ErrorOut(BaseModel):
    """Ошибка бизнес-правила или доступа."""

    detail: str


class ValidationIssue(BaseModel):
    """Одна ошибка проверки структуры запроса."""

    model_config = ConfigDict(extra="allow")

    type: str
    loc: list[str | int]
    msg: str
    input: Any | None = None
    ctx: dict[str, Any] | None = None


class RequestValidationErrorOut(BaseModel):
    """Ошибки автоматической проверки запроса FastAPI."""

    detail: list[ValidationIssue]


class AuthInput(BaseModel):
    """Подписанная строка инициализации MAX WebApp."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"init_data": "auth_date=...&user=...&hash=..."}]
        }
    )

    init_data: str = Field(
        max_length=20000,
        description="Неизменённая строка initData, полученная от MAX Bridge.",
    )


class UserOut(BaseModel):
    id: UUID
    first_name: str
    city: str
    onboarding_completed: bool


class PreferencesInput(BaseModel):
    """Настройки персонализации и условия досуга пользователя."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "city": "Москва",
                    "categories": ["koncerty", "vystavki"],
                    "budget_max": 3000,
                    "companion": "friends",
                    "preferred_days": "weekends",
                    "preferred_time": "evening",
                }
            ]
        }
    )

    city: str = Field(min_length=2, max_length=200)
    categories: list[str] = Field(min_length=1, max_length=20)
    budget_max: int | None = Field(default=None, ge=0, le=1000000)
    companion: Literal["solo", "friends", "partner", "family", "children"] = "friends"
    preferred_days: Literal["any", "weekdays", "weekends"] = "any"
    preferred_time: Literal["any", "morning", "day", "evening"] = "any"


class ReactionInput(BaseModel):
    """Реакция пользователя на событие."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"reaction": "like"}]})

    reaction: Literal["like", "dislike"]


class EventOut(BaseModel):
    id: UUID
    title: str
    description: str
    category: str
    category_name: str
    tags: list[str]
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
    reasons: list[str] = Field(default_factory=list)


class CatalogEventOut(EventOut):
    is_saved: bool


class CatalogOut(BaseModel):
    items: list[CatalogEventOut]
    total: int
    has_more: bool


class AuthOut(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "user": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "first_name": "Алексей",
                        "city": "Москва",
                        "onboarding_completed": True,
                    },
                }
            ]
        }
    )

    access_token: str
    token_type: str = "bearer"
    user: UserOut


class CategoryOut(BaseModel):
    id: str
    name: str


class PreferencesOut(BaseModel):
    city: str
    categories: list[str]
    budget_max: int | None
    companion: str
    preferred_days: str
    preferred_time: str


class ConfigOut(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "demo_mode": True,
                    "event_provider": "demo",
                    "max_bot_name": "",
                    "demo_cities": ["Москва", "Санкт-Петербург", "Казань"],
                }
            ]
        }
    )

    demo_mode: bool
    event_provider: str
    max_bot_name: str
    demo_cities: list[str]


class HealthOut(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "ok"}]})

    status: str


class ReactionOut(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"reaction": "like"}]})

    reaction: str


class SyncOut(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"synced": 42}]})

    synced: int


class EveningInput(BaseModel):
    """Условия генерации маршрута на вечер."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "vibe": "culture",
                    "duration_hours": 4,
                    "budget_max": 3000,
                    "excluded_plan_ids": [],
                }
            ]
        }
    )

    vibe: Literal["active", "calm", "date", "learn", "culture", "surprise"]
    duration_hours: Literal[2, 4, 6]
    budget_max: Literal[0, 1000, 3000] | None
    excluded_plan_ids: list[UUID] = Field(default_factory=list, max_length=200)


class TransferOut(BaseModel):
    distance_km: float
    minutes: int


class EveningEventOut(EventOut):
    estimated_price: int | None
    next_transfer: TransferOut | None


class EveningOut(BaseModel):
    id: UUID
    saved: bool
    created_at: datetime
    city: str
    date: str
    vibe: str
    duration_hours: int
    budget_max: int | None
    events: list[EveningEventOut]
    event_count: int
    total_cost: int
    cost_complete: bool
    duration_minutes: int
    score: float
    score_components: dict[str, float]
    reasons: list[str]
    warnings: list[str] = Field(default_factory=list)


class EveningGenerationOut(BaseModel):
    plan: EveningOut | None
    reason: Literal["no_matches", "exhausted"] | None
