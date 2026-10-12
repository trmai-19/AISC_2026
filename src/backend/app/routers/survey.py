import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.contribution import CommunityContribution, ContributionChallenge
from app.schemas.survey_schema import SurveySubmitRequest, SurveySubmitResponse

router = APIRouter(prefix="/survey", tags=["Community Survey & Data Ingestion"])

def sanitize_pii(text: str) -> str:
    """Tự động phát hiện và ẩn thông tin nhận dạng cá nhân (Email, SĐT)"""
    # Ẩn số điện thoại
    cleaned = re.sub(r'(\+?84|0)\d{9,10}', '[ĐÃ ẨN SĐT]', text)
    # Ẩn email
    cleaned = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[ĐÃ ẨN EMAIL]', cleaned)
    return cleaned

@router.post("/submit", response_model=SurveySubmitResponse)
def submit_survey(req: SurveySubmitRequest, db: Session = Depends(get_db)):
    """
    Tiếp nhận biểu mẫu khảo sát và tình huống đóng góp thực tế từ cộng đồng:
    Khử định danh PII -> Lưu trạng thái PENDING -> Đẩy vào hàng đợi duyệt của Admin
    """
    user_id = req.user_id if req.user_id and req.user_id != "00000000-0000-0000-0000-000000000000" else "usr-2026-0000-0000-000000000001"

    # Đếm số lượng hiện có để sinh ID tăng dần
    count = db.query(CommunityContribution).count()
    ticket_id = f"REV-2026-{(count + 1):03d}"

    cleaned_title = sanitize_pii(req.title)
    cleaned_text = sanitize_pii(req.experience_text)

    # 1. Tạo bản ghi đóng góp
    contribution = CommunityContribution(
        contribution_id=ticket_id,
        user_id=user_id,
        country_code=req.country,
        domain_id=req.domain_id,
        exp_title=cleaned_title,
        exp_text=cleaned_text,
        prep_level=req.prep_level,
        use_intention=req.use_intention,
        status="PENDING",
        submitted_at=datetime.utcnow()
    )
    db.add(contribution)

    # 2. Thêm các rào cản đã chọn
    if req.challenges:
        for code in req.challenges:
            challenge = ContributionChallenge(
                contribution_id=ticket_id,
                challenge_code=code
            )
            db.add(challenge)

    db.commit()

    return SurveySubmitResponse(
        ticket_id=ticket_id,
        status="PENDING",
        message="Cảm ơn bạn đã đóng góp! Dữ liệu đã được chuyển vào hàng đợi kiểm duyệt của Ban Quản Trị."
    )
