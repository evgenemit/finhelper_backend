from pwdlib import PasswordHash
import jwt
from datetime import datetime, timedelta, timezone


password_hash = PasswordHash.recommended()
DUMMY_PASSWORD = password_hash.hash('dummypassword')
SECRET_KEY = 'ccb1ffcfb719e6e6c54814e46d6248b12f39b96045f174c59810f213e01b74be'
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
        expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
