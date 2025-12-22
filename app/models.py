"""
Database Models
"""
from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, Numeric, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class TeamStatus(str, enum.Enum):
    """Trạng thái đội"""
    REGISTERED = "REGISTERED"  # Đã đăng ký, chưa thanh toán
    PAID_CONFIRMED = "PAID_CONFIRMED"  # Đã thanh toán, trong 16 đội
    PAID_REJECTED = "PAID_REJECTED"  # Đã thanh toán nhưng quá suất


class User(Base):
    """
    Model: User
    Quản lý tài khoản đại diện các đội
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    
    # Thông tin cơ bản
    full_name = Column(String(255), nullable=False, comment="Họ và tên")
    username = Column(String(100), unique=True, nullable=False, index=True, comment="Tên đăng nhập")
    email = Column(String(255), unique=True, nullable=False, index=True, comment="Email")
    hashed_password = Column(String(255), nullable=False, comment="Mật khẩu đã hash")
    is_active = Column(Boolean, default=True, nullable=False, comment="Tài khoản có hoạt động không")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationship
    teams = relationship("Team", back_populates="user", cascade="all, delete-orphan")


class Team(Base):
    """
    Model: Team
    Quản lý thông tin các đội đăng ký tham gia giải đấu
    """
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    
    # Thông tin cơ bản
    email = Column(String(255), nullable=True, comment="Email liên hệ")
    team_name = Column(String(255), nullable=False, comment="Tên đội bóng")
    
    # Thông tin đội trưởng
    leader_name = Column(String(255), nullable=False, comment="Tên đội trưởng")
    leader_student_id = Column(String(50), nullable=True, comment="Mã sinh viên đội trưởng")
    phone = Column(String(20), nullable=False, comment="Số điện thoại đội trưởng")
    
    # Thông tin đội phó
    vice_leader_name = Column(String(255), nullable=True, comment="Họ và tên đội phó")
    vice_leader_student_id = Column(String(50), nullable=True, comment="Mã sinh viên đội phó")
    vice_leader_phone = Column(String(20), nullable=True, comment="Số điện thoại đội phó")
    
    # Danh sách thành viên
    members_list_file = Column(String(500), nullable=True, comment="File danh sách thành viên (path)")
    members_list_text = Column(Text, nullable=True, comment="Danh sách thành viên (text backup)")
    
    # Thanh toán
    order_id = Column(String(100), unique=True, nullable=False, index=True, comment="Mã đơn hàng MoMo duy nhất")
    amount = Column(Numeric(10, 2), default=0, nullable=False, comment="Số tiền đăng ký")
    status = Column(
        Enum(TeamStatus, name="team_status", create_type=True),
        default=TeamStatus.REGISTERED,
        nullable=False,
        index=True,
        comment="Trạng thái: REGISTERED=chưa thanh toán, PAID_CONFIRMED=đã thanh toán và trong 16 đội, PAID_REJECTED=đã thanh toán nhưng quá suất"
    )
    paid_at = Column(DateTime(timezone=True), nullable=True, comment="Thời điểm thanh toán thành công")
    
    # Foreign Key
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True, comment="ID đại diện đội (User)")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship
    user = relationship("User", back_populates="teams")

    # Constants
    MAX_CONFIRMED_TEAMS = 16

    def is_confirmed(self) -> bool:
        """Kiểm tra xem đội có phải là một trong 16 đội chính thức không"""
        return self.status == TeamStatus.PAID_CONFIRMED

    def is_paid(self) -> bool:
        """Kiểm tra xem đội đã thanh toán chưa"""
        return self.status in [TeamStatus.PAID_CONFIRMED, TeamStatus.PAID_REJECTED]

    @staticmethod
    def count_confirmed(db):
        """Đếm số lượng đội đã được xác nhận (PAID_CONFIRMED)"""
        from sqlalchemy import func
        return db.query(func.count(Team.id)).filter(Team.status == TeamStatus.PAID_CONFIRMED).scalar()

