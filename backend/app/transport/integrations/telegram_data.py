import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from ...service.errors import Unauthorized


def validate_init_data(raw: str, bot_token: str, now: int | None = None) -> dict:
    """Validate Telegram Mini App init data using the Bot API algorithm."""
    try:
        pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True)
        if not pairs or len({key for key, _ in pairs}) != len(pairs):
            raise ValueError("duplicate parameters")

        data = dict(pairs)
        received_hash = data.pop("hash")
        data_check_string = "\n".join(
            f"{key}={value}" for key, value in sorted(data.items())
        )
        secret_key = hmac.new(
            b"WebAppData", bot_token.encode(), hashlib.sha256
        ).digest()
        expected_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()
        if not bot_token or not hmac.compare_digest(expected_hash, received_hash):
            raise ValueError("signature")

        age = (int(time.time()) if now is None else now) - int(data["auth_date"])
        if age < -30 or age > 3600:
            raise ValueError("expired")

        user = json.loads(data["user"])
        if (
            not isinstance(user, dict)
            or type(user.get("id")) is not int
            or user["id"] <= 0
            or user["id"] > 9_007_199_254_740_991
        ):
            raise ValueError("user")
        return user
    except (ValueError, KeyError, TypeError, OverflowError):
        raise Unauthorized("Неверные или устаревшие данные Telegram") from None
