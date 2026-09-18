from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..service.ports import UnitOfWorkPort
from .repositories import (
    EveningRepository,
    EventRepository,
    PreferencesRepository,
    ReactionRepository,
    UserRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWorkPort):
    def __init__(self, sessions: async_sessionmaker[AsyncSession]):
        self._sessions = sessions

    async def __aenter__(self):
        self._session = self._sessions()
        self.users = UserRepository(self._session)
        self.preferences = PreferencesRepository(self._session)
        self.events = EventRepository(self._session)
        self.reactions = ReactionRepository(self._session)
        self.evenings = EveningRepository(self._session)
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        try:
            await self._session.rollback()
        finally:
            await self._session.close()

    async def commit(self):
        await self._session.commit()

    async def rollback(self):
        await self._session.rollback()

    async def ping(self):
        await self._session.execute(text("SELECT 1"))
