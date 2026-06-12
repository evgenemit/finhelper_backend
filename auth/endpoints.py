import jwt
from jwt.exceptions import InvalidTokenError
from typing import Annotated
from fastapi.routing import APIRouter
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from core.database import get_db
from core.models import UserPublic, User, Token, UserCreate
from auth.utils.password import verify_password, DUMMY_PASSWORD, SECRET_KEY, \
    ALGORITHM, create_access_token, get_password_hash


router = APIRouter(prefix='/auth')

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/token/')


async def get_user(username: str, session: AsyncSession) -> User | None:
    user = (await session.exec(
        select(User).where(User.username == username)
    )).one_or_none()
    return user


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get('sub')
        if username is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token expired',
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        raise credentials_exception
    user = await get_user(username, session)
    if user is None:
        raise credentials_exception
    return user


async def authenticate_user(
    username: str,
    password: str,
    session: AsyncSession
) -> bool:
    user = await get_user(username, session)
    if not user:
        verify_password(password, DUMMY_PASSWORD)
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return True


@router.post('/token/')
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db)]
) -> Token:
    user = await authenticate_user(form_data.username, form_data.password, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Bearer'}
        )
    access_token = create_access_token(
        data={'sub': form_data.username}
    )
    return Token(access_token=access_token, token_type='bearer')


@router.get('/users/me/', response_model=UserPublic)
async def get_users_me(
    user: Annotated[UserPublic, Depends(get_current_user)]
) -> UserPublic:
    return user


@router.post('/users/', response_model=UserPublic)
async def create_user(
    user_create: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db)]
) -> UserPublic:
    """Создание пользователя"""
    hashed_password = get_password_hash(user_create.password)
    user = await get_user(user_create.username, session)
    if user is None:
        user = User(
            username=user_create.username,
            email=user_create.email,
            hashed_password=hashed_password
        )
    else:
        user.email = user_create.email
        user.hashed_password = hashed_password
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
