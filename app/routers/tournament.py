"""
Router: Tournament
Xử lý các API liên quan đến đăng ký giải đấu và thanh toán MoMo
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Response
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
    StatusUpdateSchema,
)
from app.services.momo_service import MomoService
from app.routers.auth import get_current_user_id_optional, get_current_user_id, get_current_admin_user
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
    members_list_drive_link: Optional[str] = Form(None),  # Thêm field để nhận Google Drive link
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

        # Xử lý members_list_text: ưu tiên members_list_drive_link nếu có, sau đó mới dùng members_list_text
        final_members_list_text = members_list_text
        if members_list_drive_link:
            final_members_list_text = members_list_drive_link
        elif not members_list_text:
            final_members_list_text = None

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
            members_list_text=final_members_list_text,  # Lưu Google Drive link vào đây
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
            return_url = os.getenv('MOMO_RETURN_URL', 'https://www.lcdkhoacntt1.com/itiscup/payment/callback')
            
            # Lấy IPN URL từ env và log để debug
            ipn_url = os.getenv('MOMO_NOTIFY_URL', '')
            logger.info(f"Creating payment link for team {team.id}, order_id: {team.order_id}, amount: {team.amount}, return_url: {return_url}, ipn_url: {ipn_url}")
            
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
                request_id = payment_data.get("requestId")
                
                # Lưu request_id vào database để có thể query status sau
                if request_id:
                    team.request_id = request_id
                    db.commit()
                    db.refresh(team)
                
                logger.info(f"Payment link created successfully: pay_url={pay_url is not None}, qr_code_url={qr_code_url is not None}, request_id={request_id}")
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
        return_url = os.getenv('MOMO_RETURN_URL', 'https://www.lcdkhoacntt1.com/itiscup/payment/callback')
        
        # Lấy IPN URL từ env và log để debug
        ipn_url = os.getenv('MOMO_NOTIFY_URL', '')
        logger.info(f"🔔 Creating payment link: order_id={new_order_id}")
        logger.info(f"🔔 Return URL: {return_url}")
        logger.info(f"🔔 IPN URL (Webhook): {ipn_url}")
        if not ipn_url:
            logger.error("❌ MOMO_NOTIFY_URL is not set! IPN will not work!")

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

        # Lưu request_id vào database để có thể query status sau
        request_id = payment_data.get("requestId")
        if request_id:
            team.request_id = request_id
            db.commit()
            db.refresh(team)
            logger.info(f"Saved request_id for team {team.id}: {request_id}")

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


@router.get("/test-ipn")
async def test_ipn_endpoint():
    """
    Test endpoint để kiểm tra IPN endpoint có hoạt động không
    GET /api/tournament/test-ipn
    """
    ipn_url = os.getenv('MOMO_NOTIFY_URL', 'NOT SET')
    return {
        "status": "IPN endpoint is accessible",
        "ipn_url": ipn_url,
        "ipn_endpoint": f"{ipn_url if ipn_url != 'NOT SET' else 'https://beitiscup-production.up.railway.app/api/tournament/momo-ipn'}",
        "message": "If you see this, the endpoint is working. Make sure this URL is configured in MoMo dashboard.",
        "instructions": [
            "1. Copy the ipn_endpoint URL above",
            "2. Go to MoMo Business Dashboard",
            "3. Navigate to Settings > Webhook Configuration",
            "4. Set IPN URL to the ipn_endpoint value",
            "5. Save the configuration"
        ]
    }


@router.post("/momo-ipn")
async def momo_ipn(
    request: Request,
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
        # Log request headers để debug
        logger.info(f"🔔 MoMo IPN Request received from: {request.client.host if request.client else 'unknown'}")
        logger.info(f"MoMo IPN Headers: {dict(request.headers)}")
        
        # Lấy data từ request body
        data = await request.json()
        logger.info(f"✅ MoMo IPN received: orderId={data.get('orderId')}, resultCode={data.get('resultCode')}, amount={data.get('amount')}")
        
        # Validate IPN data
        validation = momo_service.validate_ipn(data)

        if not validation["valid"]:
            logger.warning(f"MoMo IPN: Invalid data - {data}")
            # MoMo yêu cầu HTTP 204 (No Content) - không có body
            return Response(status_code=204)

        # Kiểm tra resultCode 
        # 0 = thanh toán thành công
        # 9000 = authorization thành công (cũng coi là thành công)
        # Khác 0 và 9000 = thất bại
        if validation["resultCode"] not in [0, 9000]:
            logger.info(
                f"MoMo IPN: Payment failed - "
                f"orderId={validation['orderId']}, "
                f"resultCode={validation['resultCode']}, "
                f"message={validation['message']}"
            )
            # Vẫn trả về 204 vì đây là notification, không phải error
            return Response(status_code=204)
        
        # Log khi thanh toán thành công
        logger.info(
            f"MoMo IPN: Payment successful - "
            f"orderId={validation['orderId']}, "
            f"resultCode={validation['resultCode']}, "
            f"amount={validation['amount']}"
        )

        # Tìm đội theo order_id
        team = db.query(Team).filter(Team.order_id == validation["orderId"]).first()

        if not team:
            logger.warning(f"MoMo IPN: Team not found - orderId={validation['orderId']}")
            # Trả về 204 vì đây là notification, không phải error
            return Response(status_code=204)

        # Kiểm tra số tiền
        if validation["amount"] != int(team.amount):
            logger.warning(
                f"MoMo IPN: Amount mismatch - "
                f"orderId={validation['orderId']}, "
                f"expected={team.amount}, "
                f"received={validation['amount']}"
            )
            # Trả về 204 vì đây là notification, không phải error
            return Response(status_code=204)

        # Xử lý race condition với database transaction và SELECT FOR UPDATE
        # SQLAlchemy sử dụng with_for_update() để lock row
        from datetime import datetime

        try:
            # Lock team hiện tại để cập nhật trước
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
                # MoMo yêu cầu HTTP 204 (No Content)
                return Response(status_code=204)

            # Query tất cả teams đã confirmed (không dùng aggregate với FOR UPDATE)
            # Đếm trong Python thay vì SQL
            confirmed_teams = (
                db.query(Team.id)
                .filter(Team.status == TeamStatus.PAID_CONFIRMED)
                .with_for_update()
                .all()
            )
            confirmed_count = len(confirmed_teams)

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
            logger.error(f"MoMo IPN: Database error - {str(e)}", exc_info=True)
            # Vẫn trả về 204 để MoMo không retry
            return Response(status_code=204)

        # MoMo yêu cầu HTTP 204 (No Content) - không có body
        return Response(status_code=204)

    except Exception as e:
        logger.error(
            f"MoMo IPN Processing Error: {str(e)}",
            exc_info=True,
            extra={"request": data if 'data' in locals() else {}}
        )

        # MoMo yêu cầu HTTP 204 (No Content) - vẫn trả về 204 để MoMo không retry
        return Response(status_code=204)


@router.get("/team-status/{order_id}")
async def get_team_status_by_order_id(
    order_id: str,
    db: Session = Depends(get_db),
):
    """
    Lấy trạng thái đội theo order_id (public endpoint để check sau thanh toán)
    GET /api/tournament/team-status/{order_id}
    
    Nếu đội chưa thanh toán và có request_id, tự động query MoMo để kiểm tra trạng thái
    """
    try:
        team = db.query(Team).filter(Team.order_id == order_id).first()
        
        if not team:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy đội với order_id này"
            )
        
        # Nếu đội chưa thanh toán và có request_id, tự động query MoMo
        if team.status == TeamStatus.REGISTERED and team.request_id:
            logger.info(f"🔍 Team {team.id} not yet paid, querying MoMo for status...")
            
            # Query MoMo để kiểm tra trạng thái thanh toán
            momo_response = momo_service.query_transaction(team.order_id, team.request_id)
            
            if momo_response and momo_response.get("resultCode") == 0:
                # Thanh toán thành công, cập nhật trạng thái
                logger.info(f"✅ MoMo query successful: orderId={team.order_id}, payment confirmed")
                
                # Xử lý cập nhật trạng thái với race condition handling
                from datetime import datetime
                
                try:
                    # Lock team hiện tại trước
                    team = (
                        db.query(Team)
                        .filter(Team.id == team.id)
                        .with_for_update()
                        .first()
                    )
                    
                    # Kiểm tra lại status (tránh duplicate update)
                    if not team.is_paid():
                        # Query tất cả teams đã confirmed (không dùng aggregate với FOR UPDATE)
                        # Đếm trong Python thay vì SQL
                        confirmed_teams = (
                            db.query(Team.id)
                            .filter(Team.status == TeamStatus.PAID_CONFIRMED)
                            .with_for_update()
                            .all()
                        )
                        confirmed_count = len(confirmed_teams)
                        
                        if confirmed_count < Team.MAX_CONFIRMED_TEAMS:
                            team.status = TeamStatus.PAID_CONFIRMED
                            team.paid_at = datetime.now()
                            logger.info(f"✅ Team {team.id} confirmed via MoMo query")
                        else:
                            team.status = TeamStatus.PAID_REJECTED
                            team.paid_at = datetime.now()
                            logger.info(f"⚠️  Team {team.id} rejected (over limit) via MoMo query")
                        
                        db.commit()
                        db.refresh(team)
                    
                except Exception as e:
                    db.rollback()
                    logger.error(f"Error updating team status from MoMo query: {str(e)}")
        
        logger.info(f"Team status check: order_id={order_id}, status={team.status.value}, paid_at={team.paid_at}")
        
        return {
            "success": True,
            "data": {
                "team_id": team.id,
                "team_name": team.team_name,
                "order_id": team.order_id,
                "status": team.status.value,
                "paid_at": team.paid_at.isoformat() if team.paid_at else None,
                "created_at": team.created_at.isoformat(),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get team status error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Có lỗi xảy ra khi lấy trạng thái đội"
        )


@router.post("/verify-payment/{order_id}")
async def verify_payment_status(
    order_id: str,
    db: Session = Depends(get_db),
):
    """
    Xác thực trạng thái thanh toán bằng cách query trực tiếp từ MoMo
    POST /api/tournament/verify-payment/{order_id}
    
    Endpoint này cho phép frontend/user chủ động kích hoạt kiểm tra thanh toán
    """
    try:
        team = db.query(Team).filter(Team.order_id == order_id).first()
        
        if not team:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy đội với order_id này"
            )
        
        # Kiểm tra xem đã thanh toán chưa
        if team.is_paid():
            return {
                "success": True,
                "message": "Đội này đã được xác nhận thanh toán",
                "data": {
                    "order_id": team.order_id,
                    "status": team.status.value,
                    "paid_at": team.paid_at.isoformat() if team.paid_at else None,
                }
            }
        
        # Kiểm tra có request_id không
        if not team.request_id:
            raise HTTPException(
                status_code=400,
                detail="Không thể xác thực thanh toán. Vui lòng thử tạo lại link thanh toán."
            )
        
        logger.info(f"🔍 Manual verification requested for team {team.id}, order_id={order_id}")
        
        # Query MoMo để kiểm tra trạng thái
        momo_response = momo_service.query_transaction(team.order_id, team.request_id)
        
        if not momo_response:
            raise HTTPException(
                status_code=500,
                detail="Không thể kết nối đến MoMo để kiểm tra trạng thái"
            )
        
        result_code = momo_response.get("resultCode")
        
        # resultCode = 0 hoặc 9000 = thanh toán thành công
        if result_code in [0, 9000]:
            logger.info(f"✅ MoMo verification successful: orderId={order_id}")
            
            # Cập nhật trạng thái với race condition handling
            from datetime import datetime
            
            try:
                # Lock team hiện tại trước
                team = (
                    db.query(Team)
                    .filter(Team.id == team.id)
                    .with_for_update()
                    .first()
                )
                
                # Kiểm tra lại status (tránh duplicate update)
                if not team.is_paid():
                    # Query tất cả teams đã confirmed (không dùng aggregate với FOR UPDATE)
                    # Đếm trong Python thay vì SQL
                    confirmed_teams = (
                        db.query(Team.id)
                        .filter(Team.status == TeamStatus.PAID_CONFIRMED)
                        .with_for_update()
                        .all()
                    )
                    confirmed_count = len(confirmed_teams)
                    
                    if confirmed_count < Team.MAX_CONFIRMED_TEAMS:
                        team.status = TeamStatus.PAID_CONFIRMED
                        team.paid_at = datetime.now()
                        db.commit()
                        db.refresh(team)
                        
                        return {
                            "success": True,
                            "message": "Thanh toán thành công! Đội của bạn đã được xác nhận.",
                            "data": {
                                "order_id": team.order_id,
                                "status": team.status.value,
                                "paid_at": team.paid_at.isoformat(),
                                "confirmed_count": confirmed_count + 1,
                            }
                        }
                    else:
                        team.status = TeamStatus.PAID_REJECTED
                        team.paid_at = datetime.now()
                        db.commit()
                        db.refresh(team)
                        
                        return {
                            "success": False,
                            "message": "Thanh toán thành công nhưng giải đấu đã đủ 16 đội.",
                            "data": {
                                "order_id": team.order_id,
                                "status": team.status.value,
                                "paid_at": team.paid_at.isoformat(),
                            }
                        }
                else:
                    # Đã được xử lý rồi
                    return {
                        "success": True,
                        "message": "Đội này đã được xác nhận thanh toán trước đó.",
                        "data": {
                            "order_id": team.order_id,
                            "status": team.status.value,
                            "paid_at": team.paid_at.isoformat() if team.paid_at else None,
                        }
                    }
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error updating team status: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Có lỗi khi cập nhật trạng thái đội"
                )
        
        # Chưa thanh toán hoặc thanh toán thất bại
        return {
            "success": False,
            "message": f"Thanh toán chưa thành công. {momo_response.get('message', '')}",
            "data": {
                "order_id": team.order_id,
                "status": team.status.value,
                "momo_result_code": result_code,
                "momo_message": momo_response.get("message", ""),
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verify payment error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Có lỗi xảy ra khi xác thực thanh toán"
        )


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
                "members_list_drive_link": team.members_list_text,  # Trả về members_list_text như members_list_drive_link
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
                "members_list_drive_link": team.members_list_text,  # Trả về members_list_text như members_list_drive_link
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


@router.patch("/teams/{team_id}/status")
async def update_team_status(
    team_id: int,
    status_update: StatusUpdateSchema,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Cập nhật trạng thái thanh toán của đội (chỉ admin)
    PATCH /api/tournament/teams/{team_id}/status
    """
    try:
        from datetime import datetime
        
        # Tìm team
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy đội với ID này"
            )
        
        # Validate status
        old_status = team.status
        new_status = status_update.status
        
        # Cập nhật status
        team.status = new_status
        
        # Nếu chuyển sang PAID_CONFIRMED hoặc PAID_REJECTED, cập nhật paid_at
        if new_status in [TeamStatus.PAID_CONFIRMED, TeamStatus.PAID_REJECTED] and not team.paid_at:
            team.paid_at = datetime.now()
        
        # Nếu chuyển từ PAID_CONFIRMED/PAID_REJECTED về REGISTERED, xóa paid_at
        if new_status == TeamStatus.REGISTERED and team.paid_at:
            team.paid_at = None
        
        # Lưu vào database
        db.commit()
        db.refresh(team)
        
        logger.info(
            f"Admin {admin_user.username} (ID: {admin_user.id}) updated team {team_id} ({team.team_name}) "
            f"status from {old_status.value} to {new_status.value}"
        )
        
        return {
            "success": True,
            "message": "Cập nhật trạng thái thành công",
            "data": {
                "team_id": team.id,
                "team_name": team.team_name,
                "status": team.status.value,
                "updated_at": team.updated_at.isoformat() if team.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Update Team Status Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Có lỗi xảy ra khi cập nhật trạng thái đội"
        )


@router.delete("/teams/{team_id}")
async def delete_team(
    team_id: int,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Xóa một đội (chỉ admin)
    DELETE /api/tournament/teams/{team_id}
    """
    try:
        team = db.query(Team).filter(Team.id == team_id).first()
        
        if not team:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy đội"
            )
        
        # Xóa đội
        db.delete(team)
        db.commit()
        
        logger.info(f"Admin {admin_user.username} (ID: {admin_user.id}) deleted team {team_id} ({team.team_name})")
        
        return {
            "success": True,
            "message": "Xóa đội thành công"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Delete Team Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Có lỗi xảy ra khi xóa đội"
        )

