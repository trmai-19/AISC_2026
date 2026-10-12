from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.evidence_schema import EvidenceCardResponse, DomainResponse
from app.services.evidence_service import EvidenceService

router = APIRouter(prefix="/evidence", tags=["Evidence Hub"])

@router.get("/domains", response_model=List[DomainResponse])
def get_domains():
    """Lấy danh mục 9 lĩnh vực đời sống chuẩn hóa"""
    return EvidenceService.get_domains()

@router.get("", response_model=List[EvidenceCardResponse])
def list_evidence_cards(
    country: Optional[str] = Query(None, description="Lọc quốc gia: JP, KR, AU hoặc ALL"),
    domain: Optional[str] = Query(None, description="Lọc mã lĩnh vực hoặc ALL"),
    q: Optional[str] = Query(None, description="Từ khóa tìm kiếm"),
    db: Session = Depends(get_db)
):
    """Tra cứu danh sách Thẻ Bằng Chứng trong Kho Tri thức có lọc đa tiêu chí"""
    return EvidenceService.list_cards(db, country=country, domain=domain, q=q)

@router.get("/{card_id}", response_model=EvidenceCardResponse)
def get_evidence_card_detail(card_id: str, db: Session = Depends(get_db)):
    """Xem chi tiết một Thẻ Bằng Chứng cụ thể"""
    return EvidenceService.get_card_detail(db, card_id)
