from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.service.commands import EveningQuery
from app.service.entities import Preferences, Reaction
from app.service.errors import InvalidInput, NotFound, OnboardingRequired
from app.service.entities import ReactionCounts
from app.service.evenings import (
    EveningService,
    WEIGHTS,
    estimated_price,
    interest_score,
    rounded_price,
    score_route,
    transfer,
)
from factories import make_event
from test_services import FakeUow, USER

NOW = datetime(2030, 1, 4, 12, tzinfo=timezone.utc)
OPTIONS = EveningQuery("calm", 2, 1000)


def event(hour=15, minute=0, duration=45, day=4, **kwargs):
    start = datetime(2030, 1, day, hour, minute, tzinfo=timezone.utc)
    return make_event(
        start_date=start,
        end_date=start + timedelta(minutes=duration),
        latitude=55.75,
        longitude=37.61,
        tags=(),
        price_min=400,
        price_max=400,
        **kwargs,
    )


class MemoryUow(FakeUow):
    def __init__(self, events=(), history=(), preferences=None, popularity=None):
        super().__init__(events, history, preferences)
        self.plans = {}
        self.popularity_scores = popularity or {}
        self.events.get = self.get_event
        self.reactions.popularity = self.popularity
        self.evenings = SimpleNamespace(
            add=self.add_plan,
            get=self.get_plan,
            save=self.save_plan,
            saved=self.saved_plans,
        )

    async def get_event(self, event_id):
        return next((row for row in self.rows if row.id == event_id), None)

    async def popularity(self, *args):
        return self.popularity_scores

    async def add_plan(self, plan):
        self.plans[plan.id] = plan

    async def get_plan(self, plan_id, user_id):
        plan = self.plans.get(plan_id)
        return plan if plan and plan.user_id == user_id else None

    async def save_plan(self, plan_id, user_id, now):
        plan = await self.get_plan(plan_id, user_id)
        if plan:
            plan = replace(plan, saved=True)
            self.plans[plan.id] = plan
        return plan

    async def saved_plans(self, user_id):
        return [
            plan
            for plan in self.plans.values()
            if plan.saved and plan.user_id == user_id
        ]


def service(uow, now=NOW):
    async def ensure(city):
        pass

    return EveningService(
        uow, SimpleNamespace(ensure=ensure), SimpleNamespace(now=lambda: now), "demo"
    )


@pytest.mark.parametrize(
    ("minimum", "maximum", "free", "raw", "rounded"),
    [
        (400, 700, False, "550", 600),
        (450, None, False, "450", 500),
        (None, 350, False, "350", 400),
        (None, None, False, None, None),
        (800, 900, True, "0", 0),
        (0, 0, False, "0", 0),
    ],
)
def test_price_uses_average_and_half_up_rounding(minimum, maximum, free, raw, rounded):
    row = replace(event(), price_min=minimum, price_max=maximum, is_free=free)
    value = estimated_price(row)
    assert value == (Decimal(raw) if raw is not None else None)
    assert rounded_price(value) == rounded


def test_scoring_formula_normalization_and_neutral_signals():
    first, second = event(), event(hour=16)
    from collections import Counter

    score, parts = score_route(
        [first, second],
        [transfer(first, second)],
        OPTIONS,
        None,
        Counter(),
        Counter(),
        set(),
        {},
    )
    assert sum(WEIGHTS.values()) == pytest.approx(1)
    assert (
        parts["interests_match"]
        == parts["swipe_history_match"]
        == parts["popularity"]
        == 0.5
    )
    assert parts["category_match"] == 1
    assert parts["budget_match"] == pytest.approx(0.2)
    assert parts["distance_match"] == pytest.approx(2 / 3)
    assert score == pytest.approx(
        sum(parts[key] * weight for key, weight in WEIGHTS.items())
    )
    assert all(0 <= value <= 1 for value in parts.values())


def test_personal_signals_favorites_and_surprise_diversity():
    from collections import Counter

    movie, art = event(), event(hour=16, category="vystavki")
    prefs = Preferences(("kino",), 0, "friends", "any", "evening")
    assert interest_score(movie, prefs) == pytest.approx(0.95)
    assert interest_score(art, prefs) == pytest.approx(0.15)
    _, parts = score_route(
        [movie, art],
        [transfer(movie, art)],
        replace(OPTIONS, vibe="surprise"),
        prefs,
        Counter(kino=3),
        Counter(kino=1),
        {art.id},
        {movie.id: ReactionCounts(34, 36)},
    )
    assert parts["swipe_history_match"] == pytest.approx((4 / 6 + 1) / 2)
    assert parts["category_match"] == 1
    assert parts["popularity"] == pytest.approx(0.7)
    _, repeated = score_route(
        [movie, event(hour=16)],
        [transfer(movie, art)],
        replace(OPTIONS, vibe="surprise"),
        None,
        Counter(),
        Counter(),
        set(),
        {},
    )
    assert repeated["category_match"] == 0.75


def test_questionnaire_company_days_and_time_are_soft_signals():
    row = replace(event(), tags=("family",))
    matching = Preferences(("kino",), None, "family", "weekdays", "evening")
    assert interest_score(row, matching) == pytest.approx(1)
    opposite = replace(
        matching, companion="solo", preferred_days="weekends", preferred_time="morning"
    )
    assert interest_score(row, opposite) == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_route_is_ordered_feasible_saves_without_event_reactions_and_excludes_variants():
    first, second = event(), event(hour=16)
    uow = MemoryUow([second, first])
    engine = service(uow)
    plan, reason = await engine.generate(USER, OPTIONS)
    assert reason is None and plan.route.event_count == 2
    assert [item.event.id for item in plan.route.events] == [
        first.id,
        second.id,
    ]
    assert plan.route.duration_minutes == 105
    assert plan.route.total_cost == 800
    assert plan.route.events[0].next_transfer.minutes == 10
    assert plan.route.events[1].next_transfer is None
    assert not plan.saved and await engine.saved(USER) == []
    saved = await engine.save(USER, plan.id)
    assert saved.saved and (await engine.save(USER, plan.id)).id == plan.id
    assert len(await engine.saved(USER)) == 1 and uow.history_rows == []
    assert await engine.warnings(saved) == []
    result, reason = await engine.generate(
        USER, replace(OPTIONS, excluded_plan_ids=(plan.id,))
    )
    assert result is None and reason == "exhausted"
    other = replace(USER, id=uuid4())
    with pytest.raises(NotFound):
        await engine.get(other, plan.id)
    with pytest.raises(NotFound):
        await engine.save(other, plan.id)
    with pytest.raises(NotFound):
        await engine.generate(other, replace(OPTIONS, excluded_plan_ids=(plan.id,)))


@pytest.mark.asyncio
async def test_short_route_and_three_event_route():
    rows = [
        event(duration=25),
        event(minute=40, duration=25),
        event(hour=16, minute=20, duration=25),
    ]
    uow = MemoryUow(rows)
    engine = service(uow)
    # Pairs and triples are alternatives, not a preference for a larger event count.
    shown = []
    sizes = set()
    for _ in range(4):
        plan, _ = await engine.generate(
            USER, EveningQuery("surprise", 2, 3000, tuple(shown))
        )
        assert plan is not None and plan.route.duration_minutes <= 120
        sizes.add(plan.route.event_count)
        shown.append(plan.id)
    assert sizes == {2, 3}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid",
    [
        {"hour": 14},
        {"hour": 15, "minute": 30},
        {"hour": 17, "duration": 61},
        {"hour": 16, "duration": 121},
        {"hour": 16, "duration": 0},
        {"hour": 16, "duration": -1},
        {"hour": 16, "day": 11},
        {"hour": 16, "latitude": None},
        {"hour": 16, "latitude": 90.1},
        {"hour": 16, "latitude": float("nan")},
        {"hour": 16, "latitude": 56.75},
        {"hour": 16, "timezone": "Invalid/Zone"},
        {"hour": 16, "city": "Казань"},
        {"hour": 16, "provider": "culture"},
    ],
)
async def test_high_scores_never_override_feasibility(invalid):
    first = event()
    values = dict(invalid)
    # Dataclass overrides allow explicit missing coordinates and altered durations.
    extra = {
        key: values.pop(key)
        for key in list(values)
        if key not in {"hour", "minute", "duration", "day"}
    }
    second = replace(event(**values), **extra)
    uow = MemoryUow(
        [first, second],
        preferences=Preferences(("kino",), None, "friends", "any", "evening"),
        popularity={second.id: ReactionCounts(10000, 10000)},
    )
    result, reason = await service(uow).generate(USER, OPTIONS)
    assert result is None and reason == "no_matches"


@pytest.mark.asyncio
async def test_budget_before_rounding_and_free_requires_explicit_flag():
    rows = [
        replace(event(), price_min=501, price_max=501),
        replace(event(hour=16), price_min=501, price_max=501),
    ]
    assert (await service(MemoryUow(rows)).generate(USER, OPTIONS))[0] is None
    zeros = [replace(row, price_min=0, price_max=0) for row in rows]
    assert (
        await service(MemoryUow(zeros)).generate(USER, replace(OPTIONS, budget_max=0))
    )[0] is None
    free = [replace(row, is_free=True) for row in zeros]
    plan, _ = await service(MemoryUow(free)).generate(
        USER, replace(OPTIONS, budget_max=0)
    )
    assert plan.route.total_cost == 0


@pytest.mark.asyncio
async def test_unknown_price_unlimited_and_dislike_exclusion():
    first, second = event(), replace(event(hour=16), price_min=None, price_max=None)
    uow = MemoryUow([first, second])
    engine = service(uow)
    assert (await engine.generate(USER, OPTIONS))[0] is None
    plan, _ = await engine.generate(USER, replace(OPTIONS, budget_max=None))
    assert not plan.route.cost_complete and plan.route.total_cost == 400
    uow.history_rows = [Reaction(first.id, "kino", "dislike")]
    assert (await engine.generate(USER, replace(OPTIONS, budget_max=None)))[0] is None
    uow.history_rows = [Reaction(first.id, "kino", "like")]
    assert (await engine.generate(USER, replace(OPTIONS, budget_max=None)))[
        0
    ] is not None


@pytest.mark.asyncio
async def test_date_today_lead_time_and_inclusive_seventh_day():
    first, second = event(), event(hour=16)
    engine = service(
        MemoryUow([first, second]), datetime(2030, 1, 4, 14, 31, tzinfo=timezone.utc)
    )
    assert (await engine.generate(USER, OPTIONS))[0] is None
    engine = service(
        MemoryUow([first, second]), datetime(2030, 1, 4, 14, 30, tzinfo=timezone.utc)
    )
    assert (await engine.generate(USER, OPTIONS))[0] is not None
    seventh = [event(day=10), event(day=10, hour=16)]
    plan, _ = await service(MemoryUow(seventh)).generate(USER, OPTIONS)
    assert plan.route.date.isoformat() == "2030-01-10"
    earlier = [event(day=5), event(day=5, hour=16)]
    plan, _ = await service(MemoryUow(seventh + earlier)).generate(USER, OPTIONS)
    assert plan.route.date.isoformat() == "2030-01-05"


@pytest.mark.asyncio
async def test_midnight_end_allowed_but_crossing_midnight_excluded():
    first, second = event(hour=19), event(hour=20, minute=15)
    plan, _ = await service(MemoryUow([first, second])).generate(USER, OPTIONS)
    assert plan and plan.route.events[-1].event.end_date == datetime.fromisoformat(
        "2030-01-04T21:00:00+00:00"
    )
    assert (
        await service(
            MemoryUow(
                [
                    first,
                    replace(second, end_date=second.end_date + timedelta(minutes=1)),
                ]
            )
        ).generate(USER, OPTIONS)
    )[0] is None


@pytest.mark.asyncio
async def test_other_timezone_uses_city_local_evening():
    rows = [
        replace(event(hour=13), timezone="Asia/Yekaterinburg"),
        replace(event(hour=14), timezone="Asia/Yekaterinburg"),
    ]
    plan, _ = await service(MemoryUow(rows)).generate(USER, OPTIONS)
    assert plan and plan.route.date.isoformat() == "2030-01-04"


@pytest.mark.asyncio
async def test_distance_improves_ranking_with_equal_signals():
    first, close, far = event(), event(hour=16), replace(event(hour=16), latitude=55.76)
    plan, _ = await service(MemoryUow([first, far, close])).generate(USER, OPTIONS)
    assert [item.event.id for item in plan.route.events] == [
        first.id,
        close.id,
    ]


@pytest.mark.asyncio
async def test_warnings_keep_snapshot_after_change_cancellation_and_expiry():
    first, second = event(), event(hour=16)
    uow = MemoryUow([first, second])
    engine = service(uow)
    plan, _ = await engine.generate(USER, OPTIONS)
    uow.rows[0] = replace(first, start_date=first.start_date + timedelta(minutes=5))
    uow.rows.pop()
    warnings = await engine.warnings(plan)
    assert (
        len(warnings) == 2
        and "изменились" in warnings[0]
        and "недоступно" in warnings[1]
    )
    assert (await engine.get(USER, plan.id)).route.events[
        0
    ].event.start_date == first.start_date
    assert (
        "завершился" in (await service(uow, NOW + timedelta(days=1)).warnings(plan))[0]
    )


@pytest.mark.asyncio
async def test_onboarding_and_input_validation():
    engine = service(MemoryUow())
    with pytest.raises(OnboardingRequired):
        await engine.generate(replace(USER, onboarding_completed=False), OPTIONS)
    with pytest.raises(InvalidInput):
        await engine.generate(USER, replace(OPTIONS, vibe="missing"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("hours", "end_hour", "end_minute", "valid"),
    [
        (2, 17, 0, True),
        (2, 17, 1, False),
        (4, 19, 0, True),
        (4, 19, 1, False),
        (6, 21, 0, True),
    ],
)
async def test_duration_caps_include_waiting(hours, end_hour, end_minute, valid):
    first = event(duration=20)
    second = replace(
        event(hour=end_hour - 1),
        end_date=datetime(2030, 1, 4, end_hour, end_minute, tzinfo=timezone.utc),
    )
    plan, _ = await service(MemoryUow([first, second])).generate(
        USER, replace(OPTIONS, duration_hours=hours)
    )
    assert bool(plan) is valid


@pytest.mark.asyncio
async def test_exact_transition_boundary_requires_the_full_buffer():
    first = event(duration=30)
    boundary = event(minute=40, duration=30)
    assert (await service(MemoryUow([first, boundary])).generate(USER, OPTIONS))[0]
    early = replace(boundary, start_date=boundary.start_date - timedelta(seconds=1))
    assert (await service(MemoryUow([first, early])).generate(USER, OPTIONS))[0] is None


@pytest.mark.asyncio
async def test_legacy_snapshot_roundtrip_and_http_collections_are_detached():
    from dataclasses import asdict
    import json

    from app.repository.mappers import evening_route_from_snapshot, evening_to_snapshot
    from app.transport.mappers import evening_to_response

    plan, _ = await service(MemoryUow([event(), event(hour=16)])).generate(
        USER, OPTIONS
    )
    stored = evening_to_snapshot(plan.route)
    # Reproduce the JSON layout written by the first feature version.
    legacy = dict(stored)
    legacy["events"] = [
        dict(
            asdict(stop.event),
            estimated_price=stop.estimated_price,
            next_transfer=asdict(stop.next_transfer) if stop.next_transfer else None,
            reasons=list(stop.reasons),
        )
        for stop in plan.route.events
    ]
    legacy = json.loads(
        json.dumps(
            legacy,
            default=lambda value: value.isoformat()
            if isinstance(value, datetime)
            else str(value),
        )
    )
    assert legacy == stored
    restored = evening_route_from_snapshot(legacy)
    assert restored == plan.route
    legacy["events"][0]["tags"].append("modified")
    legacy["events"][0]["reasons"].append("modified")
    assert restored == plan.route
    response = evening_to_response(plan, [])
    response.events[0].tags.append("modified")
    response.reasons.append("modified")
    assert evening_to_snapshot(plan.route) == stored


def test_popularity_smoothing_is_a_service_rule():
    from app.service.evenings import popularity_score

    assert popularity_score(ReactionCounts(0, 0)) == 0.5
    assert popularity_score(ReactionCounts(1, 1)) == 0.6
    assert popularity_score(ReactionCounts(0, 1)) == 0.4
