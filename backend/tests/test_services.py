from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.service.catalog import CatalogService
from app.service.commands import CatalogQuery, SavePreferencesCommand
from app.service.entities import Category, Preferences, Reaction, ServiceConfig, User
from app.service.errors import InvalidInput, ProviderUnavailable
from app.service.recommendations import RecommendationService
from app.service.sync import EventSyncService, SyncState
from app.service.use_cases import PreferencesService
from factories import make_event

NOW = datetime(2030, 1, 4, 9, tzinfo=timezone.utc)
CONFIG = ServiceConfig(demo_mode=True, event_provider='demo', max_bot_name='',
                       demo_cities=('Москва', 'Казань'), sync_interval_seconds=1800, admin_sync_token='')
USER = User(id=uuid4(), first_name='Друг', city='Москва', onboarding_completed=True)


class Clock:
    def now(self):
        return NOW


class Provider:
    async def categories(self):
        return [Category(id='kino', name='Кино')]

    async def events(self, city):
        return []


class FakeUow:
    def __init__(self, events=(), history=(), preferences=None):
        self.rows, self.history_rows, self.preference = list(events), list(history), preferences
        self.commits, self.rollbacks, self.upserts = 0, 0, []
        self.events = SimpleNamespace(available=self.available, has_available=self.has_available,
                                      upsert=self.upsert, deactivate_missing=self.deactivate_missing)
        self.snapshots = []
        self.reactions = SimpleNamespace(history=self.history, saved_ids=self.saved_ids)
        self.preferences = SimpleNamespace(get=self.get_preference, save=self.save_preference)
        self.users = SimpleNamespace(complete_onboarding=self.complete_onboarding)

    async def available(self, *args, **kwargs):
        return self.rows

    async def has_available(self, *args):
        return bool(self.rows)

    async def upsert(self, event):
        self.upserts.append(event)

    async def deactivate_missing(self, city, provider, external_ids):
        self.snapshots.append((city, provider, external_ids))

    async def history(self, user_id):
        return self.history_rows

    async def saved_ids(self, user_id):
        return {row.event_id for row in self.history_rows if row.reaction == 'like'}

    async def get_preference(self, user_id):
        return self.preference

    async def save_preference(self, user_id, preferences, now):
        self.preference = preferences

    async def complete_onboarding(self, user_id, city):
        return replace(USER, city=city, onboarding_completed=True)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


def sync_for(uow, provider=None):
    state = SyncState(last_sync={'__demo__': NOW})
    return EventSyncService(uow, provider or Provider(), Clock(), CONFIG, state)


@pytest.mark.asyncio
async def test_catalog_filters_before_pagination_and_includes_seen_events():
    paid, free, unknown = make_event(), make_event(is_free=True, price_min=0), make_event(price_min=None)
    uow = FakeUow(events=[paid, free, unknown], history=[Reaction(paid.id, 'kino', 'dislike'), Reaction(free.id, 'kino', 'like')])
    service = CatalogService(uow, sync_for(uow), Clock(), 'demo')
    result = await service.get(USER, CatalogQuery(budget_max=500, limit=1, offset=1))
    assert result.total == 2 and not result.has_more
    assert result.items[0].event == free and result.items[0].is_saved
    result = await service.get(USER, CatalogQuery())
    assert result.items[0].event == paid  # Dislike does not exclude a catalog item.
    assert uow.commits == 0


@pytest.mark.asyncio
async def test_recommendation_ranking_uses_preferences_and_history():
    liked = make_event()
    movie = make_event(title='Кино')
    concert = make_event(title='Концерт', category='koncerty')
    preference = Preferences(('kino',), 500, 'family', 'weekends', 'evening')
    uow = FakeUow(events=[liked, concert, movie], history=[Reaction(liked.id, 'kino', 'like')], preferences=preference)
    result = await RecommendationService(uow, sync_for(uow), Clock(), 'demo').get(USER, 20)
    assert [row.event for row in result] == [movie, concert]
    assert 'По вашим интересам' in result[0].reasons
    assert 'Похоже на то, что вам нравится' in result[0].reasons
    assert 'Для всей семьи' in result[0].reasons


@pytest.mark.asyncio
async def test_preferences_validate_then_commit_once():
    uow = FakeUow()
    service = PreferencesService(uow, Provider(), Clock(), CONFIG)
    preferences = Preferences(('kino', 'kino'), 1000, 'friends', 'any', 'any')
    result = await service.save(USER, SavePreferencesCommand(' Казань ', preferences))
    assert result.city == 'Казань'
    assert uow.preference.categories == ('kino',)
    assert uow.commits == 1
    with pytest.raises(InvalidInput, match='Неизвестная категория'):
        await service.save(USER, SavePreferencesCommand('Москва', replace(preferences, categories=('missing',))))
    assert uow.commits == 1


@pytest.mark.asyncio
async def test_sync_commits_and_only_then_updates_interval():
    class EventsProvider(Provider):
        async def events(self, city):
            return [make_event()]
    uow = FakeUow()
    state = SyncState()
    sync = EventSyncService(uow, EventsProvider(), Clock(), CONFIG, state)
    assert await sync.sync() == 1
    assert await sync.sync() == 0
    assert len(uow.upserts) == 1 and uow.commits == 1
    async def fail_commit():
        raise RuntimeError('Commit failed')
    uow.commit = fail_commit
    state.last_sync.clear()
    with pytest.raises(RuntimeError, match='Commit failed'):
        await sync.sync()
    assert state.last_sync == {}


@pytest.mark.asyncio
async def test_sync_rollback_allows_cache_read():
    class FailingProvider(Provider):
        async def events(self, city):
            raise ProviderUnavailable('Источник недоступен')
    uow = FakeUow(events=[make_event()])
    sync = EventSyncService(uow, FailingProvider(), Clock(), CONFIG, SyncState())
    await sync.ensure('Москва')
    assert uow.rollbacks == 1
    uow.rows.clear()
    with pytest.raises(ProviderUnavailable, match='Источник недоступен'):
        await sync.ensure('Москва')
    assert uow.rollbacks == 2
