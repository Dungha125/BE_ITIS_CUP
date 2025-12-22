"""
Database Configuration
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Database URL từ environment variable
# Railway sẽ tự động set DATABASE_URL cho PostgreSQL
# Development: SQLite
# Production: PostgreSQL từ Railway
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./tournament.db"
)

# Convert Railway PostgreSQL URL nếu cần (Railway dùng postgres://, SQLAlchemy cần postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Tạo engine
engine = create_engine(DATABASE_URL, echo=False)

# Tạo SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class cho models
Base = declarative_base()


def get_db():
    """
    Dependency để lấy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

