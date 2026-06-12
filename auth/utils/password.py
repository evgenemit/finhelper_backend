from pwdlib import PasswordHash
import jwt
from datetime import datetime, timedelta, timezone

from core.config import settings


password_hash = PasswordHash.recommended()
DUMMY_PASSWORD = password_hash.hash('dummypassword')
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = 'HS256'


def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password):
    return password_hash.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
