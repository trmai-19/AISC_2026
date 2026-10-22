from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.evidence_schema import EvidenceCardResponse

class ChatMessageRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Câu hỏi hoặc tình huống của người dùng")
    country: Optional[str] = Field("JP", description="Quốc gia đến (JP, KR, AU)")
    purpose: Optional[str] = Field("DU_HOC", description="Mục đích (DU_HOC, LAO_DONG, DINH_CU)")
    stage: Optional[str] = Field("PREPARING", description="Giai đoạn hành trình")
    user_id: Optional[str] = None

class ChatSourceItem(BaseModel):
    chunk_id: str
    document_id: Optional[str] = None
    source_kind: str
    source_ref: str
    title: str
    source_url: Optional[str] = None
    similarity: float

class ChatStructuredResponse(BaseModel):
    success: bool
    response_type: Optional[str] = "RAG"  # "RAG", "GREETING", "IDENTITY", "OUT_OF_SCOPE"
    direct_message: Optional[str] = None
    context_analysis: Optional[str] = None
    safe_action: Optional[str] = None
    donots: Optional[str] = None
    matched_card: Optional[EvidenceCardResponse] = None
    matched_chunk: Optional[dict] = None
    sources: Optional[list[ChatSourceItem]] = None
    confidence: Optional[int] = None
    confidence_level: Optional[str] = None
    refusal_message: Optional[str] = None

class ChatFeedbackRequest(BaseModel):
    user_id: str
    evidence_card_id: str
    feedback_type: Literal["LIKE", "REPORT"]

class ChatHistoryItemResponse(BaseModel):
    message_id: int
    user_id: Optional[str] = None
    sender_type: Literal["USER", "BOT"]
    content: str
    matched_card_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
