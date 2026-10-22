from typing import Optional
from datetime import date
from pydantic import BaseModel, ConfigDict

class KnowledgeSourceResponse(BaseModel):
    source_id: str
    country_code: str
    organization_name: str
    source_type: str
    document_title: str
    document_url: Optional[str] = None
    published_date: Optional[date] = None
    valid_until: Optional[date] = None
    reliability_score: int

    model_config = ConfigDict(from_attributes=True)

class EvidenceCardResponse(BaseModel):
    card_id: str
    source_id: Optional[str] = None
    country_code: str
    country_name: Optional[str] = None
    domain_id: str
    domain_name: Optional[str] = None
    title: str
    context: str
    verified_content: str
    safe_action: str
    donots: str
    reliability_score: int
    confidence_level: Optional[str] = None
    status: str
    verified_date: Optional[date] = None
    source_url: Optional[str] = None
    organization_name: Optional[str] = None
    source: Optional[KnowledgeSourceResponse] = None

    model_config = ConfigDict(from_attributes=True)

class DomainResponse(BaseModel):
    id: str
    code: str
    name: str
    icon: str
    desc: str
