import re
from datetime import datetime
from sqlalchemy.orm import Session
from app.repositories.contribution_repository import ContributionRepository
from app.repositories.user_repository import UserRepository
from app.models.contribution import CommunityContribution
from app.schemas.survey_schema import SurveySubmitRequest, SurveySubmitResponse

def sanitize_pii(text: str) -> str:
    """Tự động phát hiện và ẩn thông tin nhận dạng cá nhân (Email, SĐT)"""
    cleaned = re.sub(r'(\+?84|0)\d{9,10}', '[ĐÃ ẨN SĐT]', text)
    cleaned = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[ĐÃ ẨN EMAIL]', cleaned)
    return cleaned

class SurveyService:
    @staticmethod
    def submit_survey(db: Session, req: SurveySubmitRequest) -> SurveySubmitResponse:
        user_id = req.user_id if req.user_id and req.user_id != "00000000-0000-0000-0000-000000000000" else None
        if not user_id:
            default_user = UserRepository.get_first_user(db)
            user_id = default_user.user_id if default_user else None

        count = ContributionRepository.count_contributions(db)
        ticket_id = f"REV-2026-{(count + 1):03d}"

        cleaned_title = sanitize_pii(req.title)
        cleaned_text = sanitize_pii(req.experience_text)

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

        ContributionRepository.create_contribution(
            db=db,
            contribution=contribution,
            challenges=req.challenges
        )

        return SurveySubmitResponse(
            ticket_id=ticket_id,
            status="PENDING",
            message="Cảm ơn bạn đã đóng góp! Dữ liệu đã được chuyển vào hàng đợi kiểm duyệt của Ban Quản Trị."
        )
