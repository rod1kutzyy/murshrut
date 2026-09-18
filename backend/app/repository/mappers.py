from datetime import date, datetime
from uuid import UUID

from ..service import entities
from . import models


def user_from_model(row: models.User) -> entities.User:
    return entities.User(
        id=row.id,
        first_name=row.first_name,
        city=row.city,
        onboarding_completed=row.onboarding_completed,
    )


def identity_to_values(identity: entities.Identity) -> dict:
    return {
        "first_name": identity.first_name,
        "last_name": identity.last_name,
        "username": identity.username,
        "photo_url": identity.photo_url,
    }


def preferences_from_model(row: models.UserPreference) -> entities.Preferences:
    return entities.Preferences(
        categories=tuple(row.categories),
        budget_max=row.budget_max,
        companion=row.companion,
        preferred_days=row.preferred_days,
        preferred_time=row.preferred_time,
    )


def preferences_to_values(preferences: entities.Preferences) -> dict:
    return {
        "categories": list(preferences.categories),
        "budget_max": preferences.budget_max,
        "companion": preferences.companion,
        "preferred_days": preferences.preferred_days,
        "preferred_time": preferences.preferred_time,
    }


def event_from_model(row: models.Event) -> entities.Event:
    return entities.Event(
        id=row.id,
        external_id=row.external_id,
        title=row.title,
        description=row.description,
        category=row.category,
        category_name=row.category_name,
        tags=tuple(row.tags),
        image_url=row.image_url,
        image_credit=row.image_credit,
        start_date=row.start_date,
        end_date=row.end_date,
        timezone=row.timezone,
        price_min=row.price_min,
        price_max=row.price_max,
        is_free=row.is_free,
        city=row.city,
        location_name=row.location_name,
        address=row.address,
        latitude=row.latitude,
        longitude=row.longitude,
        source_url=row.source_url,
        provider=row.provider,
    )


def event_to_values(event: entities.EventDraft) -> dict:
    return {
        "external_id": event.external_id,
        "title": event.title,
        "description": event.description,
        "category": event.category,
        "category_name": event.category_name,
        "tags": list(event.tags),
        "image_url": event.image_url,
        "image_credit": event.image_credit,
        "start_date": event.start_date,
        "end_date": event.end_date,
        "timezone": event.timezone,
        "price_min": event.price_min,
        "price_max": event.price_max,
        "is_free": event.is_free,
        "city": event.city,
        "location_name": event.location_name,
        "address": event.address,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "source_url": event.source_url,
        "provider": event.provider,
    }


def reaction_from_row(event_id, category, reaction) -> entities.Reaction:
    return entities.Reaction(event_id=event_id, category=category, reaction=reaction)


def evening_to_snapshot(route: entities.EveningRoute) -> dict:
    events = []
    for stop in route.events:
        event = event_to_values(stop.event)
        event.update(
            id=str(stop.event.id),
            start_date=stop.event.start_date.isoformat(),
            end_date=stop.event.end_date.isoformat(),
            estimated_price=stop.estimated_price,
            next_transfer={
                "distance_km": stop.next_transfer.distance_km,
                "minutes": stop.next_transfer.minutes,
            }
            if stop.next_transfer
            else None,
            reasons=list(stop.reasons),
        )
        events.append(event)
    return {
        "city": route.city,
        "vibe": route.vibe,
        "duration_hours": route.duration_hours,
        "budget_max": route.budget_max,
        "total_cost": route.total_cost,
        "cost_complete": route.cost_complete,
        "duration_minutes": route.duration_minutes,
        "score": route.score,
        "date": route.date.isoformat(),
        "events": events,
        "event_count": route.event_count,
        "reasons": list(route.reasons),
        "score_components": {
            "interests_match": route.score_components.interests_match,
            "swipe_history_match": route.score_components.swipe_history_match,
            "category_match": route.score_components.category_match,
            "budget_match": route.score_components.budget_match,
            "distance_match": route.score_components.distance_match,
            "popularity": route.score_components.popularity,
        },
    }


def evening_route_from_snapshot(snapshot: dict) -> entities.EveningRoute:
    stops = []
    for item in snapshot["events"]:
        event = entities.Event(
            id=UUID(item["id"]),
            tags=tuple(item["tags"]),
            start_date=datetime.fromisoformat(item["start_date"]),
            end_date=datetime.fromisoformat(item["end_date"]),
            external_id=item["external_id"],
            title=item["title"],
            description=item["description"],
            category=item["category"],
            category_name=item["category_name"],
            image_url=item["image_url"],
            image_credit=item["image_credit"],
            timezone=item["timezone"],
            price_min=item["price_min"],
            price_max=item["price_max"],
            is_free=item["is_free"],
            city=item["city"],
            location_name=item["location_name"],
            address=item["address"],
            latitude=item["latitude"],
            longitude=item["longitude"],
            source_url=item["source_url"],
            provider=item["provider"],
        )
        movement = item["next_transfer"]
        stops.append(
            entities.EveningStop(
                event,
                item["estimated_price"],
                entities.EveningTransfer(movement["distance_km"], movement["minutes"])
                if movement
                else None,
                tuple(item["reasons"]),
            )
        )
    parts = snapshot["score_components"]
    return entities.EveningRoute(
        city=snapshot["city"],
        vibe=snapshot["vibe"],
        duration_hours=snapshot["duration_hours"],
        budget_max=snapshot["budget_max"],
        total_cost=snapshot["total_cost"],
        cost_complete=snapshot["cost_complete"],
        duration_minutes=snapshot["duration_minutes"],
        score=snapshot["score"],
        date=date.fromisoformat(snapshot["date"]),
        events=tuple(stops),
        reasons=tuple(snapshot["reasons"]),
        score_components=entities.EveningScore(
            interests_match=parts["interests_match"],
            swipe_history_match=parts["swipe_history_match"],
            category_match=parts["category_match"],
            budget_match=parts["budget_match"],
            distance_match=parts["distance_match"],
            popularity=parts["popularity"],
        ),
    )


def evening_from_model(row: models.EveningPlan) -> entities.EveningPlan:
    return entities.EveningPlan(
        id=row.id,
        user_id=row.user_id,
        route=evening_route_from_snapshot(row.snapshot),
        created_at=row.created_at,
        saved=row.saved_at is not None,
    )
