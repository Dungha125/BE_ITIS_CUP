"""
Router: Authentication
Xử lý đăng ký và đăng nhập
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models import User
from app.services.auth_service import AuthService
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    RegisterResponse,
    LoginResponse,
    TokenResponse,
    UserResponse
)
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Đăng ký tài khoản mới
    POST /api/auth/register
    """
    try:
        # Tạo user
        user = AuthService.create_user(
            db=db,
            full_name=request.full_name,
            username=request.username,
            email=request.email,
            password=request.password
        )

        return RegisterResponse(
            success=True,
            message="Đăng ký thành công",
            data=UserResponse(
                id=user.id,
                full_name=user.full_name,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                is_admin=getattr(user, 'is_admin', False),
                created_at=user.created_at,
                updated_at=user.updated_at
            )
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Có lỗi xảy ra khi đăng ký"
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Đăng nhập
    POST /api/auth/login
    """
    # Xác thực user
    user = AuthService.authenticate_user(
        db=db,
        username=request.username,
        password=request.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không đúng",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Tạo access token
    access_token = AuthService.create_access_token(
        data={"sub": str(user.id), "username": user.username}
    )

    return LoginResponse(
        success=True,
        message="Đăng nhập thành công",
        data=TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user.id,
                full_name=user.full_name,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                is_admin=getattr(user, 'is_admin', False),
                created_at=user.created_at,
                updated_at=user.updated_at
            )
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin user hiện tại
    GET /api/auth/me
    """
    # Xác thực token
    payload = AuthService.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Lấy user
    user_id = int(payload.get("sub"))
    user = AuthService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy user"
        )

    return UserResponse(
        id=user.id,
        full_name=user.full_name,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_admin=getattr(user, 'is_admin', False),  # Lấy is_admin từ user, default False nếu chưa có
        created_at=user.created_at,
        updated_at=user.updated_at
    )


async def get_current_user_id_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[int]:
    """
    Dependency để lấy user_id từ token (optional - không bắt buộc phải đăng nhập)
    """
    if not token:
        return None
    payload = AuthService.verify_token(token)
    if not payload:
        return None
    return int(payload.get("sub"))


def get_current_user_id(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> int:
    """
    Dependency để lấy user_id từ token
    """
    payload = AuthService.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ"
        )
    return int(payload.get("sub"))


async def get_current_admin_user(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency để kiểm tra user có phải admin không
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy user"
        )
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập. Chỉ admin mới có quyền này."
        )
    return user

