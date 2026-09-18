from datetime import timedelta
from uuid import UUID

import jwt
from pydantic import ValidationError

from ...service.errors import Unauthorized
from ...service.ports import ClockPort, MaxVerifierPort, TokenPort
from .max_data import validate_init_data
from .mappers import profile_to_identity
from .schemas import MaxProfileDTO


class MaxVerifier(MaxVerifierPort):
    def __init__(self, bot_token: str, clock: ClockPort):
        self._bot_token, self._clock = bot_token, clock

    def verify(self, raw: str):
        profile = validate_init_data(raw, self._bot_token, int(self._clock.now().timestamp()))
        try:
            return profile_to_identity(MaxProfileDTO.model_validate(profile))
        except ValidationError:
            raise Unauthorized('Неверные или устаревшие данные MAX') from None


class JwtTokens(TokenPort):
    def __init__(self, secret: str, clock: ClockPort):
        self._secret, self._clock = secret, clock

    def issue(self, user_id: UUID):
        now = self._clock.now()
        return jwt.encode({'sub': str(user_id), 'iat': now, 'exp': now + timedelta(hours=24)},
                          self._secret, algorithm='HS256')

    def verify(self, token: str):
        try:
            payload = jwt.decode(token, self._secret, algorithms=['HS256'],
                                 options={'require': ['sub', 'exp', 'iat']})
            return UUID(payload['sub'])
        except (jwt.PyJWTError, ValueError, KeyError, TypeError):
            raise Unauthorized('Сессия закончилась. Откройте приложение заново.') from None
