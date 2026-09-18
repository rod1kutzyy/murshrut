import hashlib
import hmac
import json
import time
from urllib.parse import urlencode
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
settings = app.state.runtime.settings
from app.repository.database import engine
from app.repository.models import Base

@pytest.mark.asyncio
async def test_end_to_end_preferences_reactions_and_identity(monkeypatch):
    monkeypatch.setattr(settings, 'max_bot_token', 'test-bot-token')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with app.router.lifespan_context(app), AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        assert (await client.get('/api/v1/users/me')).status_code == 401
        auth = (await client.post('/api/v1/auth/demo')).json()
        headers = {'Authorization': f"Bearer {auth['access_token']}"}
        assert (await client.post('/api/v1/auth/max', json={'init_data': ''})).status_code == 401
        assert (await client.get('/api/v1/recommendations', headers=headers)).status_code == 409
        pref = {'city': 'Москва', 'categories': ['koncerty'], 'budget_max': 1500, 'companion': 'friends', 'preferred_days': 'weekends', 'preferred_time': 'evening'}
        assert (await client.put('/api/v1/users/me/preferences', headers=headers, json=pref)).status_code == 200
        assert (await client.get('/api/v1/users/me/preferences', headers=headers)).json() == pref
        events = (await client.get('/api/v1/recommendations', headers=headers)).json()
        assert len(events) == 9 and all(e['city'] == 'Москва' for e in events)
        assert events[0]['category'] == 'koncerty'
        liked, disliked = events[0]['id'], events[1]['id']
        for event_id, reaction in [(liked, 'like'), (liked, 'like'), (disliked, 'dislike')]:
            assert (await client.post(f'/api/v1/events/{event_id}/reaction', headers=headers, json={'reaction': reaction})).status_code == 200
        remaining = (await client.get('/api/v1/recommendations', headers=headers)).json()
        assert len(remaining) == 7 and not {liked, disliked} & {e['id'] for e in remaining}
        assert [e['id'] for e in (await client.get('/api/v1/events/favorites', headers=headers)).json()] == [liked]
        assert (await client.get(f'/api/v1/events/{liked}', headers=headers)).json()['latitude'] is not None
        assert (await client.post(f'/api/v1/events/{liked}/reaction', headers=headers, json={'reaction': 'unknown'})).status_code == 422
        # Signed MAX identity is distinct from the shared demo profile and gets no other user's favorites.
        data = {'auth_date': str(int(time.time())), 'user': json.dumps({'id': 123456, 'first_name': 'Алексей'})}
        check = '\n'.join(f'{k}={v}' for k, v in sorted(data.items()))
        secret = hmac.new(b'WebAppData', settings.max_bot_token.encode(), hashlib.sha256).digest()
        data['hash'] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        body = {'init_data': urlencode(data)}
        real_auth = (await client.post('/api/v1/auth/max', json=body)).json()
        repeat = (await client.post('/api/v1/auth/max', json=body)).json()
        assert real_auth['user']['id'] == repeat['user']['id'] != auth['user']['id']
        assert (await client.get('/api/v1/events/favorites', headers={'Authorization': f"Bearer {real_auth['access_token']}"})).json() == []
        assert (await client.delete(f'/api/v1/events/{liked}/reaction', headers=headers)).status_code == 204
        assert (await client.get('/api/v1/events/favorites', headers=headers)).json() == []
        pref['city'] = 'Казань'
        assert (await client.put('/api/v1/users/me/preferences', headers=headers, json=pref)).status_code == 200
        assert all(e['city'] == 'Казань' for e in (await client.get('/api/v1/recommendations', headers=headers)).json())
        assert (await client.post('/api/admin/events/sync')).status_code == 403
        assert (await client.get('/api/v1/events/00000000-0000-0000-0000-000000000000', headers=headers)).status_code == 404
