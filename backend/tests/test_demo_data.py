from collections import Counter
from datetime import timedelta

from app.service.evenings import transfer
from app.transport.integrations.demo_data import (
    CATEGORIES,
    CITIES,
    TEMPLATES,
    demo_events,
)
from app.transport.integrations.mappers import provider_event_to_entity
from app.transport.integrations.schemas import ProviderEventDTO


def test_demo_catalog_covers_cities_categories_dates_and_price_scenarios():
    events = demo_events()

    assert len(events) == len(CITIES) * len(TEMPLATES)
    assert Counter(event["city"] for event in events) == {
        city: len(TEMPLATES) for city in CITIES
    }
    assert {event["category"] for event in events} == {
        category["id"] for category in CATEGORIES
    }

    moscow = [event for event in events if event["city"] == "Москва"]
    assert len({event["start_date"].date() for event in moscow}) == 5
    assert any(event["is_free"] for event in moscow)
    assert any(event["price_min"] is None for event in moscow)
    assert any(
        event["price_min"] is not None
        and event["price_max"] is not None
        and event["price_min"] != event["price_max"]
        for event in moscow
    )
    assert any("family" in event["tags"] for event in moscow)
    assert any(event["start_date"].hour < 15 for event in moscow)


def test_every_demo_event_matches_the_provider_contract():
    events = demo_events()

    parsed = [ProviderEventDTO.model_validate(event) for event in events]
    assert len({event.external_id for event in parsed}) == len(parsed)
    assert all(event.end_date > event.start_date for event in parsed)
    assert all(event.description.endswith("не реальная афиша.") for event in parsed)


def test_demo_catalog_has_a_free_route_that_fits_two_hours():
    events = [
        provider_event_to_entity(ProviderEventDTO.model_validate(event))
        for event in demo_events()
        if event["city"] == "Москва" and event["is_free"]
    ]

    assert any(
        second.start_date
        >= first.end_date + timedelta(minutes=transfer(first, second).minutes)
        and second.end_date - first.start_date <= timedelta(hours=2)
        for first in events
        for second in events
        if first.start_date < second.start_date
    )
