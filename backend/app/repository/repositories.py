from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..service.entities import (
    EventDraft,
    EveningPlan as EveningEntity,
    Identity,
    Preferences,
)
from ..service.ports import (
    EveningRepositoryPort,
    EventRepositoryPort,
    PreferencesRepositoryPort,
    ReactionRepositoryPort,
    UserRepositoryPort,
)
from .models import Event, EventReaction, EveningPlan, User, UserPreference
from .mappers import (
    evening_from_model,
    event_from_model,
    event_to_values,
    identity_to_values,
    preferences_from_model,
    preferences_to_values,
    reaction_from_row,
    user_from_model,
)


def insert_for(session: AsyncSession, model):
    return (sqlite_insert if session.bind.dialect.name == "sqlite" else pg_insert)(
        model
    )


class UserRepository(UserRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, user_id: UUID):
        row = await self._session.get(User, user_id)
        return user_from_model(row) if row else None

    async def upsert_identity(self, identity: Identity, now: datetime):
        values = identity_to_values(identity)
        statement = insert_for(self._session, User).values(
            max_user_id=identity.max_user_id, **values
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["max_user_id"], set_={**values, "updated_at": now}
            )
        )
        await self._session.flush()
        row = await self._session.scalar(
            select(User)
            .where(User.max_user_id == identity.max_user_id)
            .execution_options(populate_existing=True)
        )
        return user_from_model(row)

    async def complete_onboarding(self, user_id: UUID, city: str):
        row = await self._session.get(User, user_id)
        row.city, row.onboarding_completed = city, True
        await self._session.flush()
        return user_from_model(row)


class PreferencesRepository(PreferencesRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, user_id: UUID):
        row = await self._session.scalar(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        return preferences_from_model(row) if row else None

    async def save(self, user_id: UUID, preferences: Preferences, now: datetime):
        values = preferences_to_values(preferences)
        statement = insert_for(self._session, UserPreference).values(
            user_id=user_id, **values
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["user_id"], set_={**values, "updated_at": now}
            )
        )
        await self._session.flush()


class EventRepository(EventRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, event_id: UUID):
        row = await self._session.get(Event, event_id)
        return event_from_model(row) if row and row.is_active else None

    async def available(
        self, city: str, provider: str, now: datetime, *, inclusive: bool = True
    ):
        date_condition = Event.end_date >= now if inclusive else Event.end_date > now
        rows = (
            await self._session.scalars(
                select(Event)
                .where(
                    Event.city.ilike(city),
                    Event.provider == provider,
                    Event.is_active.is_(True),
                    date_condition,
                )
                .order_by(Event.start_date, Event.id)
            )
        ).all()
        return [event_from_model(row) for row in rows]

    async def has_available(self, city: str, provider: str, now: datetime):
        return (
            await self._session.scalar(
                select(Event.id)
                .where(
                    Event.city.ilike(city),
                    Event.provider == provider,
                    Event.is_active.is_(True),
                    Event.end_date > now,
                )
                .limit(1)
            )
            is not None
        )

    async def favorites(self, user_id: UUID, provider: str):
        rows = (
            await self._session.scalars(
                select(Event)
                .join(EventReaction)
                .where(
                    EventReaction.user_id == user_id,
                    EventReaction.reaction == "like",
                    Event.provider == provider,
                    Event.is_active.is_(True),
                )
                .order_by(EventReaction.created_at.desc())
            )
        ).all()
        return [event_from_model(row) for row in rows]

    async def upsert(self, event: EventDraft):
        values = event_to_values(event)
        values["is_active"] = True
        row = await self._session.scalar(
            select(Event).where(Event.external_id == event.external_id)
        )
        if row:
            for field, value in values.items():
                setattr(row, field, value)
        else:
            self._session.add(Event(**values))
        await self._session.flush()

    async def deactivate_missing(
        self, city: str | None, provider: str, external_ids: tuple[str, ...]
    ):
        conditions = [Event.provider == provider, Event.is_active.is_(True)]
        if city is not None:
            conditions.append(Event.city.ilike(city))
        if external_ids:
            conditions.append(Event.external_id.not_in(external_ids))
        await self._session.execute(
            update(Event).where(*conditions).values(is_active=False)
        )
        await self._session.flush()


class ReactionRepository(ReactionRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def history(self, user_id: UUID):
        rows = (
            await self._session.execute(
                select(EventReaction.event_id, Event.category, EventReaction.reaction)
                .join(Event, Event.id == EventReaction.event_id)
                .where(EventReaction.user_id == user_id)
            )
        ).all()
        return [
            reaction_from_row(event_id, category, reaction)
            for event_id, category, reaction in rows
        ]

    async def saved_ids(self, user_id: UUID):
        return set(
            (
                await self._session.scalars(
                    select(EventReaction.event_id).where(
                        EventReaction.user_id == user_id,
                        EventReaction.reaction == "like",
                    )
                )
            ).all()
        )

    async def save(self, user_id: UUID, event_id: UUID, reaction: str):
        statement = insert_for(self._session, EventReaction).values(
            user_id=user_id, event_id=event_id, reaction=reaction
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["user_id", "event_id"], set_={"reaction": reaction}
            )
        )
        await self._session.flush()

    async def remove(self, user_id: UUID, event_id: UUID):
        row = await self._session.scalar(
            select(EventReaction).where(
                EventReaction.user_id == user_id, EventReaction.event_id == event_id
            )
        )
        if not row:
            return False
        await self._session.delete(row)
        await self._session.flush()
        return True

    async def popularity(self, user_id, event_ids):
        if not event_ids:
            return {}
        rows = (
            await self._session.execute(
                select(
                    EventReaction.event_id,
                    func.sum(case((EventReaction.reaction == "like", 1), else_=0)),
                    func.count(),
                )
                .where(
                    EventReaction.user_id != user_id,
                    EventReaction.event_id.in_(event_ids),
                )
                .group_by(EventReaction.event_id)
            )
        ).all()
        return {event_id: (likes + 2) / (total + 4) for event_id, likes, total in rows}


class EveningRepository(EveningRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, plan: EveningEntity):
        self._session.add(
            EveningPlan(
                id=plan.id,
                user_id=plan.user_id,
                snapshot=plan.snapshot,
                created_at=plan.created_at,
                saved_at=None,
            )
        )
        await self._session.flush()

    async def get(self, plan_id, user_id):
        row = await self._session.scalar(
            select(EveningPlan).where(
                EveningPlan.id == plan_id, EveningPlan.user_id == user_id
            )
        )
        return evening_from_model(row) if row else None

    async def saved(self, user_id):
        rows = (
            await self._session.scalars(
                select(EveningPlan)
                .where(
                    EveningPlan.user_id == user_id, EveningPlan.saved_at.is_not(None)
                )
                .order_by(EveningPlan.saved_at.desc(), EveningPlan.id)
            )
        ).all()
        return [evening_from_model(row) for row in rows]

    async def save(self, plan_id, user_id, now):
        await self._session.execute(
            update(EveningPlan)
            .where(
                EveningPlan.id == plan_id,
                EveningPlan.user_id == user_id,
                EveningPlan.saved_at.is_(None),
            )
            .values(saved_at=now)
        )
        await self._session.flush()
        return await self.get(plan_id, user_id)
