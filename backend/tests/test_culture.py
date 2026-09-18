from datetime import datetime, timezone, timedelta
from app.transport.integrations.culture_data import normalize_event

def test_documented_pro_culture_normalization():
    now = datetime.now(timezone.utc) + timedelta(days=2)
    start = int(now.timestamp() * 1000)
    row = {'_id': 123, 'name': 'Спектакль', 'description': '<p>Привет &amp; мир</p>', 'start': start - 86400000, 'end': start + 7200000, 'price': 500, 'maxPrice': 1000, 'isFree': False, 'category': {'sysName': 'spektakli', 'name': 'Спектакли'}, 'image': {'url': 'https://example.org/image.jpg', 'author': 'Автор'}, 'places': [{'name': 'Театр', 'locale': {'name': 'Москва', 'timezone': 'Europe/Moscow'}, 'address': {'city': {'name': 'Москва'}, 'source': 'Улица, 1'}, 'mapPosition': {'coordinates': [55.75, 37.61]}}], 'seances': [{'start': start, 'end': start + 7200000, 'placeIndex': 0}]}
    e = normalize_event(row)
    assert e['start_date'] == datetime.fromtimestamp(start / 1000, timezone.utc)
    assert e['latitude'] == 55.75 and e['longitude'] == 37.61
    assert e['description'] == 'Привет & мир'
    assert e['city'] == 'Москва' and e['category'] == 'spektakli'
    assert e['image_url'] == 'https://example.org/image.jpg'

import httpx
import pytest
from app.transport.integrations import culture_data as culture_api
from app.transport.integrations.culture_data import CultureAPI, CultureAPIError

@pytest.mark.asyncio
async def test_provider_uses_server_key_and_documented_endpoints(monkeypatch):
    original_client = httpx.AsyncClient
    calls = []
    def handler(request):
        calls.append(request)
        assert request.url.params['apiKey'] == 'private-partner-key'
        if request.url.path.endswith('/categories'):
            assert request.url.params['type'] == 'events'
            return httpx.Response(200, json={'categories': [{'sysName': 'kino', 'name': 'Кино'}]})
        if request.url.path.endswith('/locales'):
            return httpx.Response(200, json={'locales': [{'_id': 8, 'name': 'Москва'}]})
        assert request.url.path.endswith('/pushkinsCardEvents')
        assert request.url.params['locales'] == '8'
        return httpx.Response(200, json={'events': []})
    monkeypatch.setattr(culture_api.httpx, 'AsyncClient', lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs))
    provider = CultureAPI()
    monkeypatch.setattr(provider.settings, 'culture_api_key', 'private-partner-key')
    assert await provider.categories() == [{'id': 'kino', 'name': 'Кино'}]
    assert await provider.events('Москва') == []
    assert len(calls) == 3

@pytest.mark.asyncio
async def test_upstream_failure_does_not_expose_key(monkeypatch):
    original_client = httpx.AsyncClient
    monkeypatch.setattr(culture_api.httpx, 'AsyncClient', lambda **kwargs: original_client(transport=httpx.MockTransport(lambda request: httpx.Response(403)), **kwargs))
    provider = CultureAPI()
    monkeypatch.setattr(provider.settings, 'culture_api_key', 'private-partner-key')
    with pytest.raises(CultureAPIError) as exc:
        await provider.categories()
    assert 'private-partner-key' not in str(exc.value)

@pytest.mark.asyncio
async def test_snapshot_fetches_pages_beyond_previous_limit(monkeypatch):
    provider = CultureAPI()
    offsets = []
    async def request(path, **params):
        if path == 'locales':
            return {'locales': [{'_id': 8, 'name': 'Москва'}]}
        offset = params['offset']
        offsets.append(offset)
        return {'events': [{'_id': i} for i in range(offset, offset + 100)] if offset < 1100 else []}
    monkeypatch.setattr(provider, 'request', request)
    monkeypatch.setattr(culture_api, 'normalize_event', lambda row: {
        'external_id': str(row['_id']), 'end_date': datetime.now(timezone.utc) + timedelta(days=1)})
    assert len(await provider.events('Москва')) == 1100
    assert offsets[-1] == 1100


@pytest.mark.asyncio
async def test_incomplete_or_malformed_snapshot_is_a_failure(monkeypatch):
    provider = CultureAPI()
    async def request(path, **params):
        if path == 'locales':
            return {'locales': [{'_id': 8, 'name': 'Москва'}]}
        return {}
    monkeypatch.setattr(provider, 'request', request)
    with pytest.raises(CultureAPIError, match='формат'):
        await provider.events('Москва')
    async def repeated_page(path, **params):
        if path == 'locales':
            return {'locales': [{'_id': 8, 'name': 'Москва'}]}
        return {'events': [{'_id': i} for i in range(100)]}
    monkeypatch.setattr(provider, 'request', repeated_page)
    monkeypatch.setattr(culture_api, 'normalize_event', lambda row: {
        'end_date': datetime.now(timezone.utc) + timedelta(days=1)})
    with pytest.raises(CultureAPIError, match='полный список'):
        await provider.events('Москва')
