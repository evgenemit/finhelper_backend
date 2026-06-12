import json
from typing import Sequence, Annotated
from fastapi import Request, Depends
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from redis.asyncio import StrictRedis

from langchain_deepseek import ChatDeepSeek
from langchain.agents import create_agent
from langchain.tools import tool, BaseTool

from auth.endpoints import get_current_user
from core.database import get_db
from core.models import User, Category, Transaction


class LLMAgent:

    def __init__(
        self,
        model: ChatDeepSeek,
        tools: Sequence[BaseTool],
        system_prompt: str
    ) -> None:
        self._model = model
        self._agent = create_agent(
            model=self._model,
            tools=tools,
            system_prompt=system_prompt,
        )

    async def ainvoke(self, messages: list = []):
        response = await self._agent.ainvoke({
            'messages': messages
        })
        return response['messages'][-1].content


async def get_agent(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):

    @tool
    async def get_categories():
        """
        Получить список существующих категорий расходов пользователя.
    
        Returns:
            list[tuple[int, str]]: Список категорий в формате [(id, name), ...]
        
        Важно:
            НЕ создавай новые категории. НЕ предлагай создать.
            Используй ТОЛЬКО id из этого списка для create_transaction и update_transaction.
        """
        stmt = select(Category.id, Category.name).where(Category.user_id == user.id)
        categories = await session.exec(stmt)
        return categories.all()

    @tool
    async def create_transaction(text: str, amount: Decimal, category_id: int):
        """
        СОЗДАТЬ ТРАНЗАКЦИЮ (реальное сохранение расхода).
    
        Args:
            text (str): Описание расхода (например "кофе", "такси", "продукты")
            amount (Decimal): Сумма расхода. ТОЛЬКО число, до 2 знаков после запятой. БЕЗ символов валют.
            category_id (int): ID категории из get_categories(). НЕ МОЖЕТ быть None.
        
        Важно:
            Ты ОБЯЗАН вызвать эту функцию, чтобы реально добавить расход.
            НЕ пиши «добавил», «сохранил», «ок» без вызова этой функции.
        """
        transaction = Transaction(
            text=text,
            amount=amount,
            category_id=category_id
        )
        session.add(transaction)

    @tool
    async def get_transactions(
        user_id: int = user.id,
        month: int | None = None,
        year: int | None = None
    ):
        """
        Получить транзакции пользователя за месяц.
    
        Args:
            user_id (int): ID пользователя.
            month (int | None): Номер месяца (1 = январь, 12 = декабрь). Если None — не подставляй сам, функция использует текущий.
            year (int | None): Год (например 2025). Если None — не подставляй сам, функция использует текущий.
        
        Важно:
            Если пользователь сказал «покажи за май 2025» → month=5, year=2025 (месяц ЧИСЛОМ, НЕ текстом).
            Если пользователь НЕ указал месяц и год — оставь month=None, year=None.
        """
        month = month or datetime.now().month
        year = year or datetime.now().year

        start_day = datetime(year, month, 1)
        if month < 12:
            last_day = datetime(year, month + 1, 1)
        else:
            last_day = datetime(year + 1, 1, 1)
        stmt = select(Transaction).where(
            Transaction.category_id.in_(
                select(Category.id).where(Category.user_id == user_id)
            ),
            Transaction.created_at >= start_day,
            Transaction.created_at < last_day
        )
        transactions = (await session.exec(stmt)).all()
        return transactions

    @tool
    async def update_transaction(
        transaction_id: int,
        category_id: int | None = None,
        text: str | None = None,
        amount: Decimal | None = None
    ) -> None:
        """
        ОБНОВИТЬ ТРАНЗАКЦИЮ (изменить одно или несколько полей).
    
        Args:
            transaction_id (int): ID транзакции (обязательный).
            category_id (int | None): Новый ID категории (из get_categories). Передавай ТОЛЬКО если нужно изменить.
            text (str | None): Новый текст описания. Передавай ТОЛЬКО если нужно изменить.
            amount (Decimal | None): Новая сумма (только число, без валют). Передавай ТОЛЬКО если нужно изменить.
        
        Важно:
            Передавай ТОЛЬКО те параметры, которые нужно изменить.
            Остальные параметры должны быть None (или не переданы).
            Например: update_transaction(transaction_id=5, amount=200) — изменит только сумму.
        """
        stmt = select(Transaction).where(Transaction.id == transaction_id)
        transaction = (await session.exec(stmt)).one_or_none()
        if category_id:
            transaction.category_id = category_id
        if text:
            transaction.text = text
        if amount:
            transaction.amount = amount
        session.add(transaction)

    agent = LLMAgent(
        request.app.state.model,
        [
            get_categories,
            get_transactions,
            create_transaction,
            update_transaction
        ],
        """
        Ты — дружелюбный ассистент по учёту расходов в Telegram. Твоя задача — строго выполнять действия через инструменты (tools), а НЕ имитировать их.

        Правила поведения

        1. НЕ симулируй создание, изменение или получение транзакций.
        Если пользователь просит записать расход — ты ОБЯЗАН вызвать create_transaction.
        Если НЕ вызвал — считай, что ничего не сделано. НЕ пиши «я добавил», если НЕ вызвал функцию.

        2. Категории:
        Ты можешь только использовать существующие категории (получаешь через get_categories).
        НЕ создавай новые. НЕ предлагай создать.
        НЕ назначай случайную категорию, если подходящей нет.
        НИКОГДА не показывай id категорий пользователю.

        3. Суммы:
        Все суммы — число с максимум 2 знаками после запятой.
        НЕ используй символы валют. Только число.

        4. Формат ответа:
        Отвечай дружелюбно, коротко (1 фраза, максимум 2), с 1-2 уместными эмодзи.
        НЕ используй markdown: **, *, _, `, -, 1., #.
        НЕ используй списки, заголовки, код, таблицы.
        Только plain text + эмодзи.

        5. Ответы на разные случаи:

        Если пользователь назвал трату без суммы:
        → «Сколько потратил на [что]? 💸»
        Пример: пиццу купил → «Сколько потратил на пиццу? 🍕💸»

        Если пользователь назвал сумму после уточнения:
        → «✅ Ок, добавил: [сумма] на [что]»

        Если несколько трат одной суммой:
        → «✅ Добавил: [сумма1] на [что1], [сумма2] на [что2]»

        Если категория не подходит:
        → «Нет категории для [что] 😕 Выбери из: категории через запятую»

        Если спросил статистику:
        → «За [месяц] потратил: [список трат кратко]. Всего [сумма] 💰»

        Если пользователь спрашивает "что я могу" или "помощь":
        → «Просто напиши трату, например: кофе 150 ☕»

        6. Запрещено показывать: id, технические детали, слова «функция», «tool», «вызов», «БД».

        Примеры:

        Пользователь: пиццу купил
        Агент: Сколько потратил на пиццу? 🍕💸

        Пользователь: 500
        Агент: (вызывает create_transaction) → ✅ Ок, добавил: 500 на пиццу 🍕

        Пользователь: кола 60, чипсы 35
        Агент: ✅ Добавил: 60 на кола, 35 на чипсы 🥤

        Пользователь: покажи расходы
        Агент: За этот месяц: кофе 150, пицца 500. Всего 650 💰
        """
    )
    agent._session = session
    return agent


async def get_messages(
    user_id: int,
    redis: StrictRedis
) -> list[dict]:
    messages = await redis.lrange(f'message:{user_id}', 0, -1)
    return [json.loads(i) for i in messages]


async def add_message(
    msg: str,
    role: str,
    user_id: int,
    redis: StrictRedis
) -> None:
    message = {'role': role, 'content': msg}
    await redis.rpush(f'message:{user_id}', json.dumps(message))
    await redis.expire(f'message:{user_id}', 600)
