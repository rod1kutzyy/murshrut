from datetime import datetime, timedelta, timezone

CATEGORIES = [
    {'id': 'koncerty', 'name': 'Концерты'}, {'id': 'spektakli', 'name': 'Театр'},
    {'id': 'vystavki', 'name': 'Выставки'}, {'id': 'kino', 'name': 'Кино'},
    {'id': 'ekskursii', 'name': 'Экскурсии'}, {'id': 'obuchenie', 'name': 'Лекции и обучение'},
    {'id': 'vstrechi', 'name': 'Встречи'}, {'id': 'prazdniki', 'name': 'Праздники'},
    {'id': 'prochie', 'name': 'Другое'},
]
CITIES = {'Москва': (55.7558, 37.6173), 'Санкт-Петербург': (59.9343, 30.3351), 'Казань': (55.7963, 49.1088)}

def demo_events():
    templates = [
        ('Джаз под звёздами', 'koncerty', 1200, 'Камерный вечер с джазовым квартетом. Живой звук, любимые стандарты и немного импровизации.', 'Музыкальная гостиная', 'jazz', []),
        ('Искусство быть собой', 'vystavki', 0, 'Выставка современного искусства о повседневности, мечтах и поиске себя. Живопись, фотография и инсталляции.', 'Галерея «Пространство»', 'art', []),
        ('Маленький принц', 'spektakli', 800, 'Тёплая постановка для детей и взрослых о дружбе и о том, что самое важное нельзя увидеть глазами.', 'Камерный театр', 'theatre', ['family']),
        ('Кино на большом экране', 'kino', 400, 'Вечер классического кино с обсуждением после показа. Посмотрите знакомую историю по-новому.', 'Киноклуб', 'cinema', []),
        ('Город: скрытые истории', 'ekskursii', 500, 'Прогулка по тихим улицам с местным историком. Необычные дома, городские легенды и новые маршруты.', 'Городской центр', 'city', []),
        ('Как смотреть на искусство', 'obuchenie', 300, 'Доступная лекция искусствоведа: учимся замечать детали и понимать замысел художника без сложных терминов.', 'Лекторий', 'art', []),
        ('Акустический вечер', 'koncerty', 1500, 'Молодые музыканты, авторские песни и уютная атмосфера. Приходите с друзьями и открывайте новые имена.', 'Культурный центр', 'jazz', []),
        ('День семейных открытий', 'prazdniki', 0, 'Мастер-классы, игры и небольшой концерт. Проведите день вместе и попробуйте что-нибудь новое.', 'Городской парк', 'city', ['family']),
        ('Вечер настольных игр', 'vstrechi', 0, 'Новые знакомства и настольные игры. Ведущий объяснит правила, а компания найдётся на месте.', 'Библиотека', 'cinema', []),
    ]
    names = {c['id']: c['name'] for c in CATEGORIES}
    base = datetime.now(timezone.utc).replace(hour=16, minute=0, second=0, microsecond=0) + timedelta(days=1)
    result = []
    for city, (lat, lon) in CITIES.items():
        for i, (title, category, price, desc, place, artwork, tags) in enumerate(templates):
            start = base + timedelta(days=i)
            result.append(dict(external_id=f'demo:{city}:{i}', title=title, description=desc + ' Это демонстрационное мероприятие, не реальная афиша.', category=category, category_name=names[category], tags=tags, image_url=f'/art/{artwork}.svg', image_credit='Иллюстрация приложения', start_date=start, end_date=start + timedelta(hours=2), timezone='Europe/Moscow', price_min=price, price_max=price, is_free=price == 0, city=city, location_name=place, address='Демонстрационная локация в центре города', latitude=lat + (i % 3 - 1) * .018, longitude=lon + (i // 3 - 1) * .025, source_url=None, provider='demo'))
    return result
