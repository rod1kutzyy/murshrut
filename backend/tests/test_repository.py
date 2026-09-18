import os
from dataclasses import is_dataclass, replace
from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.bootstrap import SystemClock, settings_to_service_config
from app.config import Settings
from app.repository.mappers import event_from_model, event_to_values, preferences_from_model
from app.repository.models import Base, Event as EventModel, UserPreference
from app.repository.unit_of_work import SqlAlchemyUnitOfWork
from app.service.commands import SavePreferencesCommand
from app.service.entities import Identity, Preferences
from app.service.use_cases import PreferencesService
from app.transport.integrations.providers import DemoProvider
from factories import make_event


@pytest_asyncio.fixture(params=['sqlite', 'postgresql'])
async def sessions(request):
    schema = None
    if request.param == 'postgresql':
        url = os.environ.get('TEST_REPOSITORY_DATABASE_URL')
        if not url:
            pytest.skip('Set TEST_REPOSITORY_DATABASE_URL to test PostgreSQL')
        schema = 'architecture_test_' + uuid4().hex
        engine = create_async_engine(url, connect_args={'server_settings': {'search_path': schema}})
    else:
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as connection:
        if schema:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        if schema:
            async with engine.begin() as connection:
                await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await engine.dispose()


@pytest.mark.asyncio
async def test_upserts_and_detached_entities(sessions):
    identity = Identity(max_user_id=123456, first_name='Первое имя')
    event = make_event()
    preference = Preferences(('kino',), 1000, 'friends', 'any', 'evening')
    async with SqlAlchemyUnitOfWork(sessions) as uow:
        user = await uow.users.upsert_identity(identity, datetime.now(timezone.utc))
        await uow.preferences.save(user.id, preference, datetime.now(timezone.utc))
        await uow.events.upsert(event)
        stored = (await uow.events.available('Москва', 'demo', datetime.now(timezone.utc)))[0]
        await uow.reactions.save(user.id, stored.id, 'like')
        await uow.commit()
        updated = await uow.users.upsert_identity(replace(identity, first_name='Второе имя'), datetime.now(timezone.utc))
        await uow.events.upsert(replace(event, title='Новое название'))
        await uow.reactions.save(user.id, stored.id, 'dislike')
        await uow.commit()
        detached_user = await uow.users.get(user.id)
        detached_event = await uow.events.get(stored.id)
        detached_preference = await uow.preferences.get(user.id)
        history = await uow.reactions.history(user.id)
    assert user.id == updated.id == detached_user.id
    assert detached_user.first_name == 'Второе имя'
    assert user.first_name == 'Первое имя'  # Previous result is a detached snapshot.
    assert detached_event.title == 'Новое название'
    assert detached_event.external_id == event.external_id
    assert detached_event.tags == ('family',)
    assert detached_event.image_url is None and detached_event.latitude is None
    assert detached_event.start_date.replace(tzinfo=timezone.utc) == event.start_date
    assert detached_preference == preference
    assert all(is_dataclass(value) for value in (detached_user, detached_event, detached_preference, *history))
    assert history[0].reaction == 'dislike'


@pytest.mark.asyncio
async def test_preferences_and_city_are_atomic(sessions):
    async with SqlAlchemyUnitOfWork(sessions) as uow:
        user = await uow.users.upsert_identity(Identity(123), datetime.now(timezone.utc))
        await uow.commit()
    config = settings_to_service_config(Settings(demo_mode=True, event_provider='demo'))
    preference = Preferences(('kino',), 500, 'friends', 'any', 'any')
    with pytest.raises(RuntimeError, match='Second operation failed'):
        async with SqlAlchemyUnitOfWork(sessions) as uow:
            original = uow.users.complete_onboarding
            async def fail_after_city_change(user_id, city):
                await original(user_id, city)
                raise RuntimeError('Second operation failed')
            uow.users.complete_onboarding = fail_after_city_change
            await PreferencesService(uow, DemoProvider(), SystemClock(), config).save(
                user, SavePreferencesCommand('Казань', preference))
    async with SqlAlchemyUnitOfWork(sessions) as uow:
        unchanged = await uow.users.get(user.id)
        assert unchanged.city == 'Москва' and not unchanged.onboarding_completed
        assert await uow.preferences.get(user.id) is None
        updated = await PreferencesService(uow, DemoProvider(), SystemClock(), config).save(
            unchanged, SavePreferencesCommand('Казань', preference))
    assert updated.city == 'Казань' and updated.onboarding_completed
    async with SqlAlchemyUnitOfWork(sessions) as uow:
        assert (await uow.users.get(user.id)).city == 'Казань'
        assert await uow.preferences.get(user.id) == preference


@pytest.mark.asyncio
async def test_uncommitted_changes_are_rolled_back(sessions):
    async with SqlAlchemyUnitOfWork(sessions) as uow:
        user = await uow.users.upsert_identity(Identity(321), datetime.now(timezone.utc))
    async with SqlAlchemyUnitOfWork(sessions) as uow:
        assert await uow.users.get(user.id) is None
        await uow.ping()


@pytest.mark.asyncio
async def test_reactions_favorites_and_provider_isolation(sessions):
    async with SqlAlchemyUnitOfWork(sessions) as uow:
        user = await uow.users.upsert_identity(Identity(456), datetime.now(timezone.utc))
        for provider in ('demo', 'culture'):
            await uow.events.upsert(make_event(provider=provider))
        demo = (await uow.events.available('Москва', 'demo', datetime.now(timezone.utc)))[0]
        culture = (await uow.events.available('Москва', 'culture', datetime.now(timezone.utc)))[0]
        for row in (demo, culture):
            await uow.reactions.save(user.id, row.id, 'like')
        await uow.commit()
        assert await uow.events.favorites(user.id, 'demo') == [demo]
        assert await uow.events.favorites(uuid4(), 'demo') == []
        assert await uow.reactions.saved_ids(user.id) == {demo.id, culture.id}
        assert await uow.reactions.remove(user.id, demo.id)
        assert not await uow.reactions.remove(user.id, demo.id)
        await uow.commit()
        assert await uow.events.favorites(user.id, 'demo') == []
        assert await uow.events.available('Казань', 'demo', datetime.now(timezone.utc)) == []


def test_mapper_copies_collections_and_explicitly_maps_fields():
    event = make_event()
    values = event_to_values(event)
    values['id'] = event.id
    row = EventModel(**values)
    result = event_from_model(row)
    row.tags.append('changed')
    assert result.tags == event.tags
    assert result.id == event.id and result.price_max == event.price_max
    tags = event_to_values(result)['tags']
    tags.append('another change')
    assert result.tags == ('family',)
    preference = preferences_from_model(UserPreference(categories=['kino'], budget_max=None,
                                    companion='solo', preferred_days='any', preferred_time='any'))
    assert preference.categories == ('kino',) and preference.budget_max is None

@pytest.mark.asyncio
async def test_successful_snapshot_removes_missing_events_and_restores_reappearing(sessions):
    from app.service.catalog import CatalogService
    from app.service.commands import CatalogQuery
    from app.service.errors import ProviderUnavailable
    from app.service.sync import EventSyncService, SyncState

    now = datetime(2030, 1, 4, tzinfo=timezone.utc)
    class Clock:
        def now(self):
            return now
    class Provider:
        rows = []
        failing = False
        async def events(self, city):
            if self.failing:
                raise ProviderUnavailable('Источник недоступен')
            return self.rows
    provider = Provider()
    config = settings_to_service_config(Settings(demo_mode=True, event_provider='culture'))
    state = SyncState()
    event = make_event(provider='culture')
    other_city = make_event(provider='culture', city='Казань')
    other_source = make_event(provider='demo')
    async with SqlAlchemyUnitOfWork(sessions) as uow:
        user = await uow.users.upsert_identity(Identity(987), now)
        user = await uow.users.complete_onboarding(user.id, 'Москва')
        for row in (event, other_city, other_source):
            await uow.events.upsert(row)
        stored = (await uow.events.available('Москва', 'culture', now))[0]
        await uow.reactions.save(user.id, stored.id, 'like')
        await uow.commit()
    async with SqlAlchemyUnitOfWork(sessions) as uow:
        sync = EventSyncService(uow, provider, Clock(), config, state)
        provider.failing = True
        await sync.ensure('Москва')
        assert (await CatalogService(uow, sync, Clock(), 'culture').get(user, CatalogQuery())).total == 1
        provider.failing = False
        await sync.sync('Москва', force=True)  # Successful empty snapshot.
        assert (await CatalogService(uow, sync, Clock(), 'culture').get(user, CatalogQuery())).total == 0
        assert not await uow.events.has_available('Москва', 'culture', now)
        assert await uow.events.get(stored.id) is None
        assert await uow.events.favorites(user.id, 'culture') == []
        assert len(await uow.events.available('Казань', 'culture', now)) == 1
        assert len(await uow.events.available('Москва', 'demo', now)) == 1
        assert stored.id in await uow.reactions.saved_ids(user.id)
        provider.rows = [event]
        await sync.sync('Москва', force=True)
        result = await CatalogService(uow, sync, Clock(), 'culture').get(user, CatalogQuery())
        assert result.total == 1 and result.items[0].is_saved
        assert result.items[0].event.id == stored.id
        assert len(await uow.events.favorites(user.id, 'culture')) == 1
    with pytest.raises(RuntimeError):
        async with SqlAlchemyUnitOfWork(sessions) as uow:
            await uow.events.deactivate_missing('Москва', 'culture', ())
            raise RuntimeError('Transaction failed')
    async with SqlAlchemyUnitOfWork(sessions) as uow:
        assert await uow.events.get(stored.id) is not None


@pytest.mark.asyncio
async def test_partial_snapshot_only_deactivates_missing_ids(sessions):
    missing, retained = make_event(), make_event()
    async with SqlAlchemyUnitOfWork(sessions) as uow:
        for event in (missing, retained):
            await uow.events.upsert(event)
        await uow.events.deactivate_missing(None, 'demo', (retained.external_id,))
        await uow.commit()
    async with SqlAlchemyUnitOfWork(sessions) as uow:
        assert [event.external_id for event in await uow.events.available('Москва', 'demo', datetime.now(timezone.utc))] == [retained.external_id]
