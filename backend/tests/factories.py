from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.service.entities import Event


def make_event(**overrides):
    start = datetime(2030, 1, 5, 16, tzinfo=timezone.utc)
    values = dict(id=uuid4(), external_id=f'test:{uuid4()}', title='Событие', description='Описание',
                  category='kino', category_name='Кино', tags=('family',), image_url=None,
                  image_credit=None, start_date=start, end_date=start + timedelta(hours=2),
                  timezone='Europe/Moscow', price_min=500, price_max=1000, is_free=False,
                  city='Москва', location_name='Клуб', address='Центр', latitude=None,
                  longitude=None, source_url=None, provider='demo')
    values.update(overrides)
    return Event(**values)
