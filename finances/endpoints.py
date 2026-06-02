from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, and_, desc
from typing import Annotated
from datetime import datetime

from core.database import get_db
from auth.endpoints import get_current_user
from core.models import Transaction, User, CategoryBase, Category, \
    CategoryPublic, CategoryDetailPublic, TransactionCreate, TransactionPublic


router = APIRouter()


@router.get('/categories/', response_model=list[CategoryPublic])
async def get_user_categories(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
) -> list[CategoryPublic]:
    stmt = select(Category).where(Category.user_id == user.id)
    return (await session.exec(stmt)).all()


@router.get('/finances/', response_model=list[CategoryDetailPublic])
async def get_detail_finances(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    month: int | None = None,
    year: int | None = None
) -> list[CategoryDetailPublic]:
    month = month or datetime.now().month
    year = year or datetime.now().year

    if month < 12:
        last_day = datetime(year, month + 1, 1)
    else:
        last_day = datetime(year + 1, 1, 1)
    conditions = [
        Transaction.category_id == Category.id,
        Transaction.created_at >= datetime(year, month, 1),
        Transaction.created_at < last_day
    ]

    stmt = select(
        Category, func.coalesce(func.sum(Transaction.amount), 0).label('total')
    ).where(Category.user_id == user.id).outerjoin(
        Transaction, and_(*conditions)
    ).group_by(Category.id).order_by(desc('total')).options(
        selectinload(Category.transactions.and_(*conditions))
    )
    category_amount = await session.exec(stmt)
    return [
        CategoryDetailPublic(
            id=cat.id,
            name=cat.name,
            amount=amount,
            transactions=cat.transactions
        )
        for cat, amount in category_amount.all()
    ]


@router.post('/categories/', response_model=CategoryPublic)
async def create_category(
    category_base: CategoryBase,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
) -> CategoryPublic:
    category = Category(
        name=category_base.name,
        user=user
    )
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


@router.get('/categories/{category_id}/', response_model=CategoryDetailPublic)
async def get_category(
    category_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    month: int | None = None,
    year: int | None = None
) -> CategoryDetailPublic:
    month = month or datetime.now().month
    year = year or datetime.now().year
    if month < 12:
        end_date = datetime(year, month + 1, 1)
    else:
        end_date = datetime(year + 1, 1, 1)
    start_date = datetime(year, month, 1)

    stmt = select(
        Category
    ).where(
        Category.user_id == user.id,
        Category.id == category_id
    ).options(
        selectinload(Category.transactions.and_(
            Transaction.created_at >= start_date,
            Transaction.created_at < end_date
        ))
    )
    category = (await session.exec(stmt)).one_or_none()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Category not found'
        )
    amount = sum((tr.amount for tr in category.transactions))
    return CategoryDetailPublic(
        id=category.id,
        name=category.name,
        amount=amount,
        transactions=category.transactions,
    )


@router.post('/transactions/', response_model=TransactionPublic)
async def create_transaction(
    transaction_data: TransactionCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
) -> TransactionPublic:
    stmt = select(Category).where(
        Category.user_id == user.id,
        Category.id == transaction_data.category_id
    )
    result = (await session.exec(stmt)).one_or_none()
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Category not found'
        )

    transaction = Transaction(
        text=transaction_data.text,
        amount=transaction_data.amount,
        category_id=transaction_data.category_id,
    )
    session.add(transaction)
    await session.commit()
    await session.refresh(transaction)
    return transaction
