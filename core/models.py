from decimal import Decimal
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import func


class UserBase(SQLModel):
    username: str = Field(unique=True)


class User(UserBase, table=True):
    __tablename__ = 'users'

    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str

    categories: list['Category'] = Relationship(
        back_populates='user',
        cascade_delete=True
    )


class UserPublic(UserBase):
    id: int


class UserCreate(UserBase):
    password: str


class UserUpdate(UserBase):
    username: str | None = None
    password: str | None = None
    new_password: str | None = None


class Token(SQLModel):
    access_token: str
    token_type: str


class CategoryBase(SQLModel):
    name: str


class Category(CategoryBase, table=True):
    __tablename__ = 'categories'

    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key='users.id', ondelete='CASCADE')

    user: User = Relationship(back_populates='categories')
    transactions: list['Transaction'] = Relationship(
        back_populates='category',
        sa_relationship_kwargs={'order_by': 'Transaction.created_at.desc()'},
        cascade_delete=True
    )


class CategoryPublic(CategoryBase):
    id: int


class CategoryDetailPublic(CategoryBase):
    id: int
    amount: Decimal = Field(default=0, max_digits=7, decimal_places=2)
    transactions: list['TransactionPublic']


class TransactionBase(SQLModel):
    text: str
    amount: Decimal = Field(default=0, max_digits=6, decimal_places=2)


class Transaction(TransactionBase, table=True):
    __tablename__ = 'transactions'

    id: int = Field(primary_key=True)
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column_kwargs={'server_default': func.now()}
    )
    category_id: int = Field(foreign_key='categories.id', ondelete='CASCADE')

    category: Category = Relationship(back_populates='transactions')


class TransactionPublic(TransactionBase):
    id: int
    created_at: datetime


class TransactionCreate(TransactionBase):
    category_id: int
