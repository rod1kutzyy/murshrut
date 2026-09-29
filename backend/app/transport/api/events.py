from datetime import date as CalendarDate
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from ...service.entities import User
from ...service.facade import Services
from ..mappers import (
    catalog_to_query,
    catalog_to_response,
    event_to_response,
    reaction_to_command,
    reaction_to_response,
    recommendation_to_response,
)
from .dependencies import current_user, get_services
from .openapi import error_responses
from .schemas import CatalogOut, EventOut, ReactionInput, ReactionOut

router = APIRouter(prefix="/api/v1", tags=["events"])


@router.get(
    "/recommendations",
    response_model=list[EventOut],
    summary="Получить персональные рекомендации",
    description="Не возвращает события, на которые пользователь уже отреагировал.",
    responses=error_responses(401, 409, 422, 502),
)
async def recommendations(
    limit: int = Query(
        20, ge=1, le=100, description="Максимальное число рекомендаций."
    ),
    user: User = Depends(current_user),
    services: Services = Depends(get_services),
):
    return [
        recommendation_to_response(result)
        for result in await services.recommendations.get(user, limit)
    ]


@router.get(
    "/events/catalog",
    response_model=CatalogOut,
    summary="Найти события в каталоге",
    description="Применяет фильтры до пагинации и возвращает признак сохранения.",
    responses=error_responses(401, 409, 422, 502),
)
async def catalog(
    q: str = Query(
        "", max_length=200, description="Поиск по названию события или площадки."
    ),
    date_mode: Literal["any", "today", "weekend", "date"] = Query(
        "any", description="Предустановленный период или конкретная дата."
    ),
    date: str | None = Query(
        None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Дата YYYY-MM-DD для режима date.",
    ),
    categories: list[str] = Query(
        default=[], description="Повторяемый идентификатор категории."
    ),
    free_only: bool = Query(False, description="Показывать только бесплатные события."),
    budget_max: int | None = Query(
        None,
        ge=0,
        le=1000000,
        description="Максимальная минимальная цена; несовместимо с free_only.",
    ),
    time: Literal["any", "evening"] = Query(
        "any", description="Любое время или начало не раньше 18:00."
    ),
    limit: int = Query(20, ge=1, le=100, description="Размер страницы."),
    offset: int = Query(0, ge=0, description="Смещение от начала результата."),
    user: User = Depends(current_user),
    services: Services = Depends(get_services),
):
    try:
        selected_date = CalendarDate.fromisoformat(date) if date else None
    except ValueError:
        raise HTTPException(422, "Укажите дату в формате ГГГГ-ММ-ДД") from None
    query = catalog_to_query(
        q,
        date_mode,
        selected_date,
        categories,
        free_only,
        budget_max,
        time,
        limit,
        offset,
    )
    return catalog_to_response(await services.catalog.get(user, query))


@router.get(
    "/events/favorites",
    response_model=list[EventOut],
    summary="Получить избранные события",
    responses=error_responses(401),
)
async def favorites(
    user: User = Depends(current_user), services: Services = Depends(get_services)
):
    return [event_to_response(event) for event in await services.events.favorites(user)]


@router.get(
    "/events/{event_id}",
    response_model=EventOut,
    summary="Получить событие",
    responses=error_responses(401, 404, 422),
)
async def detail(
    event_id: UUID,
    user: User = Depends(current_user),
    services: Services = Depends(get_services),
):
    return event_to_response(await services.events.detail(event_id))


@router.post(
    "/events/{event_id}/reaction",
    response_model=ReactionOut,
    summary="Сохранить реакцию на событие",
    responses=error_responses(401, 404, 422),
)
async def react(
    event_id: UUID,
    body: ReactionInput,
    user: User = Depends(current_user),
    services: Services = Depends(get_services),
):
    return reaction_to_response(
        await services.events.react(user, reaction_to_command(event_id, body))
    )


@router.delete(
    "/events/{event_id}/reaction",
    status_code=204,
    summary="Удалить реакцию на событие",
    responses=error_responses(401, 422),
)
async def remove_reaction(
    event_id: UUID,
    user: User = Depends(current_user),
    services: Services = Depends(get_services),
):
    await services.events.remove_reaction(user, event_id)
