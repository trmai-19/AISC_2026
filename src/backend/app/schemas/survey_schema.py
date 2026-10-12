from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class SurveySubmitRequest(BaseModel):
    country: Literal["JP", "KR", "AU"]
    purpose: Literal["DU_HOC", "LAO_DONG", "DINH_CU"]
    stage: str
    prep_level: int = Field(..., ge=1, le=5, description="Thang đo mức chuẩn bị 1-5")
    challenges: List[str] = Field(default_factory=list, description="Danh sách mã rào cản gặp phải")
    title: str = Field(..., min_length=5, max_length=255, description="Tiêu đề tình huống ứng xử")
    domain_id: str = Field(..., description="Mã lĩnh vực thuộc 9 lĩnh vực đời sống")
    experience_text: str = Field(..., min_length=15, description="Mô tả cụ thể tình huống và cách xử lý")
    use_intention: int = Field(..., ge=1, le=5, description="Ý định sẵn sàng sử dụng ứng dụng 1-5")
    user_id: Optional[str] = None

class SurveySubmitResponse(BaseModel):
    ticket_id: str
    status: str
    message: str
