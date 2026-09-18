from datetime import date as CalendarDate
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from ...service.entities import User
from ...service.facade import Services
from ..mappers import (catalog_to_query, catalog_to_response, event_to_response,
                       reaction_to_command, reaction_to_response, recommendation_to_response)
from .dependencies import current_user, get_services
from .schemas import CatalogOut, EventOut, ReactionInput, ReactionOut

router = APIRouter(prefix='/api/v1')


@router.get('/recommendations', response_model=list[EventOut])
async def recommendations(limit: int = Query(20, ge=1, le=100), user: User = Depends(current_user),
                          services: Services = Depends(get_services)):
    return [recommendation_to_response(result) for result in await services.recommendations.get(user, limit)]


@router.get('/events/catalog', response_model=CatalogOut)
async def catalog(
    q: str = Query('', max_length=200),
    date_mode: Literal['any', 'today', 'weekend', 'date'] = 'any',
    date: str | None = Query(None, pattern=r'^\d{4}-\d{2}-\d{2}$'),
    categories: list[str] = Query(default=[]), free_only: bool = False,
    budget_max: int | None = Query(None, ge=0, le=1000000),
    time: Literal['any', 'evening'] = 'any', limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0), user: User = Depends(current_user),
    services: Services = Depends(get_services),
):
    try:
        selected_date = CalendarDate.fromisoformat(date) if date else None
    except ValueError:
        raise HTTPException(422, 'Укажите дату в формате ГГГГ-ММ-ДД') from None
    query = catalog_to_query(q, date_mode, selected_date, categories, free_only, budget_max, time, limit, offset)
    return catalog_to_response(await services.catalog.get(user, query))


@router.get('/events/favorites', response_model=list[EventOut])
async def favorites(user: User = Depends(current_user), services: Services = Depends(get_services)):
    return [event_to_response(event) for event in await services.events.favorites(user)]


@router.get('/events/{event_id}', response_model=EventOut)
async def detail(event_id: UUID, user: User = Depends(current_user), services: Services = Depends(get_services)):
    return event_to_response(await services.events.detail(event_id))


@router.post('/events/{event_id}/reaction', response_model=ReactionOut)
async def react(event_id: UUID, body: ReactionInput, user: User = Depends(current_user),
                services: Services = Depends(get_services)):
    return reaction_to_response(await services.events.react(user, reaction_to_command(event_id, body)))


@router.delete('/events/{event_id}/reaction', status_code=204)
async def remove_reaction(event_id: UUID, user: User = Depends(current_user), services: Services = Depends(get_services)):
    await services.events.remove_reaction(user, event_id)
