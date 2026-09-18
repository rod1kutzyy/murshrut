from datetime import datetime
from pydantic import BaseModel


class MaxProfileDTO(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None


class CategoryDTO(BaseModel):
    id: str
    name: str


class ProviderEventDTO(BaseModel):
    external_id: str
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
