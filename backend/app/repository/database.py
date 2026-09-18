from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from ..config import get_settings

engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
Session = async_sessionmaker(engine, expire_on_commit=False)

