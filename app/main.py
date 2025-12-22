"""
FastAPI Main Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routers import tournament, auth
from app.database import engine, Base, SessionLocal
from app.models import User
from app.services.auth_service import AuthService
from app.middleware import EncryptionMiddleware
import logging

logger = logging.getLogger(__name__)

# Tạo database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup và shutdown events
    - Tự động tạo admin user nếu chưa có
    """
    # Startup
    logger.info("Starting ITISCUP Tournament API...")
    
    # Tự động tạo admin user nếu chưa có
    # Chờ một chút để đảm bảo migration đã chạy xong
    import asyncio
    await asyncio.sleep(2)
    
    db = SessionLocal()
    try:
        admin_username = "admin"
        admin_email = "admin@itiscup.com"
        admin_password = "admin123"  # Đổi mật khẩu sau khi đăng nhập
        admin_full_name = "Administrator"
        
        # Kiểm tra xem column is_admin có tồn tại không bằng raw SQL
        try:
            from sqlalchemy import text
            result = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='is_admin'"))
            column_exists = result.fetchone() is not None
            
            if not column_exists:
                logger.warning("⚠️  Column 'is_admin' does not exist in database.")
                logger.warning("⚠️  Migration might not have run. Please check migration logs.")
                logger.warning("⚠️  Admin user will not be created. Run: alembic upgrade head")
                db.close()
                yield
                return
        except Exception as e:
            # Nếu không phải PostgreSQL hoặc lỗi khác, thử cách khác
            logger.warning(f"⚠️  Could not check column existence: {e}")
            # Vẫn tiếp tục thử tạo admin, nếu lỗi sẽ catch ở dưới
        
        # Kiểm tra xem đã có admin chưa
        try:
            existing_admin = db.query(User).filter(
                (User.username == admin_username) | (User.email == admin_email)
            ).first()
            
            if existing_admin:
                # Nếu user đã tồn tại nhưng chưa phải admin, cập nhật
                if not existing_admin.is_admin:
                    try:
                        existing_admin.is_admin = True
                        db.commit()
                        logger.info(f"✅ Updated user '{existing_admin.username}' to admin")
                    except Exception as e:
                        logger.warning(f"⚠️  Could not update user to admin: {e}")
                        db.rollback()
                else:
                    logger.info(f"✅ Admin user already exists: {admin_username}")
            else:
                # Tạo admin mới
                try:
                    hashed_password = AuthService.get_password_hash(admin_password)
                    admin = User(
                        full_name=admin_full_name,
                        username=admin_username,
                        email=admin_email,
                        hashed_password=hashed_password,
                        is_active=True,
                        is_admin=True
                    )
                    db.add(admin)
                    db.commit()
                    db.refresh(admin)
                    logger.info(f"✅ Created admin user: {admin_username} / {admin_password}")
                    logger.info("⚠️  IMPORTANT: Change admin password after first login!")
                except Exception as e:
                    logger.warning(f"⚠️  Could not create admin user: {e}")
                    db.rollback()
        except Exception as e:
            error_msg = str(e).lower()
            if 'is_admin' in error_msg or 'does not exist' in error_msg or 'undefinedcolumn' in error_msg:
                logger.error(f"❌ Column 'is_admin' does not exist in database.")
                logger.error(f"❌ Please run migration: alembic upgrade head")
                logger.error(f"❌ Error details: {e}")
            else:
                logger.error(f"❌ Error during admin user creation: {e}")
            db.rollback()
    except Exception as e:
        logger.error(f"❌ Unexpected error during startup: {e}")
        if db:
            db.rollback()
    finally:
        if db:
            db.close()
    
    yield
    
    # Shutdown
    logger.info("Shutting down ITISCUP Tournament API...")


# Tạo FastAPI app
app = FastAPI(
    title="ITISCUP Tournament API",
    description="API cho hệ thống đăng ký giải đấu ITISCUP với thanh toán MoMo",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production nên chỉ định domain cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Encryption middleware - MÃ HÓA CHỈ CÁC API HIỂN THỊ THÔNG TIN
# Chỉ encrypt các APIs có thông tin nhạy cảm (email, phone, student_id)
app.add_middleware(
    EncryptionMiddleware,
    encrypted_paths=[
        "/api/tournament/teams",        # Danh sách teams (có email, phone)
        "/api/tournament/my-teams",     # Teams của user (có email, phone)
        "/api/auth/me",                 # Thông tin user (có email)
    ]
)

# Include routers
app.include_router(tournament.router, prefix="/api")
app.include_router(auth.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ITISCUP Tournament API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

