from datetime import date
from uuid import UUID

from ..service.commands import (
    EveningQuery,
    CatalogQuery,
    ReactCommand,
    SavePreferencesCommand,
)
from ..service.entities import (
    EveningPlan,
    Category,
    Event,
    Preferences,
    ServiceConfig,
    User,
)
from ..service.results import (
    AuthenticationResult,
    CatalogEvent,
    CatalogResult,
    HealthResult,
    PreferencesResult,
    ReactionResult,
    RecommendedEvent,
    SyncResult,
)
from .api.schemas import (
    EveningInput,
    EveningOut,
    EveningEventOut,
    TransferOut,
    AuthOut,
    CatalogEventOut,
    CatalogOut,
    CategoryOut,
    ConfigOut,
    EventOut,
    HealthOut,
    PreferencesInput,
    PreferencesOut,
    ReactionInput,
    ReactionOut,
    SyncOut,
    UserOut,
)


def preferences_to_command(body: PreferencesInput) -> SavePreferencesCommand:
    return SavePreferencesCommand(
        city=body.city,
        preferences=Preferences(
            categories=tuple(body.categories),
            budget_max=body.budget_max,
            companion=body.companion,
            preferred_days=body.preferred_days,
            preferred_time=body.preferred_time,
        ),
    )


def reaction_to_command(event_id: UUID, body: ReactionInput) -> ReactCommand:
    return ReactCommand(event_id=event_id, reaction=body.reaction)


def catalog_to_query(
    q: str,
    date_mode: str,
    selected_date: date | None,
    categories: list[str],
    free_only: bool,
    budget_max: int | None,
    time: str,
    limit: int,
    offset: int,
) -> CatalogQuery:
    return CatalogQuery(
        q=q,
        date_mode=date_mode,
        selected_date=selected_date,
        categories=tuple(categories),
        free_only=free_only,
        budget_max=budget_max,
        evening=time == "evening",
        limit=limit,
        offset=offset,
    )


def user_to_response(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        first_name=user.first_name,
        city=user.city,
        onboarding_completed=user.onboarding_completed,
    )


def auth_to_response(result: AuthenticationResult) -> AuthOut:
    return AuthOut(
        access_token=result.access_token,
        token_type="bearer",
        user=user_to_response(result.user),
    )


def category_to_response(category: Category) -> CategoryOut:
    return CategoryOut(id=category.id, name=category.name)


def preferences_to_response(result: PreferencesResult) -> PreferencesOut:
    preference = result.preferences
    return PreferencesOut(
        city=result.city,
        categories=list(preference.categories),
        budget_max=preference.budget_max,
        companion=preference.companion,
        preferred_days=preference.preferred_days,
        preferred_time=preference.preferred_time,
    )


def event_response_values(event: Event, reasons: tuple[str, ...] = ()) -> dict:
    return {
        "id": event.id,
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
        "reasons": list(reasons),
    }


def event_to_response(event: Event) -> EventOut:
    return EventOut(**event_response_values(event))


def recommendation_to_response(result: RecommendedEvent) -> EventOut:
    return EventOut(**event_response_values(result.event, result.reasons))


def catalog_event_to_response(item: CatalogEvent) -> CatalogEventOut:
    return CatalogEventOut(**event_response_values(item.event), is_saved=item.is_saved)


def catalog_to_response(result: CatalogResult) -> CatalogOut:
    return CatalogOut(
        items=[catalog_event_to_response(item) for item in result.items],
        total=result.total,
        has_more=result.has_more,
    )


def configuration_to_response(config: ServiceConfig) -> ConfigOut:
    return ConfigOut(
        demo_mode=config.demo_mode,
        event_provider=config.event_provider,
        max_bot_name=config.max_bot_name,
        demo_cities=list(config.demo_cities),
    )


def health_to_response(result: HealthResult) -> HealthOut:
    return HealthOut(status=result.status)


def reaction_to_response(result: ReactionResult) -> ReactionOut:
    return ReactionOut(reaction=result.reaction)


def sync_to_response(result: SyncResult) -> SyncOut:
    return SyncOut(synced=result.synced)


def evening_to_query(body: EveningInput) -> EveningQuery:
    return EveningQuery(
        vibe=body.vibe,
        duration_hours=body.duration_hours,
        budget_max=body.budget_max,
        excluded_plan_ids=tuple(body.excluded_plan_ids),
    )


def evening_to_response(plan: EveningPlan, warnings: list[str]) -> EveningOut:
    route = plan.route
    events = []
    for stop in route.events:
        movement = stop.next_transfer
        events.append(
            EveningEventOut(
                **event_response_values(stop.event, stop.reasons),
                estimated_price=stop.estimated_price,
                next_transfer=TransferOut(
                    distance_km=movement.distance_km, minutes=movement.minutes
                )
                if movement
                else None,
            )
        )
    return EveningOut(
        id=plan.id,
        saved=plan.saved,
        created_at=plan.created_at,
        date=route.date.isoformat(),
        events=events,
        event_count=route.event_count,
        city=route.city,
        vibe=route.vibe,
        duration_hours=route.duration_hours,
        budget_max=route.budget_max,
        total_cost=route.total_cost,
        cost_complete=route.cost_complete,
        duration_minutes=route.duration_minutes,
        score=route.score,
        reasons=list(route.reasons),
        warnings=list(warnings),
        score_components={
            "interests_match": route.score_components.interests_match,
            "swipe_history_match": route.score_components.swipe_history_match,
            "category_match": route.score_components.category_match,
            "budget_match": route.score_components.budget_match,
            "distance_match": route.score_components.distance_match,
            "popularity": route.score_components.popularity,
        },
    )
