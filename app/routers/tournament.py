"""
Router: Tournament
Xử lý các API liên quan đến đăng ký giải đấu và thanh toán MoMo
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import time
import secrets
import os
import logging

from app.database import get_db
from app.models import Team, TeamStatus
# Import from schemas.py file (now no conflict with schemas package)
from app.schemas import (
    RegisterTeamResponse,
    CreatePaymentResponse,
    TeamsListResponse,
    CreatePaymentRequest,
)
from app.services.momo_service import MomoService
from app.routers.auth import get_current_user_id_optional, get_current_user_id
from typing import Optional

router = APIRouter(prefix="/tournament", tags=["tournament"])
momo_service = MomoService()
logger = logging.getLogger(__name__)


@router.post("/register", response_model=RegisterTeamResponse)
async def register_team(
    email: str = Form(...),
    team_name: str = Form(...),
    leader_name: str = Form(...),
    leader_student_id: str = Form(...),
    phone: str = Form(...),
    vice_leader_name: str = Form(...),
    vice_leader_student_id: str = Form(...),
    vice_leader_phone: str = Form(...),
    members_list_text: Optional[str] = Form(None),
    amount: Optional[float] = Form(None),  # Optional, sẽ set mặc định nếu không có
    members_list_file: Optional[UploadFile] = File(None),
    user_id: Optional[int] = Depends(get_current_user_id_optional),  # Optional: có thể đăng ký không cần login
    db: Session = Depends(get_db),
):
    """
    Đăng ký đội mới
    POST /api/tournament/register
    
    Lưu ý: Mỗi tài khoản chỉ được đăng ký 1 đội duy nhất
    """
    try:
        # Kiểm tra nếu user đã đăng nhập, chỉ cho phép 1 đội/user
        if user_id:
            existing_team = db.query(Team).filter(Team.user_id == user_id).first()
            if existing_team:
                raise HTTPException(
                    status_code=400,
                    detail="Mỗi tài khoản chỉ được đăng ký 1 đội duy nhất. Bạn đã có đội đăng ký rồi."
                )
        
        # Tạo orderId duy nhất: timestamp + random string
        order_id = f"ITIS_{int(time.time())}_{secrets.token_hex(4)}"

        # Xử lý file upload nếu có
        members_list_file_path = None
        if members_list_file:
            # Tạo thư mục nếu chưa có
            upload_dir = "storage/teams/members"
            os.makedirs(upload_dir, exist_ok=True)

            # Lưu file
            file_extension = members_list_file.filename.split(".")[-1]
            file_name = f"members_{order_id}_{int(time.time())}.{file_extension}"
            file_path = os.path.join(upload_dir, file_name)

            with open(file_path, "wb") as f:
                content = await members_list_file.read()
                f.write(content)

            members_list_file_path = file_path

        # Số tiền cố định: 10.000 VND
        fixed_amount = 10000.0
        if amount is not None:
            fixed_amount = float(amount)

        # Tạo đội mới với trạng thái REGISTERED
        team = Team(
            email=email,
            team_name=team_name,
            leader_name=leader_name,
            leader_student_id=leader_student_id,
            phone=phone,
            vice_leader_name=vice_leader_name,
            vice_leader_student_id=vice_leader_student_id,
            vice_leader_phone=vice_leader_phone,
            members_list_file=members_list_file_path,
            members_list_text=members_list_text,
            order_id=order_id,
            amount=fixed_amount,
            status=TeamStatus.REGISTERED,
            user_id=user_id,  # Link với user nếu có đăng nhập
        )

        db.add(team)
        db.commit()
        db.refresh(team)

        # Tự động tạo payment link ngay sau khi đăng ký
        # Link này sẽ được lưu để user có thể thanh toán sau
        pay_url = None
        qr_code_url = None
        
        try:
            order_info = f"Đăng ký giải đấu ITISCUP - {team.team_name}"
            # Tạo return URL động dựa trên origin của request
            return_url = os.getenv('MOMO_RETURN_URL', 'http://localhost:3000/itiscup/payment/callback')
            
            logger.info(f"Creating payment link for team {team.id}, order_id: {team.order_id}, amount: {team.amount}")
            payment_data = momo_service.create_payment_link(
                team.order_id,
                int(team.amount),
                order_info,
                f'{{"team_id": {team.id}}}',
                return_url=return_url
            )
            
            if payment_data:
                pay_url = payment_data.get("payUrl")
                qr_code_url = payment_data.get("qrCodeUrl")
                logger.info(f"Payment link created successfully: pay_url={pay_url is not None}, qr_code_url={qr_code_url is not None}")
            else:
                logger.warning(f"Failed to create payment link for team {team.id}")
        except Exception as e:
            logger.error(f"Error creating payment link: {str(e)}", exc_info=True)
            # Không fail registration nếu không tạo được payment link
            # User có thể tạo lại sau qua endpoint /create-payment

        response_data = {
            "team_id": team.id,
            "order_id": team.order_id,
            "status": team.status.value,
        }
        
        # Thêm payment link nếu có
        if pay_url:
            response_data["pay_url"] = pay_url
        if qr_code_url:
            response_data["qr_code_url"] = qr_code_url
        
        logger.info(f"Team registration successful: team_id={team.id}, order_id={team.order_id}, has_pay_url={pay_url is not None}")
        
        return RegisterTeamResponse(
            success=True,
            message="Đăng ký đội thành công",
            data=response_data,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Register Team Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Có lỗi xảy ra khi đăng ký đội"
        )


@router.post("/create-payment", response_model=CreatePaymentResponse)
async def create_momo_payment(
    request: CreatePaymentRequest,
    db: Session = Depends(get_db),
):
    """
    Tạo payment link MoMo với order_id mới mỗi lần gọi
    POST /api/tournament/create-payment
    
    Mỗi lần gọi sẽ tạo order_id mới để đảm bảo payment link luôn mới
    """
    try:
        # Tìm đội theo order_id (order_id cũ từ request)
        team = db.query(Team).filter(Team.order_id == request.order_id).first()

        if not team:
            raise HTTPException(status_code=404, detail="Không tìm thấy đội")

        # Kiểm tra xem đội đã thanh toán chưa
        if team.is_paid():
            raise HTTPException(
                status_code=400,
                detail="Đội này đã thanh toán rồi"
            )

        # Kiểm tra xem đã đủ 16 đội chưa
        confirmed_count = Team.count_confirmed(db)
        if confirmed_count >= Team.MAX_CONFIRMED_TEAMS:
            raise HTTPException(
                status_code=400,
                detail="Đã đủ 16 đội. Giải đấu đã chốt danh sách."
            )

        # TẠO ORDER_ID MỚI mỗi lần thanh toán
        new_order_id = f"ITIS_{int(time.time())}_{secrets.token_hex(4)}"
        
        # Cập nhật order_id mới vào database
        team.order_id = new_order_id
        db.commit()
        db.refresh(team)
        
        logger.info(f"Created new order_id for team {team.id}: {new_order_id}")

        # Tạo orderInfo
        order_info = f"Đăng ký giải đấu ITISCUP - {team.team_name}"
        
        # Tạo return URL động
        return_url = os.getenv('MOMO_RETURN_URL', 'http://localhost:3000/itiscup/payment/callback')

        # Tạo payment link từ MoMo với order_id mới
        payment_data = momo_service.create_payment_link(
            new_order_id,  # Sử dụng order_id mới
            int(team.amount),
            order_info,
            f'{{"team_id": {team.id}}}',
            return_url=return_url
        )

        if not payment_data:
            raise HTTPException(
                status_code=500,
                detail="Không thể tạo link thanh toán. Vui lòng thử lại sau."
            )

        return CreatePaymentResponse(
            success=True,
            message="Tạo link thanh toán thành công",
            data={
                "pay_url": payment_data.get("payUrl"),
                "qr_code_url": payment_data.get("qrCodeUrl"),
                "deeplink": payment_data.get("deeplink"),
                "order_id": new_order_id,  # Trả về order_id mới
                "amount": int(team.amount),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Create MoMo Payment Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Có lỗi xảy ra khi tạo link thanh toán"
        )


@router.post("/momo-ipn")
async def momo_ipn(
    data: dict,
    db: Session = Depends(get_db),
):
    """
    Xử lý IPN webhook từ MoMo
    POST /api/tournament/momo-ipn

    QUAN TRỌNG: Xử lý race condition với database transaction và SELECT FOR UPDATE
    - Sử dụng database transaction
    - Lock row khi đếm số đội PAID_CONFIRMED
    - Chỉ 16 đội đầu tiên được confirm, các đội sau bị reject
    """
    try:
        # Validate IPN data
        validation = momo_service.validate_ipn(data)

        if not validation["valid"]:
            logger.warning(f"MoMo IPN: Invalid data - {data}")
            return {"resultCode": 1, "message": "Invalid data"}

        # Kiểm tra resultCode (0 = thanh toán thành công)
        if validation["resultCode"] != 0:
            logger.info(
                f"MoMo IPN: Payment failed - "
                f"orderId={validation['orderId']}, "
                f"resultCode={validation['resultCode']}, "
                f"message={validation['message']}"
            )
            return {"resultCode": 0, "message": "OK"}

        # Tìm đội theo order_id
        team = db.query(Team).filter(Team.order_id == validation["orderId"]).first()

        if not team:
            logger.warning(f"MoMo IPN: Team not found - orderId={validation['orderId']}")
            return {"resultCode": 1, "message": "Team not found"}

        # Kiểm tra số tiền
        if validation["amount"] != int(team.amount):
            logger.warning(
                f"MoMo IPN: Amount mismatch - "
                f"orderId={validation['orderId']}, "
                f"expected={team.amount}, "
                f"received={validation['amount']}"
            )
            return {"resultCode": 1, "message": "Amount mismatch"}

        # Xử lý race condition với database transaction và SELECT FOR UPDATE
        # SQLAlchemy sử dụng with_for_update() để lock row
        from datetime import datetime

        try:
            # Bắt đầu transaction
            # Lock tất cả các row có status PAID_CONFIRMED để đếm chính xác
            confirmed_count = (
                db.query(func.count(Team.id))
                .filter(Team.status == TeamStatus.PAID_CONFIRMED)
                .with_for_update()
                .scalar()
            )

            # Lock team hiện tại để cập nhật
            team = (
                db.query(Team)
                .filter(Team.id == team.id)
                .with_for_update()
                .first()
            )

            # Kiểm tra xem đội đã được xử lý chưa (tránh duplicate IPN)
            if team.is_paid():
                logger.info(
                    f"MoMo IPN: Team already processed - "
                    f"orderId={validation['orderId']}, "
                    f"status={team.status.value}"
                )
                db.commit()
                return {"resultCode": 0, "message": "OK"}

            # Quyết định trạng thái dựa trên số lượng đội đã confirm
            if confirmed_count < Team.MAX_CONFIRMED_TEAMS:
                # Chưa đủ 16 đội → Confirm
                team.status = TeamStatus.PAID_CONFIRMED
                team.paid_at = datetime.now()
                db.commit()

                logger.info(
                    f"MoMo IPN: Team confirmed - "
                    f"orderId={validation['orderId']}, "
                    f"teamName={team.team_name}, "
                    f"confirmedCount={confirmed_count + 1}"
                )

                # Emit realtime event (sẽ implement sau với WebSocket hoặc SSE)
                # await emit_team_payment_confirmed(team)

            else:
                # Đã đủ 16 đội → Reject
                team.status = TeamStatus.PAID_REJECTED
                team.paid_at = datetime.now()
                db.commit()

                logger.info(
                    f"MoMo IPN: Team rejected (over limit) - "
                    f"orderId={validation['orderId']}, "
                    f"teamName={team.team_name}, "
                    f"confirmedCount={confirmed_count}"
                )

                # Emit realtime event
                # await emit_team_payment_rejected(team)

        except Exception as e:
            db.rollback()
            raise e

        # Trả về success cho MoMo
        return {"resultCode": 0, "message": "OK"}

    except Exception as e:
        logger.error(
            f"MoMo IPN Processing Error: {str(e)}",
            exc_info=True,
            extra={"request": data}
        )

        # Vẫn trả về success để MoMo không retry (nếu cần xử lý lại sau)
        return {"resultCode": 0, "message": "OK"}


@router.get("/my-teams", response_model=TeamsListResponse)
async def get_my_teams(
    user_id: Optional[int] = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """
    Lấy danh sách đội của user hiện tại (cần đăng nhập)
    GET /api/tournament/my-teams
    Trả về danh sách đội kèm payment link để thanh toán
    """
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Vui lòng đăng nhập để xem đội của bạn"
        )
    
    try:
        # Lấy tất cả đội của user
        teams = db.query(Team).filter(Team.user_id == user_id).order_by(Team.created_at.desc()).all()
        
        teams_data = []
        for team in teams:
            # Không tự động tạo payment link ở đây
            # User sẽ gọi /create-payment endpoint để tạo link mới với order_id mới mỗi lần
            # Điều này đảm bảo mỗi lần click "Thanh Toán Ngay" sẽ có order_id mới
            pay_url = None
            qr_code_url = None
            
            teams_data.append({
                "id": team.id,
                "email": team.email,
                "team_name": team.team_name,
                "leader_name": team.leader_name,
                "leader_student_id": team.leader_student_id,
                "phone": team.phone,
                "vice_leader_name": team.vice_leader_name,
                "vice_leader_student_id": team.vice_leader_student_id,
                "vice_leader_phone": team.vice_leader_phone,
                "members_list_file": team.members_list_file,
                "members_list_text": team.members_list_text,
                "order_id": team.order_id,
                "amount": float(team.amount),
                "status": team.status.value,
                "paid_at": team.paid_at.isoformat() if team.paid_at else None,
                "created_at": team.created_at.isoformat(),
                "updated_at": team.updated_at.isoformat(),
                "pay_url": pay_url,  # Payment link để thanh toán
                "qr_code_url": qr_code_url,  # QR code để quét
            })
        
        return TeamsListResponse(
            success=True,
            data={
                "teams": teams_data,
                "total": len(teams_data),
            },
        )
    except Exception as e:
        logger.error(f"Get my teams error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Có lỗi xảy ra khi lấy danh sách đội"
        )


@router.get("/teams", response_model=TeamsListResponse)
async def get_teams(db: Session = Depends(get_db)):
    """
    Lấy danh sách tất cả các đội
    GET /api/tournament/teams
    """
    try:
        teams = db.query(Team).order_by(Team.created_at.desc()).all()

        # Đếm số đội đã confirm
        confirmed_count = Team.count_confirmed(db)
        is_full = confirmed_count >= Team.MAX_CONFIRMED_TEAMS

        # Convert teams to response format
        teams_data = [
            {
                "id": team.id,
                "email": team.email,
                "team_name": team.team_name,
                "leader_name": team.leader_name,
                "leader_student_id": team.leader_student_id,
                "phone": team.phone,
                "vice_leader_name": team.vice_leader_name,
                "vice_leader_student_id": team.vice_leader_student_id,
                "vice_leader_phone": team.vice_leader_phone,
                "members_list_file": team.members_list_file,
                "members_list_text": team.members_list_text,
                "order_id": team.order_id,
                "amount": float(team.amount),
                "status": team.status.value,
                "paid_at": team.paid_at.isoformat() if team.paid_at else None,
                "created_at": team.created_at.isoformat(),
                "updated_at": team.updated_at.isoformat(),
            }
            for team in teams
        ]

        return TeamsListResponse(
            success=True,
            data={
                "teams": teams_data,
                "confirmed_count": confirmed_count,
                "max_teams": Team.MAX_CONFIRMED_TEAMS,
                "is_full": is_full,
            },
        )

    except Exception as e:
        logger.error(f"Get Teams Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Có lỗi xảy ra khi lấy danh sách đội"
        )

