from collections import Counter
from datetime import timezone
from zoneinfo import ZoneInfo

from .entities import User
from .errors import OnboardingRequired
from .ports import ClockPort, UnitOfWorkPort
from .results import RecommendedEvent
from .sync import EventSyncService


class RecommendationService:
    def __init__(self, uow: UnitOfWorkPort, sync: EventSyncService, clock: ClockPort, provider: str):
        self.uow, self.sync, self.clock, self.provider = uow, sync, clock, provider

    @staticmethod
    def score(event, user, preference, liked, disliked):
        score, reasons = 0, []
        if event.city.casefold() == user.city.casefold():
            score += 5
            reasons.append('В вашем городе')
        if preference:
            if event.category in preference.categories:
                score += 3
                reasons.append('По вашим интересам')
            if preference.budget_max is None or event.is_free or (event.price_min is not None and event.price_min <= preference.budget_max):
                score += 2
                reasons.append('Подходит по бюджету')
            local = event.start_date.replace(tzinfo=event.start_date.tzinfo or timezone.utc).astimezone(ZoneInfo(event.timezone))
            weekend = local.weekday() >= 5
            if preference.preferred_days == 'any' or (preference.preferred_days == 'weekends' and weekend) or (preference.preferred_days == 'weekdays' and not weekend):
                score += 1
            period = 'morning' if local.hour < 12 else 'day' if local.hour < 18 else 'evening'
            if preference.preferred_time in {'any', period}:
                score += 1
            if preference.companion in {'family', 'children'} and 'family' in event.tags:
                score += 2
                reasons.append('Для всей семьи')
        score += min(liked[event.category], 3) * 2 - min(disliked[event.category], 3) * 2
        if liked[event.category]:
            reasons.append('Похоже на то, что вам нравится')
        return score, reasons


    async def get(self, user: User, limit: int) -> list[RecommendedEvent]:
        if not user.onboarding_completed:
            raise OnboardingRequired('Сначала заполните анкету')
        await self.sync.ensure(user.city)
        preference = await self.uow.preferences.get(user.id)
        history = await self.uow.reactions.history(user.id)
        liked = Counter(row.category for row in history if row.reaction == 'like')
        disliked = Counter(row.category for row in history if row.reaction == 'dislike')
        seen = {row.event_id for row in history}
        events = await self.uow.events.available(user.city, self.provider, self.clock.now())
        ranked = [(event, *self.score(event, user, preference, liked, disliked))
                  for event in events if event.id not in seen]
        ranked.sort(key=lambda row: (-row[1], row[0].start_date, str(row[0].id)))
        return [RecommendedEvent(event=event, reasons=tuple(reasons))
                for event, _, reasons in ranked[:limit]]
