from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AdminQueueItemResponse(BaseModel):
    id: str
    type: str
    submitter: str
    country: str
    country_name: str
    domain_id: str
    domain_name: str
    submitted_at: str
    title: str
    experience_text: str
    source_credibility: str
    status: Literal["PENDING", "APPROVED", "REJECTED"]
    prep_level: Optional[int] = None
    use_intention: Optional[int] = None

class QueueActionRequest(BaseModel):
    action: Literal["APPROVE", "REJECT"]
    admin_user_id: Optional[str] = "11111111-aaaa-0000-0000-000000000001"
    note: Optional[str] = None

class AuditLogResponse(BaseModel):
    log_id: int
    admin_user_id: str
    reference_id: str
    action_taken: str
    processed_at: datetime

    model_config = ConfigDict(from_attributes=True)
