from .catalog import CatalogService
from .evenings import EveningService
from .entities import ServiceConfig
from .ports import (
    ClockPort,
    EventProviderPort,
    MaxVerifierPort,
    TokenPort,
    UnitOfWorkPort,
)
from .recommendations import RecommendationService
from .sync import EventSyncService, SyncState
from .use_cases import AuthService, EventsService, PreferencesService, SystemService


class Services:
    def __init__(
        self,
        uow: UnitOfWorkPort,
        provider: EventProviderPort,
        verifier: MaxVerifierPort,
        tokens: TokenPort,
        clock: ClockPort,
        config: ServiceConfig,
        sync_state: SyncState,
    ):
        self.sync = EventSyncService(uow, provider, clock, config, sync_state)
        self.auth = AuthService(uow, verifier, tokens, clock, config)
        self.preferences = PreferencesService(uow, provider, clock, config)
        self.events = EventsService(uow, config)
        self.catalog = CatalogService(uow, self.sync, clock, config.event_provider)
        self.recommendations = RecommendationService(
            uow, self.sync, clock, config.event_provider
        )
        self.evenings = EveningService(uow, self.sync, clock, config.event_provider)
        self.system = SystemService(uow, provider, config, self.sync)
