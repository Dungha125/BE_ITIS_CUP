"""
Router: My Teams
Xử lý các API liên quan đến đội của user hiện tại
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Team
from app.schemas import TeamResponse
from app.routers.auth import get_current_user_id

router = APIRouter(prefix="/my-teams", tags=["My Teams"])


@router.get("/", response_model=List[TeamResponse])
async def get_my_teams(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Lấy danh sách đội của user hiện tại
    GET /api/my-teams/
    """
    teams = db.query(Team).filter(Team.user_id == user_id).all()
    return teams


@router.get("/{team_id}/payment-link")
async def get_payment_link(
    team_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Lấy payment link của đội (chỉ user sở hữu đội mới được lấy)
    GET /api/my-teams/{team_id}/payment-link
    """
    team = db.query(Team).filter(Team.id == team_id, Team.user_id == user_id).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Không tìm thấy đội")
    
    # Nếu chưa có payment link, tạo mới
    if not team.payment_url:
        from app.services.momo_service import MomoService
        momo_service = MomoService()
        
        order_info = f"Đăng ký giải đấu ITISCUP - {team.team_name}"
        payment_data = momo_service.create_payment_link(
            team.order_id,
            int(team.amount),
            order_info,
            f'{{"team_id": {team.id}}}'
        )
        
        if payment_data:
            team.payment_url = payment_data.get("payUrl")
            team.qr_code_url = payment_data.get("qrCodeUrl")
            db.commit()
            db.refresh(team)
    
    return {
        "success": True,
        "data": {
            "payment_url": team.payment_url,
            "qr_code_url": team.qr_code_url,
            "order_id": team.order_id,
            "amount": float(team.amount),
        }
    }

