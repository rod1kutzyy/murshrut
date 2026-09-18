from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.bootstrap import Runtime
from app.config import Settings
from app.repository.models import Base
from app.service.entities import Category, Identity
from app.service.errors import ProviderUnavailable
from app.transport.api.application import create_app
from test_evenings import NOW, event
from test_repository import sessions  # SQLite and real PostgreSQL fixture.


@pytest_asyncio.fixture
async def api_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    class Clock:
        def now(self):
            return NOW

    class Provider:
        async def events(self, city):
            return [event(), event(hour=16)]

        async def categories(self):
            return [Category("kino", "Кино")]

    runtime = Runtime(
        settings=Settings(demo_mode=True, event_provider="demo"),
        sessions=async_sessionmaker(engine, expire_on_commit=False),
        database_engine=engine,
        clock=Clock(),
        provider=Provider(),
    )
    app = create_app(runtime)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        auth = (await client.post("/api/v1/auth/demo")).json()
        headers = {"Authorization": "Bearer " + auth["access_token"]}
        preferences = await client.put(
            "/api/v1/users/me/preferences",
            headers=headers,
            json={"city": "Москва", "categories": ["kino"]},
        )
        assert preferences.status_code == 200, preferences.text
        yield client, headers, runtime


@pytest.mark.asyncio
async def test_api_generation_save_restore_and_user_isolation(api_client):
    client, headers, runtime = api_client
    options = {"vibe": "calm", "duration_hours": 2, "budget_max": 1000}
    assert (
        await client.post("/api/v1/evenings/generate", json=options)
    ).status_code == 401
    assert (
        await client.post(
            "/api/v1/evenings/generate",
            headers=headers,
            json={**options, "vibe": "invalid"},
        )
    ).status_code == 422
    result = await client.post(
        "/api/v1/evenings/generate", headers=headers, json=options
    )
    assert result.status_code == 200, result.text
    plan = result.json()["plan"]
    assert not plan["saved"] and plan["event_count"] == 2 and plan["warnings"] == []
    assert (await client.get("/api/v1/evenings", headers=headers)).json() == []
    assert "external_id" not in plan["events"][0]
    assert (await client.get("/api/v1/events/favorites", headers=headers)).json() == []
    for _ in range(2):
        assert (
            await client.post(f"/api/v1/evenings/{plan['id']}/save", headers=headers)
        ).json()["saved"]
    assert len((await client.get("/api/v1/evenings", headers=headers)).json()) == 1
    restored = (
        await client.get(f"/api/v1/evenings/{plan['id']}", headers=headers)
    ).json()
    assert (
        restored["events"] == plan["events"]
        and restored["score_components"] == plan["score_components"]
    )
    assert (await client.get("/api/v1/events/favorites", headers=headers)).json() == []
    exhausted = (
        await client.post(
            "/api/v1/evenings/generate",
            headers=headers,
            json={**options, "excluded_plan_ids": [plan["id"]]},
        )
    ).json()
    assert exhausted == {"plan": None, "reason": "exhausted"}
    async with runtime.services() as services:
        other = await services.auth.uow.users.upsert_identity(
            Identity(987654), datetime.now(timezone.utc)
        )
        await services.auth.uow.commit()
        token = services.auth.tokens.issue(other.id)
    foreign = {"Authorization": "Bearer " + token}
    for method, suffix in [("GET", ""), ("POST", "/save")]:
        assert (
            await client.request(
                method, f"/api/v1/evenings/{plan['id']}{suffix}", headers=foreign
            )
        ).status_code == 404
    assert (
        await client.get(f"/api/v1/evenings/{uuid4()}", headers=headers)
    ).status_code == 404


@pytest.mark.asyncio
async def test_sync_failure_uses_cache_and_distinguishes_unavailable_source(api_client):
    client, headers, runtime = api_client
    options = {"vibe": "calm", "duration_hours": 2, "budget_max": 1000}

    async def fail(city):
        raise ProviderUnavailable("Источник недоступен")

    runtime.provider.events = fail
    runtime.sync_state.last_sync.clear()
    assert (
        await client.post("/api/v1/evenings/generate", headers=headers, json=options)
    ).json()["plan"]
    await client.put(
        "/api/v1/users/me/preferences",
        headers=headers,
        json={"city": "Казань", "categories": ["kino"]},
    )
    assert (
        await client.post("/api/v1/evenings/generate", headers=headers, json=options)
    ).status_code == 502


@pytest.mark.asyncio
async def test_repository_popularity_excludes_self_and_plans_survive_event_removal(
    sessions,
):
    from app.repository.unit_of_work import SqlAlchemyUnitOfWork
    from app.service.entities import (
        EveningPlan,
        EveningRoute,
        EveningStop,
        EveningScore,
        ReactionCounts,
    )

    async with SqlAlchemyUnitOfWork(sessions) as uow:
        user = await uow.users.upsert_identity(Identity(555), NOW)
        other = await uow.users.upsert_identity(Identity(666), NOW)
        draft = event()
        await uow.events.upsert(draft)
        row = (await uow.events.available("Москва", "demo", NOW))[0]
        assert await uow.reactions.popularity(user.id, (row.id,)) == {}
        await uow.reactions.save(user.id, row.id, "dislike")
        assert await uow.reactions.popularity(user.id, (row.id,)) == {}
        await uow.reactions.save(other.id, row.id, "like")
        assert (await uow.reactions.popularity(user.id, (row.id,)))[
            row.id
        ] == ReactionCounts(1, 1)
        await uow.reactions.save(other.id, row.id, "dislike")
        assert (await uow.reactions.popularity(user.id, (row.id,)))[
            row.id
        ] == ReactionCounts(0, 1)
        plan = EveningPlan(
            uuid4(),
            user.id,
            EveningRoute(
                "Москва",
                NOW.date(),
                "calm",
                2,
                1000,
                (EveningStop(row, 400, None, ()),),
                400,
                True,
                45,
                0.5,
                EveningScore(0.5, 0.5, 1, 0.6, 1, 0.5),
                (),
            ),
            NOW,
        )
        await uow.evenings.add(plan)
        await uow.commit()
        assert await uow.evenings.saved(user.id) == []
        await uow.evenings.save(plan.id, user.id, NOW)
        await uow.commit()
        await uow.events.deactivate_missing("Москва", "demo", ())
        await uow.commit()
    async with SqlAlchemyUnitOfWork(sessions) as uow:
        restored = await uow.evenings.get(plan.id, user.id)
        assert restored.saved and restored.route == plan.route
        assert await uow.evenings.get(plan.id, other.id) is None
        assert await uow.evenings.save(plan.id, other.id, NOW) is None
        assert len(await uow.evenings.saved(user.id)) == 1
        assert await uow.evenings.saved(other.id) == []
