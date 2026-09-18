from ...service.ports import EventProviderPort
from .culture_data import CultureAPI
from .demo_data import CATEGORIES, demo_events
from .mappers import category_to_entity, provider_event_to_entity
from .schemas import CategoryDTO, ProviderEventDTO


class DemoProvider(EventProviderPort):
    async def categories(self):
        return [category_to_entity(CategoryDTO.model_validate(row)) for row in CATEGORIES]

    async def events(self, city: str):
        return [provider_event_to_entity(ProviderEventDTO.model_validate(row)) for row in demo_events()]


class CultureProvider(EventProviderPort):
    def __init__(self, client: CultureAPI):
        self._client = client

    async def categories(self):
        return [category_to_entity(CategoryDTO.model_validate(row)) for row in await self._client.categories()]

    async def events(self, city: str):
        return [provider_event_to_entity(ProviderEventDTO.model_validate(row)) for row in await self._client.events(city)]
