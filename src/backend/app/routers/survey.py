from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.survey_schema import SurveySubmitRequest, SurveySubmitResponse
from app.services.survey_service import SurveyService

router = APIRouter(prefix="/survey", tags=["Community Survey & Data Ingestion"])

@router.post("/submit", response_model=SurveySubmitResponse)
def submit_survey(req: SurveySubmitRequest, db: Session = Depends(get_db)):
    """
    Tiếp nhận biểu mẫu khảo sát và tình huống đóng góp thực tế từ cộng đồng:
    Khử định danh PII -> Lưu trạng thái PENDING -> Đẩy vào hàng đợi duyệt của Admin
    """
    return SurveyService.submit_survey(db, req)
