from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import main
from app.bootstrap import Runtime
from app.transport.integrations.providers import DemoProvider
from app.repository.models import Base, Event
from app.service import catalog
from app.service.catalog import matches
from app.service.errors import ProviderUnavailable

NOW = datetime(2030, 1, 4, 9, tzinfo=timezone.utc)  # Friday, 12:00 Moscow.

class FixedClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW if tz else NOW.replace(tzinfo=None)


def event(start, end=None, **overrides):
    return SimpleNamespace(title='Событие', location_name='Площадка', category='kino',
                           is_free=False, price_min=None, timezone='Europe/Moscow',
                           start_date=datetime.fromisoformat(start),
                           end_date=datetime.fromisoformat(end) if end else datetime.fromisoformat(start) + timedelta(hours=2),
                           **overrides)

@pytest.mark.parametrize('now,start,expected', [
    (NOW, '2030-01-04T16:00:00+00:00', False),
    (NOW, '2030-01-05T16:00:00+00:00', True),
    (NOW, '2030-01-06T16:00:00+00:00', True),
    (NOW, '2030-01-07T16:00:00+00:00', False),
    (datetime(2030, 1, 6, 9, tzinfo=timezone.utc), '2030-01-05T16:00:00+00:00', False),
    (datetime(2030, 1, 6, 9, tzinfo=timezone.utc), '2030-01-06T16:00:00+00:00', True),
    (datetime(2030, 1, 7, 9, tzinfo=timezone.utc), '2030-01-12T16:00:00+00:00', True),
])
def test_weekend_boundaries(now, start, expected):
    assert matches(event(start), now=now, date_mode='weekend') is expected


def test_day_overlap_local_time_and_midnight():
    assert matches(event('2030-01-03T22:00:00+00:00'), now=NOW, date_mode='today')
    assert not matches(event('2030-01-03T19:00:00+00:00', '2030-01-03T21:00:00+00:00'), now=NOW, date_mode='today')
    assert matches(event('2030-01-03T19:00:00+00:00', '2030-01-05T21:00:00+00:00'), now=NOW, date_mode='date', selected_date=date(2030, 1, 4))
    assert matches(event('2030-01-04T15:00:00+00:00'), now=NOW, evening=True)
    assert not matches(event('2030-01-04T14:59:00+00:00'), now=NOW, evening=True)
    # SQLite's naive UTC values follow the same rules.
    assert matches(event('2030-01-04T15:00:00'), now=NOW, evening=True)

@pytest_asyncio.fixture
async def client(monkeypatch):
    test_engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    sessions = async_sessionmaker(test_engine, expire_on_commit=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    class Clock:
        def now(self):
            return NOW
    runtime = Runtime(sessions=sessions, database_engine=test_engine, clock=Clock())
    runtime.sync_state.last_sync['__demo__'] = NOW
    monkeypatch.setattr(main.app.state, 'runtime', runtime)
    rows = [
        ('Джазовый ВЕЧЕР', 'Музыкальная гостиная', 'koncerty', 1000, False, 'Москва', 'demo', 0),
        ('Выставка', 'Галерея', 'vystavki', 0, True, 'Москва', 'demo', 1),
        ('Экскурсия', 'Центр', 'ekskursii', None, False, 'Москва', 'demo', 1),
        ('100% _ искусство', 'Галерея', 'vystavki', 500, False, 'Москва', 'demo', 2),
        ('Другое место', 'Центр', 'kino', 0, True, 'Казань', 'demo', 1),
        ('Другой источник', 'Центр', 'kino', 0, True, 'Москва', 'culture', 1),
        ('Завершённое', 'Центр', 'kino', 0, True, 'Москва', 'demo', -1),
    ]
    async with sessions() as db:
        for i, (title, place, category, price, free, city, provider, day) in enumerate(rows):
            start = NOW.replace(hour=16) + timedelta(days=day)
            db.add(Event(external_id=f'catalog-test:{i}', title=title, location_name=place,
                         category=category, category_name=category, price_min=price, is_free=free,
                         city=city, provider=provider, start_date=start, end_date=start + timedelta(hours=2),
                         timezone='Europe/Moscow'))
        await db.commit()
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url='http://test') as http:
        yield http
    main.app.dependency_overrides.clear()
    await test_engine.dispose()

async def headers(client):
    auth = (await client.post('/api/v1/auth/demo')).json()
    result = {'Authorization': f"Bearer {auth['access_token']}"}
    await client.put('/api/v1/users/me/preferences', headers=result,
                     json={'city': 'Москва', 'categories': ['kino'], 'budget_max': 0})
    return result

@pytest.mark.asyncio
async def test_catalog_identity_reactions_and_pagination(client):
    assert (await client.get('/api/v1/events/catalog')).status_code == 401
    auth_headers = await headers(client)
    result = (await client.get('/api/v1/events/catalog', headers=auth_headers)).json()
    assert result['total'] == 4  # Profile's kino/free preferences do not restrict catalog.
    liked, skipped = [item['id'] for item in result['items'][:2]]
    await client.post(f'/api/v1/events/{liked}/reaction', headers=auth_headers, json={'reaction': 'like'})
    await client.post(f'/api/v1/events/{skipped}/reaction', headers=auth_headers, json={'reaction': 'dislike'})
    first = (await client.get('/api/v1/events/catalog?limit=2', headers=auth_headers)).json()
    second = (await client.get('/api/v1/events/catalog?limit=2&offset=2', headers=auth_headers)).json()
    assert first['total'] == second['total'] == 4
    assert first['has_more'] and not second['has_more']
    assert [item['id'] for item in first['items'] + second['items']] == [item['id'] for item in result['items']]
    assert first['items'][0]['is_saved']
    assert not first['items'][1]['is_saved']
    await client.post(f'/api/v1/events/{skipped}/reaction', headers=auth_headers, json={'reaction': 'like'})
    assert len((await client.get('/api/v1/events/favorites', headers=auth_headers)).json()) == 2
    # Another identity has the same catalog but no saved markers.
    from app.service.entities import User
    from app.transport.api.dependencies import current_user
    main.app.dependency_overrides[current_user] = lambda: User(id=uuid4(), first_name='Друг', city='Москва', onboarding_completed=True)
    other = (await client.get('/api/v1/events/catalog', headers=auth_headers)).json()
    assert all(not item['is_saved'] for item in other['items'])
    main.app.dependency_overrides.pop(current_user)

@pytest.mark.asyncio
async def test_search_price_dates_and_combined_filters(client):
    auth_headers = await headers(client)
    async def get(**params):
        response = await client.get('/api/v1/events/catalog', headers=auth_headers, params=params)
        assert response.status_code == 200
        return response.json()
    assert (await get(q='  джАЗОВЫЙ вечер  '))['total'] == 1
    assert (await get(q='ГОСТИНАЯ'))['total'] == 1
    assert (await get(q=''))['total'] == 4
    assert (await get(q='% _'))['total'] == 1
    assert (await get(q='100_'))['total'] == 0
    assert (await get(budget_max=500))['total'] == 2
    assert (await get(free_only=True))['total'] == 1
    assert (await get(date_mode='today'))['total'] == 1
    assert (await get(date_mode='date', date='2030-01-05'))['total'] == 2
    assert (await get(date_mode='weekend', categories=['vystavki', 'ekskursii'], budget_max=500))['total'] == 2
    assert (await get(time='evening'))['total'] == 4
    assert (await get(q='Несуществующее')) == {'items': [], 'total': 0, 'has_more': False}

@pytest.mark.asyncio
@pytest.mark.parametrize('query', ['date_mode=date', 'date_mode=invalid', 'date=2030-02-30', 'date=0', 'date=20300105', 'time=morning', 'free_only=true&budget_max=500', 'budget_max=-1', 'limit=101', 'offset=-1', 'q=' + 'x' * 201])
async def test_invalid_filters(client, query):
    assert (await client.get(f'/api/v1/events/catalog?{query}', headers=await headers(client))).status_code == 422

@pytest.mark.asyncio
async def test_sync_failure_uses_cache_and_errors_without_cache(client, monkeypatch):
    auth_headers = await headers(client)
    class FailingProvider(DemoProvider):
        async def events(self, city):
            raise ProviderUnavailable('Источник недоступен')
    main.app.state.runtime.provider = FailingProvider()
    main.app.state.runtime.sync_state.last_sync.clear()
    assert (await client.get('/api/v1/events/catalog', headers=auth_headers)).status_code == 200
    await client.put('/api/v1/users/me/preferences', headers=auth_headers, json={'city': 'Санкт-Петербург', 'categories': ['kino']})
    response = await client.get('/api/v1/events/catalog', headers=auth_headers)
    assert response.status_code == 502
    assert response.json()['detail'] == 'Источник недоступен'
