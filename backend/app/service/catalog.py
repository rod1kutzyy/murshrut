from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .commands import CatalogQuery
from .entities import User
from .errors import InvalidInput, OnboardingRequired
from .ports import ClockPort, UnitOfWorkPort
from .results import CatalogEvent, CatalogResult
from .sync import EventSyncService


def aware(value):
    # SQLite returns naive datetimes for UTC values stored by the provider.
    return value.replace(tzinfo=value.tzinfo or timezone.utc)


def matches(event, *, now, q='', date_mode='any', selected_date=None,
            categories=(), free_only=False, budget_max=None, evening=False):
    if q and q.casefold() not in event.title.casefold() and q.casefold() not in event.location_name.casefold():
        return False
    if categories and event.category not in categories:
        return False
    if free_only and not event.is_free:
        return False
    if budget_max is not None and not event.is_free and (event.price_min is None or event.price_min > budget_max):
        return False
    zone = ZoneInfo(event.timezone)
    start, end = aware(event.start_date), aware(event.end_date)
    if evening and start.astimezone(zone).hour < 18:
        return False
    if date_mode != 'any':
        today = now.astimezone(zone).date()
        first = selected_date if date_mode == 'date' else today
        days = 1
        if date_mode == 'weekend':
            if today.weekday() < 5:
                first = today + timedelta(days=5 - today.weekday())
                days = 2
            else:
                days = 7 - today.weekday()
        lower = datetime.combine(first, time.min, zone)
        upper = datetime.combine(first + timedelta(days=days), time.min, zone)
        # Day windows are half-open; an event ending at midnight belongs to the previous day.
        if not (start < upper and end > lower):
            return False
    return True


class CatalogService:
    def __init__(self, uow: UnitOfWorkPort, sync: EventSyncService, clock: ClockPort, provider: str):
        self.uow, self.sync, self.clock, self.provider = uow, sync, clock, provider

    async def get(self, user: User, query: CatalogQuery) -> CatalogResult:
        if not user.onboarding_completed:
            raise OnboardingRequired('Сначала заполните анкету')
        if query.date_mode == 'date' and query.selected_date is None:
            raise InvalidInput('Выберите конкретную дату')
        if query.free_only and query.budget_max is not None:
            raise InvalidInput('Выберите бесплатно или ограничение бюджета')
        await self.sync.ensure(user.city)
        events = await self.uow.events.available(user.city, self.provider, self.clock.now(), inclusive=False)
        now = self.clock.now()
        filtered = [event for event in events if matches(
            event, now=now, q=query.q.strip(), date_mode=query.date_mode,
            selected_date=query.selected_date, categories=query.categories,
            free_only=query.free_only, budget_max=query.budget_max, evening=query.evening,
        )]
        saved = await self.uow.reactions.saved_ids(user.id)
        return CatalogResult(
            items=tuple(CatalogEvent(event=event, is_saved=event.id in saved)
                        for event in filtered[query.offset:query.offset + query.limit]),
            total=len(filtered), has_more=query.offset + query.limit < len(filtered),
        )
