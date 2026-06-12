from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from redis.asyncio import StrictRedis
from langchain_deepseek import ChatDeepSeek

from core.config import settings
from auth.endpoints import router as auth_router
from finances.endpoints import router as fin_router
from agent.endpoints import router as agent_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = ChatDeepSeek(
        model='deepseek-v4-flash',
        api_key=settings.DEEPSEEK_KEY,
        temperature=0.1,
    )
    app.state.redis = StrictRedis(
        host='localhost',
        port=6379,
        decode_responses=True
    )
    yield
    await app.state.redis.aclose()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)
app.include_router(auth_router)
app.include_router(fin_router)
app.include_router(agent_router)
