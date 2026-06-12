from fastapi import Request
from redis.asyncio import StrictRedis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from core.config import settings


engine = create_async_engine(settings.database_url)
session_maker = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    async with session_maker() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e


async def get_redis(request: Request) -> StrictRedis:
    return request.app.state.redis
