import hmac
from uuid import UUID

from .commands import ReactCommand, SavePreferencesCommand
from .entities import Identity, Preferences, ServiceConfig, User
from .errors import Forbidden, InvalidInput, NotFound, Unauthorized
from .ports import ClockPort, EventProviderPort, MaxVerifierPort, TokenPort, UnitOfWorkPort
from .results import AuthenticationResult, HealthResult, PreferencesResult, ReactionResult, SyncResult
from .sync import EventSyncService


class AuthService:
    def __init__(self, uow: UnitOfWorkPort, verifier: MaxVerifierPort, tokens: TokenPort,
                 clock: ClockPort, config: ServiceConfig):
        self.uow, self.verifier, self.tokens, self.clock, self.config = uow, verifier, tokens, clock, config

    async def authenticate(self, identity: Identity) -> AuthenticationResult:
        user = await self.uow.users.upsert_identity(identity, self.clock.now())
        await self.uow.commit()
        return AuthenticationResult(user=user, access_token=self.tokens.issue(user.id))

    async def max(self, raw: str):
        return await self.authenticate(self.verifier.verify(raw))

    async def demo(self):
        if not self.config.demo_mode:
            raise NotFound('Не найдено')
        return await self.authenticate(Identity(max_user_id=-1))

    async def current_user(self, token: str | None) -> User:
        if not token:
            raise Unauthorized('Сессия закончилась. Откройте приложение заново.')
        user_id = self.tokens.verify(token)
        user = await self.uow.users.get(user_id)
        if user is None:
            raise Unauthorized('Сессия закончилась. Откройте приложение заново.')
        return user


class PreferencesService:
    def __init__(self, uow: UnitOfWorkPort, provider: EventProviderPort, clock: ClockPort, config: ServiceConfig):
        self.uow, self.provider, self.clock, self.config = uow, provider, clock, config

    async def get(self, user: User) -> PreferencesResult | None:
        preferences = await self.uow.preferences.get(user.id)
        return PreferencesResult(city=user.city, preferences=preferences) if preferences else None

    async def save(self, user: User, command: SavePreferencesCommand) -> User:
        city = command.city.strip()
        if len(city) < 2:
            raise InvalidInput('Укажите город')
        if self.config.event_provider == 'demo' and city not in self.config.demo_cities:
            raise InvalidInput('В деморежиме доступны Москва, Санкт-Петербург и Казань')
        allowed = {category.id for category in await self.provider.categories()}
        if any(category not in allowed for category in command.preferences.categories):
            raise InvalidInput('Неизвестная категория')
        preference = command.preferences
        unique = Preferences(categories=tuple(dict.fromkeys(preference.categories)),
                             budget_max=preference.budget_max, companion=preference.companion,
                             preferred_days=preference.preferred_days, preferred_time=preference.preferred_time)
        await self.uow.preferences.save(user.id, unique, self.clock.now())
        updated_user = await self.uow.users.complete_onboarding(user.id, city)
        await self.uow.commit()
        return updated_user


class EventsService:
    def __init__(self, uow: UnitOfWorkPort, config: ServiceConfig):
        self.uow, self.config = uow, config

    async def detail(self, event_id: UUID):
        event = await self.uow.events.get(event_id)
        if event is None or event.provider != self.config.event_provider:
            raise NotFound('Мероприятие не найдено')
        return event

    async def favorites(self, user: User):
        return await self.uow.events.favorites(user.id, self.config.event_provider)

    async def react(self, user: User, command: ReactCommand):
        await self.detail(command.event_id)
        if command.reaction not in {'like', 'dislike'}:
            raise InvalidInput('Неизвестная реакция')
        await self.uow.reactions.save(user.id, command.event_id, command.reaction)
        await self.uow.commit()
        return ReactionResult(reaction=command.reaction)

    async def remove_reaction(self, user: User, event_id: UUID):
        if await self.uow.reactions.remove(user.id, event_id):
            await self.uow.commit()


class SystemService:
    def __init__(self, uow: UnitOfWorkPort, provider: EventProviderPort, config: ServiceConfig, sync: EventSyncService):
        self.uow, self.provider, self.config, self.sync = uow, provider, config, sync

    async def health(self):
        await self.uow.ping()
        return HealthResult()

    async def categories(self):
        return await self.provider.categories()

    def configuration(self):
        return self.config

    async def admin_sync(self, city: str, token: str):
        if not self.config.admin_sync_token or not hmac.compare_digest(token, self.config.admin_sync_token):
            raise Forbidden('Доступ запрещён')
        return SyncResult(synced=await self.sync.sync(city, force=True))
