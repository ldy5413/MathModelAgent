from sqlmodel import select
from dependency import SessionDep
from models import User
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from datetime import timedelta, datetime, timezone
from jose import jwt


# jwt 配置
ALGORITHM = "HS256"
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"


#  密码加密工具🔐
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  # 密码加密
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # 认证


# 验证用户:数据库中是否存在该用户
async def authenticate_user(db: SessionDep, username: str, password: str):
    user = db.exec(select(User).where(User.account == username)).first()
    if not user:
        return False
    if not verify_password(password, user.password):
        print(user)
        return False
    return user


# 验证密码
def verify_password(plain_password: str, hashed_password: str):
    return plain_password == hashed_password


# 创建访问令牌
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expires_delta = datetime.now(timezone.utc) + expires_delta
    else:
        expires_delta = datetime.now(timezone.utc) + timedelta(
            minutes=15
        )  # 默认过期时间 15分钟
    to_encode.update({"exp": expires_delta})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# 验证token,是否有效
async def authenticate_token(db: SessionDep, token: str):
    try:
        # 解码令牌
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # 获取用户账号
        username = payload.get("sub")
        if username is None:
            return False
        # 验证用户是否存在
        user = db.exec(select(User).where(User.account == username)).first()
        if not user:
            return False
        return user
    except jwt.JWTError:
        return False
