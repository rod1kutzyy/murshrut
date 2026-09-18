from contextlib import asynccontextmanager
from datetime import datetime, timezone

from .config import get_settings
from .repository.database import Session, engine
from .repository.unit_of_work import SqlAlchemyUnitOfWork
from .service.entities import ServiceConfig
from .service.facade import Services
from .service.ports import ClockPort
from .service.sync import SyncState
from .transport.integrations.culture_data import CultureAPI
from .transport.integrations.demo_data import CITIES
from .transport.integrations.providers import CultureProvider, DemoProvider
from .transport.integrations.security import JwtTokens, MaxVerifier


class SystemClock(ClockPort):
    def now(self):
        return datetime.now(timezone.utc)


def settings_to_service_config(settings) -> ServiceConfig:
    return ServiceConfig(demo_mode=settings.demo_mode, event_provider=settings.event_provider,
                         max_bot_name=settings.max_bot_name,
                         demo_cities=tuple(CITIES) if settings.event_provider == 'demo' else (),
                         sync_interval_seconds=settings.sync_interval_seconds,
                         admin_sync_token=settings.admin_sync_token)


class Runtime:
    def __init__(self, settings=None, sessions=None, database_engine=None, provider=None,
                 clock=None, verifier=None, tokens=None, uow_factory=None):
        self.settings = settings or get_settings()
        self.sessions = sessions if sessions is not None else Session
        self.engine = database_engine if database_engine is not None else engine
        self.provider = provider if provider is not None else (
            DemoProvider() if self.settings.event_provider == 'demo'
            else CultureProvider(CultureAPI(self.settings)))
        self.clock = clock if clock is not None else SystemClock()
        self.security_clock = SystemClock()
        self.verifier, self.tokens = verifier, tokens
        self.sync_state = SyncState()
        self.uow_factory = uow_factory if uow_factory is not None else lambda: SqlAlchemyUnitOfWork(self.sessions)

    @asynccontextmanager
    async def services(self):
        async with self.uow_factory() as uow:
            yield Services(uow=uow, provider=self.provider,
                           verifier=self.verifier or MaxVerifier(self.settings.max_bot_token, self.security_clock),
                           tokens=self.tokens or JwtTokens(self.settings.jwt_secret, self.security_clock),
                           clock=self.clock, config=settings_to_service_config(self.settings),
                           sync_state=self.sync_state)

    async def startup(self):
        self.settings.validate_runtime()
        if self.settings.event_provider == 'demo':
            async with self.services() as services:
                await services.sync.sync()

    async def shutdown(self):
        await self.engine.dispose()
