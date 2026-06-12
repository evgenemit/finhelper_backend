from typing import Annotated
from fastapi import APIRouter, Depends
from redis.asyncio import StrictRedis

from agent.utils.llm_agent import LLMAgent, get_agent, get_messages, add_message
from core.database import get_redis
from core.models import User
from auth.endpoints import get_current_user


router = APIRouter(prefix='/agent')


@router.get('/')
async def agent(
    msg: str,
    agent: Annotated[LLMAgent, Depends(get_agent)],
    redis: Annotated[StrictRedis, Depends(get_redis)],
    user: Annotated[User, Depends(get_current_user)]
):
    await add_message(msg, 'user', user.id, redis)
    messages = await get_messages(user.id, redis)
    answer = await agent.ainvoke(messages)
    await add_message(answer, 'assistant', user.id, redis)
    await agent._session.commit()
    return {'answer': answer}
