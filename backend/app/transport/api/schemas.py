from datetime import datetime
from uuid import UUID
from typing import Literal
from pydantic import BaseModel, Field

class AuthInput(BaseModel):
    init_data: str = Field(max_length=20000)

class UserOut(BaseModel):
    id: UUID
    first_name: str
    city: str
    onboarding_completed: bool

class PreferencesInput(BaseModel):
    city: str = Field(min_length=2, max_length=200)
    categories: list[str] = Field(min_length=1, max_length=20)
    budget_max: int | None = Field(default=None, ge=0, le=1000000)
    companion: Literal['solo', 'friends', 'partner', 'family', 'children'] = 'friends'
    preferred_days: Literal['any', 'weekdays', 'weekends'] = 'any'
    preferred_time: Literal['any', 'morning', 'day', 'evening'] = 'any'

class ReactionInput(BaseModel):
    reaction: Literal['like', 'dislike']

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
    access_token: str
    token_type: str = 'bearer'
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
    demo_mode: bool
    event_provider: str
    max_bot_name: str
    demo_cities: list[str]

class HealthOut(BaseModel):
    status: str

class ReactionOut(BaseModel):
    reaction: str

class SyncOut(BaseModel):
    synced: int
