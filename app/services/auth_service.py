"""
Service: AuthService
Xử lý authentication và authorization
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.models import User
import os
from dotenv import load_dotenv

load_dotenv()

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Password hashing - Dùng Argon2 thay vì bcrypt (không giới hạn 72 bytes)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class AuthService:
    """Service xử lý authentication"""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Xác thực mật khẩu"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash mật khẩu"""
        # Argon2 không có giới hạn 72 bytes như bcrypt
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Tạo JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Xác thực JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Lấy user theo username hoặc email"""
        user = db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        return user

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Lấy user theo ID"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def create_user(
        db: Session,
        full_name: str,
        username: str,
        email: str,
        password: str
    ) -> User:
        """Tạo user mới"""
        # Kiểm tra username đã tồn tại chưa
        if db.query(User).filter(User.username == username).first():
            raise ValueError("Username đã tồn tại")
        
        # Kiểm tra email đã tồn tại chưa
        if db.query(User).filter(User.email == email).first():
            raise ValueError("Email đã tồn tại")

        # Hash password
        hashed_password = AuthService.get_password_hash(password)

        # Tạo user
        user = User(
            full_name=full_name,
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        """Xác thực user"""
        user = AuthService.get_user_by_username(db, username)
        if not user:
            return None
        if not AuthService.verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user

