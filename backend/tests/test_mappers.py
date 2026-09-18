from datetime import date
from uuid import uuid4

from app.service.entities import Preferences, User
from app.service.results import CatalogEvent, CatalogResult, PreferencesResult, RecommendedEvent
from app.transport.api.schemas import PreferencesInput, ReactionInput
from app.transport.integrations.mappers import profile_to_identity, provider_event_to_entity
from app.transport.integrations.schemas import MaxProfileDTO, ProviderEventDTO
from app.transport.mappers import (catalog_to_query, catalog_to_response, event_response_values,
                                  preferences_to_command, preferences_to_response, reaction_to_command,
                                  recommendation_to_response, user_to_response)
from app.repository.mappers import event_to_values
from factories import make_event


def test_request_to_business_commands():
    body = PreferencesInput(city='Москва', categories=['kino'], budget_max=None)
    command = preferences_to_command(body)
    body.categories.append('koncerty')
    assert command.preferences.categories == ('kino',)
    assert command.preferences.budget_max is None
    event_id = uuid4()
    reaction = reaction_to_command(event_id, ReactionInput(reaction='like'))
    assert reaction.event_id == event_id and reaction.reaction == 'like'
    query = catalog_to_query('поиск', 'date', date(2030, 1, 5), ['kino'], False, 500, 'evening', 20, 40)
    assert query.selected_date == date(2030, 1, 5) and query.evening
    assert query.categories == ('kino',) and query.offset == 40


def test_business_results_to_http_schemas():
    event = make_event()
    recommended = recommendation_to_response(RecommendedEvent(event, ('По вашим интересам',)))
    assert recommended.reasons == ['По вашим интересам']
    assert recommended.id == event.id and recommended.image_url is None
    catalog = catalog_to_response(CatalogResult((CatalogEvent(event, True),), 1, False))
    assert catalog.items[0].is_saved and catalog.items[0].reasons == []
    assert catalog.model_dump(mode='json')['items'][0]['id'] == str(event.id)
    assert 'external_id' not in catalog.items[0].model_dump()
    user = User(uuid4(), 'Имя', 'Москва', True)
    assert user_to_response(user).onboarding_completed
    preference = Preferences(('kino',), None, 'solo', 'any', 'evening')
    response = preferences_to_response(PreferencesResult('Москва', preference))
    response.categories.append('new')
    assert preference.categories == ('kino',)


def test_external_dtos_to_business_entities():
    profile = profile_to_identity(MaxProfileDTO(id=123, first_name=None, username='user'))
    assert profile.max_user_id == 123 and profile.first_name == 'Друг' and profile.username == 'user'
    event = make_event()
    dto = ProviderEventDTO.model_validate(event_to_values(event))
    draft = provider_event_to_entity(dto)
    dto.tags.append('changed')
    assert draft.external_id == event.external_id and draft.tags == ('family',)
    assert draft.start_date == event.start_date and draft.price_max == event.price_max
