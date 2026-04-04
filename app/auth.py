from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Request, Depends
from sqlalchemy.orm import Session

from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.database import get_db
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class NotAuthenticated(Exception):
    """Raised when user is not authenticated."""
    pass


class InsufficientPermissions(Exception):
    """Raised when user lacks required permissions."""
    pass


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """FastAPI dependency: extracts and validates user from JWT cookie."""
    token = request.cookies.get("access_token")
    if not token:
        raise NotAuthenticated()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise NotAuthenticated()
    except JWTError:
        raise NotAuthenticated()

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise NotAuthenticated()
    return user


def get_current_user_optional(request: Request, db: Session) -> Optional[User]:
    """Get current user without raising - returns None if not authenticated."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            return None
        return db.query(User).filter(User.id == user_id).first()
    except JWTError:
        return None


def require_role(*roles):
    """FastAPI dependency factory: ensures user has one of the specified roles."""
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise InsufficientPermissions()
        return current_user
    return role_checker
