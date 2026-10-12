from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.knowledge import EvidenceCard, KnowledgeSource
from app.schemas.evidence_schema import EvidenceCardResponse, DomainResponse

router = APIRouter(prefix="/evidence", tags=["Evidence Hub"])

DOMAINS = [
    {"id": "phap_ly", "code": "DOM-01", "name": "Hành chính – Pháp lý", "icon": "scale", "desc": "Thủ tục visa, thẻ cư trú, đăng ký thường trú, lao động, hợp đồng và quyền công dân."},
    {"id": "cong_viec", "code": "DOM-02", "name": "Học tập – Công việc", "icon": "briefcase", "desc": "Văn hóa công sở, làm thêm (baito), thi cử, đạo đức học thuật và quan hệ cấp trên - cấp dưới."},
    {"id": "giao_tiep", "code": "DOM-03", "name": "Giao tiếp – Văn hoá ứng xử", "icon": "message-circle", "desc": "Kính ngữ, cúi chào, xưng hô, giao tiếp phi ngôn ngữ, văn hóa xin lỗi và thể diện."},
    {"id": "nha_o", "code": "DOM-04", "name": "Nhà ở – Tiện ích", "icon": "home", "desc": "Thuê nhà, tiền lễ (Reikin/Shikikin), phân loại rác, tiếng ồn và nội quy căn hộ."},
    {"id": "tai_chinh", "code": "DOM-05", "name": "Tài chính – Ngân hàng", "icon": "credit-card", "desc": "Mở tài khoản ngân hàng, chuyển tiền kiều hối, mã số thuế và thanh toán điện tử."},
    {"id": "y_te", "code": "DOM-06", "name": "Y tế – Bảo hiểm", "icon": "activity", "desc": "Bảo hiểm y tế quốc dân (NHI / NHIS / OSHC), khám chữa bệnh và cấp cứu."},
    {"id": "giao_thong", "code": "DOM-07", "name": "Giao thông – Đi lại", "icon": "map-pin", "desc": "Tàu điện, xe buýt, thẻ IC/Opal, văn hóa nhường ghế, quy định đi xe đạp và bằng lái."},
    {"id": "doi_song", "code": "DOM-08", "name": "Đời sống hằng ngày – Ẩm thực", "icon": "coffee", "desc": "Quy chuẩn bàn ăn, rót rượu, tiền tip, chia hóa đơn (betsu-betsu / Dutch treat), siêu thị."},
    {"id": "cong_dong", "code": "DOM-09", "name": "Cộng đồng – Mạng lưới hỗ trợ", "icon": "users", "desc": "Hội đồng hương, hỗ trợ sinh viên quốc tế, cơ quan đại diện ngoại giao và các tổ chức thiện nguyện."}
]

DOMAIN_MAP = {d["id"]: d["name"] for d in DOMAINS}
COUNTRY_MAP = {"JP": "Nhật Bản", "KR": "Hàn Quốc", "AU": "Australia"}

@router.get("/domains", response_model=List[DomainResponse])
def get_domains():
    """Lấy danh mục 9 lĩnh vực đời sống chuẩn hóa"""
    return DOMAINS

@router.get("", response_model=List[EvidenceCardResponse])
def list_evidence_cards(
    country: Optional[str] = Query(None, description="Lọc quốc gia: JP, KR, AU hoặc ALL"),
    domain: Optional[str] = Query(None, description="Lọc mã lĩnh vực hoặc ALL"),
    q: Optional[str] = Query(None, description="Từ khóa tìm kiếm"),
    db: Session = Depends(get_db)
):
    """Tra cứu danh sách Thẻ Bằng Chứng trong Kho Tri thức có lọc đa tiêu chí"""
    query = db.query(EvidenceCard).filter(EvidenceCard.status == "APPROVED")

    if country and country != "ALL":
        query = query.filter(EvidenceCard.country_code == country)
    if domain and domain != "ALL":
        query = query.filter(EvidenceCard.domain_id == domain)
    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        query = query.filter(
            (EvidenceCard.title.ilike(term)) |
            (EvidenceCard.context.ilike(term)) |
            (EvidenceCard.verified_content.ilike(term))
        )

    cards = query.order_by(EvidenceCard.reliability_score.desc()).all()

    result = []
    for c in cards:
        result.append(
            EvidenceCardResponse(
                card_id=c.card_id,
                source_id=c.source_id,
                country_code=c.country_code,
                country_name=COUNTRY_MAP.get(c.country_code, c.country_code),
                domain_id=c.domain_id,
                domain_name=DOMAIN_MAP.get(c.domain_id, c.domain_id),
                title=c.title,
                context=c.context,
                verified_content=c.verified_content,
                safe_action=c.safe_action,
                donots=c.donots,
                reliability_score=c.reliability_score,
                confidence_level=c.confidence_level,
                status=c.status,
                verified_date=c.verified_date,
                source=c.source
            )
        )
    return result

@router.get("/{card_id}", response_model=EvidenceCardResponse)
def get_evidence_card_detail(card_id: str, db: Session = Depends(get_db)):
    """Xem chi tiết một Thẻ Bằng Chứng cụ thể"""
    card = db.query(EvidenceCard).filter(EvidenceCard.card_id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Không tìm thấy thẻ bằng chứng")

    return EvidenceCardResponse(
        card_id=card.card_id,
        source_id=card.source_id,
        country_code=card.country_code,
        country_name=COUNTRY_MAP.get(card.country_code, card.country_code),
        domain_id=card.domain_id,
        domain_name=DOMAIN_MAP.get(card.domain_id, card.domain_id),
        title=card.title,
        context=card.context,
        verified_content=card.verified_content,
        safe_action=card.safe_action,
        donots=card.donots,
        reliability_score=card.reliability_score,
        confidence_level=card.confidence_level,
        status=card.status,
        verified_date=card.verified_date,
        source=card.source
    )
