from ..service import entities
from . import models


def user_from_model(row: models.User) -> entities.User:
    return entities.User(id=row.id, first_name=row.first_name, city=row.city,
                         onboarding_completed=row.onboarding_completed)


def identity_to_values(identity: entities.Identity) -> dict:
    return {'first_name': identity.first_name, 'last_name': identity.last_name,
            'username': identity.username, 'photo_url': identity.photo_url}


def preferences_from_model(row: models.UserPreference) -> entities.Preferences:
    return entities.Preferences(categories=tuple(row.categories), budget_max=row.budget_max,
                                companion=row.companion, preferred_days=row.preferred_days,
                                preferred_time=row.preferred_time)


def preferences_to_values(preferences: entities.Preferences) -> dict:
    return {'categories': list(preferences.categories), 'budget_max': preferences.budget_max,
            'companion': preferences.companion, 'preferred_days': preferences.preferred_days,
            'preferred_time': preferences.preferred_time}


def event_from_model(row: models.Event) -> entities.Event:
    return entities.Event(
        id=row.id, external_id=row.external_id, title=row.title, description=row.description,
        category=row.category, category_name=row.category_name, tags=tuple(row.tags),
        image_url=row.image_url, image_credit=row.image_credit,
        start_date=row.start_date, end_date=row.end_date, timezone=row.timezone,
        price_min=row.price_min, price_max=row.price_max, is_free=row.is_free,
        city=row.city, location_name=row.location_name, address=row.address,
        latitude=row.latitude, longitude=row.longitude, source_url=row.source_url,
        provider=row.provider,
    )


def event_to_values(event: entities.EventDraft) -> dict:
    return {
        'external_id': event.external_id, 'title': event.title, 'description': event.description,
        'category': event.category, 'category_name': event.category_name, 'tags': list(event.tags),
        'image_url': event.image_url, 'image_credit': event.image_credit,
        'start_date': event.start_date, 'end_date': event.end_date, 'timezone': event.timezone,
        'price_min': event.price_min, 'price_max': event.price_max, 'is_free': event.is_free,
        'city': event.city, 'location_name': event.location_name, 'address': event.address,
        'latitude': event.latitude, 'longitude': event.longitude, 'source_url': event.source_url,
        'provider': event.provider,
    }


def reaction_from_row(event_id, category, reaction) -> entities.Reaction:
    return entities.Reaction(event_id=event_id, category=category, reaction=reaction)
