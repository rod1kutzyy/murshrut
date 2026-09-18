import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

from .entities import ServiceConfig
from .errors import ProviderUnavailable
from .ports import ClockPort, EventProviderPort, UnitOfWorkPort

logger = logging.getLogger(__name__)


@dataclass
class SyncState:
    locks: dict[str, asyncio.Lock] = field(default_factory=dict)
    last_sync: dict[str, datetime] = field(default_factory=dict)


class EventSyncService:
    def __init__(self, uow: UnitOfWorkPort, provider: EventProviderPort,
                 clock: ClockPort, config: ServiceConfig, state: SyncState):
        self.uow, self.provider, self.clock, self.config, self.state = uow, provider, clock, config, state

    async def sync(self, city='Москва', force=False) -> int:
        key = city if self.config.event_provider == 'culture' else '__demo__'
        async with self.state.locks.setdefault(key, asyncio.Lock()):
            previous = self.state.last_sync.get(key)
            if not force and previous and (self.clock.now() - previous).total_seconds() < self.config.sync_interval_seconds:
                return 0
            events = await self.provider.events(city)
            for event in events:
                await self.uow.events.upsert(event)
            # Demo snapshots cover every demo city; Culture snapshots cover only the requested city.
            await self.uow.events.deactivate_missing(
                city if self.config.event_provider == 'culture' else None,
                self.config.event_provider, tuple(event.external_id for event in events),
            )
            await self.uow.commit()
            self.state.last_sync[key] = self.clock.now()
            return len(events)

    async def ensure(self, city: str):
        try:
            await self.sync(city)
        except ProviderUnavailable:
            await self.uow.rollback()
            if not await self.uow.events.has_available(city, self.config.event_provider, self.clock.now()):
                raise
            logger.warning('Culture sync failed; using cached events')
