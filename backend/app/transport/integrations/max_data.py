import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl
from ...service.errors import Unauthorized


def validate_init_data(raw: str, bot_token: str, now: int | None = None) -> dict:
    try:
        pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True)
        if not pairs or len({k for k, _ in pairs}) != len(pairs):
            raise ValueError('duplicate parameters')
        data = dict(pairs)
        signature = data.pop('hash')
        check = '\n'.join(f'{k}={v}' for k, v in sorted(data.items()))
        secret = hmac.new(b'WebAppData', bot_token.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not bot_token or not hmac.compare_digest(expected, signature):
            raise ValueError('signature')
        age = (int(time.time()) if now is None else now) - int(data['auth_date'])
        if age < -30 or age > 3600:
            raise ValueError('expired')
        user = json.loads(data['user'])
        if not isinstance(user, dict) or type(user.get('id')) is not int or user['id'] <= 0 or user['id'] > 9223372036854775807:
            raise ValueError('user')
        return user
    except (ValueError, KeyError, TypeError, OverflowError):
        raise Unauthorized('Неверные или устаревшие данные MAX') from None
