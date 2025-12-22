"""
Pydantic Schemas cho request/response validation
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models import TeamStatus


class TeamRegisterRequest(BaseModel):
    """Request schema cho đăng ký đội"""
    email: EmailStr = Field(..., description="Email liên hệ")
    team_name: str = Field(..., min_length=1, max_length=255, description="Tên đội thi đấu")
    leader_name: str = Field(..., min_length=1, max_length=255, description="Họ và tên đội trưởng")
    leader_student_id: str = Field(..., min_length=1, max_length=50, description="Mã sinh viên đội trưởng")
    phone: str = Field(..., min_length=1, max_length=20, description="Số điện thoại đội trưởng")
    vice_leader_name: str = Field(..., min_length=1, max_length=255, description="Họ và tên đội phó")
    vice_leader_student_id: str = Field(..., min_length=1, max_length=50, description="Mã sinh viên đội phó")
    vice_leader_phone: str = Field(..., min_length=1, max_length=20, description="Số điện thoại đội phó")
    members_list_text: Optional[str] = Field(None, description="Danh sách thành viên (text)")
    amount: Optional[float] = Field(None, description="Số tiền đăng ký (mặc định: 10,000 VND)")


class CreatePaymentRequest(BaseModel):
    """Request schema cho tạo payment link"""
    order_id: str = Field(..., description="Mã đơn hàng")


class TeamResponse(BaseModel):
    """Response schema cho thông tin đội"""
    id: int
    email: Optional[str]
    team_name: str
    leader_name: str
    leader_student_id: Optional[str]
    phone: str
    vice_leader_name: Optional[str]
    vice_leader_student_id: Optional[str]
    vice_leader_phone: Optional[str]
    members_list_file: Optional[str]
    members_list_text: Optional[str]
    order_id: str
    amount: float
    status: TeamStatus
    paid_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RegisterTeamResponse(BaseModel):
    """Response schema cho đăng ký đội thành công"""
    success: bool
    message: str
    data: dict


class CreatePaymentResponse(BaseModel):
    """Response schema cho tạo payment link"""
    success: bool
    message: str
    data: dict


class TeamsListResponse(BaseModel):
    """Response schema cho danh sách đội"""
    success: bool
    data: dict


class MomoIpnRequest(BaseModel):
    """Request schema cho MoMo IPN webhook"""
    partnerCode: str
    orderId: str
    requestId: str
    amount: int
    orderInfo: str
    orderType: str
    transId: str
    resultCode: int
    message: str
    payType: str
    responseTime: int
    extraData: str
    signature: str

