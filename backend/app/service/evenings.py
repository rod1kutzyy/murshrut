"""Feasible evening routes first, normalized personal scoring second."""

import asyncio
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import math
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .commands import EveningQuery
from .entities import (
    EveningPlan,
    EveningRoute,
    EveningStop,
    EveningTransfer,
    EveningScore,
    ReactionCounts,
    User,
)
from .ports import ClockPort, UnitOfWorkPort
from .sync import EventSyncService
from .errors import InvalidInput, NotFound, OnboardingRequired

WEIGHTS = {
    "interests_match": 0.30,
    "swipe_history_match": 0.25,
    "category_match": 0.15,
    "budget_match": 0.10,
    "distance_match": 0.10,
    "popularity": 0.10,
}
VIBE_CATEGORIES = {
    "active": {"koncerty", "prazdniki", "vstrechi"},
    "calm": {"vystavki", "kino"},
    "date": {"vystavki", "kino", "koncerty", "spektakli"},
    "learn": {"obuchenie", "ekskursii"},
    "culture": {"vystavki", "spektakli", "koncerty", "ekskursii"},
    "surprise": set(),
}


def utc(value):
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc)


def estimated_price(event):
    if event.is_free:
        return Decimal(0)
    prices = [
        Decimal(str(value))
        for value in (event.price_min, event.price_max)
        if value is not None and math.isfinite(value) and value >= 0
    ]
    return sum(prices) / len(prices) if prices else None


def rounded_price(value):
    return (
        int((value / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * 100)
        if value is not None
        else None
    )


def transfer(first, second):
    lat1, lon1, lat2, lon2 = map(
        math.radians,
        (first.latitude, first.longitude, second.latitude, second.longitude),
    )
    hav = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    distance = 6371 * 2 * math.asin(math.sqrt(min(1, max(0, hav)))) * 1.3
    return EveningTransfer(round(distance, 2), math.ceil(distance / 4 * 60) + 10)


def interest_score(event, preference):
    if not preference:
        return 0.5
    local = utc(event.start_date).astimezone(ZoneInfo(event.timezone))
    family = any(
        tag.casefold() in {"family", "для всей семьи", "семейный"} for tag in event.tags
    )
    company = float(preference.companion in {"family", "children"}) if family else 0.5
    days = preference.preferred_days == "any" or (
        preference.preferred_days == "weekends"
    ) == (local.weekday() >= 5)
    period = "morning" if local.hour < 12 else "day" if local.hour < 18 else "evening"
    return (
        0.8 * (event.category in preference.categories)
        + 0.1 * company
        + 0.05 * days
        + 0.05 * (preference.preferred_time in {"any", period})
    )


def popularity_score(counts: ReactionCounts) -> float:
    return (counts.likes + 2) / (counts.total + 4)


def event_signals(event, query, preference, liked, disliked, saved, popularity):
    return (
        interest_score(event, preference),
        1
        if event.id in saved
        else (liked[event.category] + 1)
        / (liked[event.category] + disliked[event.category] + 2),
        float(event.category in VIBE_CATEGORIES[query.vibe]),
        popularity_score(popularity.get(event.id, ReactionCounts(0, 0))),
    )


def cached_score(signals, categories, transitions, query, raw_total):
    size = len(signals)
    components = {
        "interests_match": sum(item[0] for item in signals) / size,
        "swipe_history_match": sum(item[1] for item in signals) / size,
        "category_match": (0.5 + 0.5 * len(set(categories)) / size)
        if query.vibe == "surprise"
        else sum(item[2] for item in signals) / size,
        "budget_match": 1 - float(raw_total / query.budget_max)
        if query.budget_max
        else 1,
        "distance_match": 1
        - sum(item.minutes for item in transitions) / len(transitions) / 30,
        "popularity": sum(item[3] for item in signals) / size,
    }
    components = {
        key: min(1.0, max(0.0, float(value))) for key, value in components.items()
    }
    return sum(components[key] * weight for key, weight in WEIGHTS.items()), components


def score_route(
    events, transitions, query, preference, liked, disliked, saved, popularity
):
    return cached_score(
        [
            event_signals(event, query, preference, liked, disliked, saved, popularity)
            for event in events
        ],
        [event.category for event in events],
        transitions,
        query,
        sum((estimated_price(event) or Decimal(0)) for event in events),
    )


def select_evening_route(
    days, city, query, preference, liked, disliked, saved, popularity, excluded
):
    """Rank every feasible route using detached inputs; safe to run outside the event loop."""
    had_route = False
    for day in sorted(days):
        events = sorted(
            days[day], key=lambda event: (utc(event.start_date), str(event.id))
        )
        prices = [estimated_price(event) or Decimal(0) for event in events]
        starts = [utc(event.start_date) for event in events]
        ends = [utc(event.end_date) for event in events]
        lengths = [
            (end - start).total_seconds() / 60 for start, end in zip(starts, ends)
        ]
        ids = [str(event.id) for event in events]
        signals = [
            event_signals(event, query, preference, liked, disliked, saved, popularity)
            for event in events
        ]
        edges = {}
        for i, first in enumerate(events):
            for j in range(i + 1, len(events)):
                second = events[j]
                if first.timezone != second.timezone:
                    continue
                movement = transfer(first, second)
                if movement.minutes <= 30 and starts[j] >= ends[i] + timedelta(
                    minutes=movement.minutes
                ):
                    edges[i, j] = movement
        best = None

        def consider(indices):
            nonlocal best, had_route
            route = [events[index] for index in indices]
            duration = (ends[indices[-1]] - starts[indices[0]]).total_seconds() / 60
            total = sum(prices[index] for index in indices)
            if duration > query.duration_hours * 60 or (
                query.budget_max is not None and total > query.budget_max
            ):
                return
            had_route = True
            if frozenset(event.id for event in route) in excluded:
                return
            movements = [edges[a, b] for a, b in zip(indices, indices[1:])]
            score, components = cached_score(
                [signals[index] for index in indices],
                [event.category for event in route],
                movements,
                query,
                total,
            )
            walking = sum(item.minutes for item in movements)
            event_minutes = sum(lengths[index] for index in indices)
            waiting = duration - event_minutes - walking
            key = (
                -score,
                walking,
                waiting,
                total,
                tuple(ids[index] for index in indices),
            )
            if best is None or key < best[0]:
                best = (key, route, movements, score, components, duration)

        successors = defaultdict(list)
        for i, j in edges:
            successors[i].append(j)
        for i, following in successors.items():
            for j in following:
                consider((i, j))
                for k in successors.get(j, ()):
                    consider((i, j, k))
        if best is None:
            continue
        _, route, movements, score, components, duration = best
        items = []
        for index, event in enumerate(route):
            reasons = []
            if interest_score(event, preference) >= 0.8:
                reasons.append("По вашим интересам")
            if event.id in saved:
                reasons.append("Из вашего избранного")
            if event.category in VIBE_CATEGORIES[query.vibe]:
                reasons.append("Под настроение вечера")
            items.append(
                EveningStop(
                    event=replace(
                        event,
                        start_date=utc(event.start_date),
                        end_date=utc(event.end_date),
                    ),
                    estimated_price=rounded_price(estimated_price(event)),
                    next_transfer=movements[index] if index < len(movements) else None,
                    reasons=tuple(reasons),
                )
            )
        selected = EveningRoute(
            city=city,
            date=day,
            vibe=query.vibe,
            duration_hours=query.duration_hours,
            budget_max=query.budget_max,
            events=tuple(items),
            total_cost=sum(item.estimated_price or 0 for item in items),
            cost_complete=all(item.estimated_price is not None for item in items),
            duration_minutes=math.ceil(duration),
            score=score,
            score_components=EveningScore(**components),
            reasons=("Площадки рядом", "Можно посетить последовательно"),
        )
        return selected, None
    return None, "exhausted" if had_route and excluded else "no_matches"


class EveningService:
    def __init__(
        self,
        uow: UnitOfWorkPort,
        sync: EventSyncService,
        clock: ClockPort,
        provider: str,
    ):
        self.uow, self.sync, self.clock, self.provider = uow, sync, clock, provider

    async def _owned(self, user: User, plan_id: UUID) -> EveningPlan:
        plan = await self.uow.evenings.get(plan_id, user.id)
        if plan is None:
            raise NotFound("План вечера не найден")
        return plan

    async def generate(
        self, user: User, query: EveningQuery
    ) -> tuple[EveningPlan | None, str | None]:
        if not user.onboarding_completed:
            raise OnboardingRequired("Сначала заполните анкету")
        if (
            query.vibe not in VIBE_CATEGORIES
            or query.duration_hours not in {2, 4, 6}
            or query.budget_max not in {None, 0, 1000, 3000}
        ):
            raise InvalidInput("Проверьте условия вечера")
        excluded = set()
        for plan_id in query.excluded_plan_ids:
            plan = await self._owned(user, plan_id)
            excluded.add(frozenset(stop.event.id for stop in plan.route.events))
        await self.sync.ensure(user.city)
        now = utc(self.clock.now())
        preference = await self.uow.preferences.get(user.id)
        history = await self.uow.reactions.history(user.id)
        liked = Counter(row.category for row in history if row.reaction == "like")
        disliked = Counter(row.category for row in history if row.reaction == "dislike")
        banned = {row.event_id for row in history if row.reaction == "dislike"}
        saved = await self.uow.reactions.saved_ids(user.id)
        rows = await self.uow.events.available(
            user.city, self.provider, now, inclusive=False
        )
        days = defaultdict(list)
        for event in rows:
            if (
                event.id in banned
                or event.city.casefold() != user.city.casefold()
                or event.provider != self.provider
            ):
                continue
            if any(
                value is None or not math.isfinite(value)
                for value in (event.latitude, event.longitude)
            ):
                continue
            if not -90 <= event.latitude <= 90 or not -180 <= event.longitude <= 180:
                continue
            try:
                zone = ZoneInfo(event.timezone)
            except (ZoneInfoNotFoundError, ValueError, TypeError):
                continue
            start, end = utc(event.start_date), utc(event.end_date)
            local = start.astimezone(zone)
            today = now.astimezone(zone).date()
            midnight = datetime.combine(
                local.date() + timedelta(days=1), datetime.min.time(), zone
            )
            if (
                not 0 <= (local.date() - today).days <= 6
                or local.hour < 18
                or end <= start
                or end > utc(midnight)
            ):
                continue
            if start < now or (
                local.date() == today and start < now + timedelta(minutes=30)
            ):
                continue
            price = estimated_price(event)
            if query.budget_max is not None and (
                price is None or price > query.budget_max
            ):
                continue
            if query.budget_max == 0 and not event.is_free:
                continue
            days[local.date()].append(event)
        popularity = await self.uow.reactions.popularity(
            user.id, tuple(event.id for events in days.values() for event in events)
        )
        selected, reason = await asyncio.to_thread(
            select_evening_route,
            days,
            user.city,
            query,
            preference,
            liked,
            disliked,
            saved,
            popularity,
            excluded,
        )
        if selected is None:
            return None, reason
        plan = EveningPlan(uuid4(), user.id, selected, now)
        await self.uow.evenings.add(plan)
        await self.uow.commit()
        return plan, None

    async def get(self, user: User, plan_id: UUID) -> EveningPlan:
        return await self._owned(user, plan_id)

    async def save(self, user: User, plan_id: UUID) -> EveningPlan:
        await self._owned(user, plan_id)
        plan = await self.uow.evenings.save(plan_id, user.id, self.clock.now())
        await self.uow.commit()
        return plan

    async def saved(self, user: User) -> list[EveningPlan]:
        return await self.uow.evenings.saved(user.id)

    async def warnings(self, plan: EveningPlan) -> list[str]:
        warnings = []
        if utc(plan.route.events[-1].event.end_date) <= utc(self.clock.now()):
            warnings.append("Этот вечер уже завершился")
        for stop in plan.route.events:
            item = stop.event
            current = await self.uow.events.get(item.id)
            if current is None or current.provider != self.provider:
                warnings.append(f"Событие «{item.title}» больше недоступно")
            elif (
                utc(current.start_date) != utc(item.start_date)
                or utc(current.end_date) != utc(item.end_date)
                or any(
                    getattr(current, key) != getattr(item, key)
                    for key in (
                        "location_name",
                        "address",
                        "latitude",
                        "longitude",
                        "price_min",
                        "price_max",
                        "is_free",
                    )
                )
            ):
                warnings.append(
                    f"У события «{item.title}» изменились условия. Проверьте карточку"
                )
        return warnings
