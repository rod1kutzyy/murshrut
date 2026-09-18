import hashlib
import hmac
import json
from urllib.parse import urlencode
import pytest
from app.service.errors import Unauthorized
from app.transport.integrations.max_data import validate_init_data

TOKEN = 'test-bot-token'
NOW = 1800000000

def signed(**extra):
    data = {'auth_date': str(NOW), 'user': json.dumps({'id': 42, 'first_name': 'Тест & = +'}), **extra}
    secret = hmac.new(b'WebAppData', TOKEN.encode(), hashlib.sha256).digest()
    check = '\n'.join(f'{k}={v}' for k, v in sorted(data.items()))
    data['hash'] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)

def test_valid_signature_and_unicode():
    assert validate_init_data(signed(), TOKEN, NOW)['first_name'] == 'Тест & = +'

@pytest.mark.parametrize('raw', [signed().replace('42', '43'), signed() + '&auth_date=1800000000', signed(auth_date=str(NOW - 3601)), signed(auth_date=str(NOW + 100)), 'user=x&hash=bad', signed(user='null')])
def test_invalid_init_data_rejected(raw):
    with pytest.raises(Unauthorized) as exc:
        validate_init_data(raw, TOKEN, NOW)
    assert str(exc.value) == 'Неверные или устаревшие данные MAX'
