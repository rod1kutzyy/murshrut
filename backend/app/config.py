from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'postgresql+asyncpg://postgres:postgres@localhost:5432/events'
    jwt_secret: str = 'local-demo-secret-change-before-production-32'
    max_bot_token: str = ''
    max_bot_name: str = ''
    demo_mode: bool = False
    event_provider: str = 'culture'
    culture_api_key: str = ''
    culture_api_url: str = 'https://pro.culture.ru/api/2.5/'
    culture_events_path: str = 'pushkinsCardEvents'
    sync_interval_seconds: int = 1800
    admin_sync_token: str = ''

    def validate_runtime(self):
        if self.event_provider not in {'demo', 'culture'}:
            raise RuntimeError('EVENT_PROVIDER must be demo or culture')
        if not self.demo_mode and (len(self.jwt_secret) < 32 or self.jwt_secret.startswith('local-demo') or not self.max_bot_token):
            raise RuntimeError('Production requires MAX_BOT_TOKEN and a unique JWT_SECRET (32+ characters)')
        if self.event_provider == 'culture' and not self.culture_api_key:
            raise RuntimeError('Culture provider requires CULTURE_API_KEY; use EVENT_PROVIDER=demo locally')

@lru_cache
def get_settings():
    return Settings()
