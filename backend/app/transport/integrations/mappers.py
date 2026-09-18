from ...service.entities import Category, EventDraft, Identity
from .schemas import CategoryDTO, MaxProfileDTO, ProviderEventDTO


def profile_to_identity(profile: MaxProfileDTO) -> Identity:
    return Identity(max_user_id=profile.id, first_name=profile.first_name or 'Друг',
                    last_name=profile.last_name, username=profile.username, photo_url=profile.photo_url)


def category_to_entity(category: CategoryDTO) -> Category:
    return Category(id=category.id, name=category.name)


def provider_event_to_entity(event: ProviderEventDTO) -> EventDraft:
    return EventDraft(
        external_id=event.external_id, title=event.title, description=event.description,
        category=event.category, category_name=event.category_name, tags=tuple(event.tags),
        image_url=event.image_url, image_credit=event.image_credit,
        start_date=event.start_date, end_date=event.end_date, timezone=event.timezone,
        price_min=event.price_min, price_max=event.price_max, is_free=event.is_free,
        city=event.city, location_name=event.location_name, address=event.address,
        latitude=event.latitude, longitude=event.longitude, source_url=event.source_url, provider=event.provider,
    )
