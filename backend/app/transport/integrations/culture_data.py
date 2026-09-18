import html
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from datetime import datetime, timezone
from urllib.parse import urljoin
import httpx
from ...config import get_settings

from ...service.errors import ProviderUnavailable

CultureAPIError = ProviderUnavailable


def safe_url(value):
    return value if isinstance(value, str) and value.startswith(('https://', 'http://')) else None


def timestamp(value):
    if not isinstance(value, (int, float)):
        raise ValueError('Missing timestamp')
    return datetime.fromtimestamp(value / 1000 if value > 100000000000 else value, timezone.utc)


def normalize_event(raw):
    places = raw.get('places') or []
    place = places[0] if places else {}
    future = sorted((s for s in raw.get('seances', []) if isinstance(s.get('end'), (int, float)) and timestamp(s['end']) >= datetime.now(timezone.utc)), key=lambda s: s['start'])
    seance = future[0] if future else None
    if seance and 0 <= seance.get('placeIndex', 0) < len(places):
        place = places[seance.get('placeIndex', 0)]
    address = place.get('address') or {}
    locale = place.get('locale') or {}
    coords = (place.get('mapPosition') or {}).get('coordinates') or []
    # PRO API documents coordinates as [latitude, longitude], not GeoJSON order.
    lat, lon = (coords[:2] if len(coords) >= 2 else (None, None))
    if lat is not None and (not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)) or not -90 <= lat <= 90 or not -180 <= lon <= 180):
        lat, lon = None, None
    zone = locale.get('timezone', 'Europe/Moscow')
    try:
        ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        zone = 'Europe/Moscow'
    category = raw.get('category') or {}
    image = raw.get('image') or {}
    image_url = safe_url(image.get('url'))
    return dict(
        external_id=f"culture:{raw['_id']}", title=raw['name'],
        description=html.unescape(re.sub('<[^>]+>', ' ', raw.get('description', ''))).strip(),
        category=category.get('sysName', 'prochie'), category_name=category.get('name', 'Другое'),
        tags=[str(t.get('name', '')) for t in raw.get('tags', []) if isinstance(t, dict)],
        image_url=image_url, image_credit=' · '.join(filter(None, [image.get('author'), image.get('source')])) or None,
        start_date=timestamp(seance['start'] if seance else raw['start']), end_date=timestamp(seance['end'] if seance else raw['end']),
        timezone=zone, price_min=raw.get('price'), price_max=raw.get('maxPrice'), is_free=bool(raw.get('isFree')),
        city=(address.get('city') or {}).get('name') or locale.get('name', ''), location_name=place.get('name', ''),
        address=address.get('source') or ', '.join(str((address.get(k) or {}).get('name', '')) for k in ('city', 'street', 'house')),
        latitude=lat, longitude=lon, source_url=safe_url(raw.get('saleLink')) or f"https://www.culture.ru/events/{raw['_id']}", provider='culture',
    )

class CultureAPI:
    def __init__(self, settings=None):
        self.settings = settings or get_settings()

    async def request(self, path, **params):
        try:
            async with httpx.AsyncClient(timeout=25) as client:
                response = await client.get(urljoin(self.settings.culture_api_url, path), params={'apiKey': self.settings.culture_api_key, **params})
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError):
            # Do not include upstream URLs in errors: query string contains apiKey.
            raise CultureAPIError('Не удалось получить данные PRO.Культура.РФ. Проверьте ключ и доступность API.') from None

    async def categories(self):
        data = await self.request('categories', type='events', limit=100)
        return [{'id': c['sysName'], 'name': c['name']} for c in data.get('categories', [])]

    async def events(self, city):
        locales = await self.request('locales', nameQuery=city, limit=100)
        locale_rows = locales.get('locales')
        if not isinstance(locale_rows, list) or any(not isinstance(row, dict) for row in locale_rows):
            raise CultureAPIError('Неожиданный формат ответа PRO.Культура.РФ')
        ids = [str(c['_id']) for c in locale_rows if c.get('name', '').casefold() == city.casefold()]
        if not ids:
            return []
        result = []
        offset = 0
        seen_pages = set()
        while True:
            data = await self.request(self.settings.culture_events_path, locales=','.join(ids), limit=100, offset=offset)
            rows = data.get('events', data.get('pushkinsCardEvents'))
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise CultureAPIError('Неожиданный формат ответа PRO.Культура.РФ')
            page_ids = tuple(str(row.get('_id')) for row in rows)
            if rows and page_ids in seen_pages:
                raise CultureAPIError('Не удалось получить полный список событий PRO.Культура.РФ')
            seen_pages.add(page_ids)
            for row in rows:
                try:
                    event = normalize_event(row)
                    if event['end_date'] >= datetime.now(timezone.utc):
                        result.append(event)
                except (KeyError, ValueError, TypeError, OverflowError):
                    continue
            if len(rows) < 100:
                break
            offset += 100
        return result
