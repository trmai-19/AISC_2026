import json
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.services.rag_service import get_transformed_engine
from app.repositories.evidence_repository import EvidenceRepository
from app.schemas.evidence_schema import EvidenceCardResponse, DomainResponse, KnowledgeSourceResponse

logger = logging.getLogger(__name__)

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

def _map_chunk_to_card(r: Any) -> EvidenceCardResponse:
    """Chuyển đổi một chunk từ knowledge.current_rag_chunks thành EvidenceCardResponse chuẩn xác"""
    meta = r.metadata if isinstance(r.metadata, dict) else json.loads(r.metadata or '{}')
    content = r.content or ""
    source_kind = r.source_kind or "EXTERNAL"
    country_code = r.country_code or "JP"
    country_name = COUNTRY_MAP.get(country_code, country_code)

    # 1. Phân loại Domain: lấy trực tiếp từ metadata DB nếu có, mặc định giao tiếp cho cẩm nang manners/etiquette
    raw_domain = meta.get("domain_id")
    if raw_domain and raw_domain in DOMAIN_MAP:
        domain_id = raw_domain
    else:
        # Cẩm nang JNTO và Cultural Atlas tập trung vào nghi thức giao tiếp & ứng xử xã hội
        domain_id = "giao_tiep"

    domain_name = DOMAIN_MAP.get(domain_id, "Giao tiếp – Văn hoá ứng xử")

    # 2. Thông tin nguồn và tổ chức thật từ dữ liệu crawl
    if source_kind == "EXTERNAL":
        chunk_idx = (r.chunk_index or 0) + 1
        base_title = meta.get("title") or r.title or "Cẩm nang quy chuẩn ứng xử"
        title = f"{base_title} (Mục {chunk_idx})"
        org_name = meta.get("organization") or ("Japan National Tourism Organization (JNTO)" if country_code == "JP" else "Cultural Atlas - Mosaica")
        source_type = "Tài liệu chính thống đối soát"
        source_url = meta.get("source_url") or meta.get("resolved_url")
        context = meta.get("page_title") or f"Tài liệu hướng dẫn quy chuẩn văn hóa ứng xử chính thức tại {country_name}"
        confidence = "Nguồn chính thống đối soát"
        reliability = 100
    else:
        title = r.title or "Kinh nghiệm thực tế từ cộng đồng"
        org_name = f"Cộng đồng kiều bào tại {country_name}"
        source_type = "Kinh nghiệm cộng đồng"
        source_url = None
        context = f"Kinh nghiệm thực tiễn chia sẻ bởi kiều bào người Việt sinh sống tại {country_name}"
        confidence = "Kinh nghiệm cộng đồng"
        reliability = 95

    # 3. Thời gian thu thập / cập nhật từ metadata
    date_str = meta.get("stored_at") or meta.get("submitted_at") or meta.get("retrieved_at")
    verified_date = None
    if date_str:
        try:
            verified_date = datetime.fromisoformat(str(date_str).replace("Z", "+00:00")).date()
        except Exception:
            verified_date = date.today()
    else:
        verified_date = date.today()

    source_resp = KnowledgeSourceResponse(
        source_id=r.source_ref or f"SRC-{country_code}-{source_kind}",
        country_code=country_code,
        organization_name=org_name,
        source_type=source_type,
        document_title=r.title or title,
        document_url=source_url,
        published_date=verified_date,
        valid_until=date(2028, 12, 31),
        reliability_score=reliability
    )

    return EvidenceCardResponse(
        card_id=r.chunk_id,
        source_id=source_resp.source_id,
        country_code=country_code,
        country_name=country_name,
        domain_id=domain_id,
        domain_name=domain_name,
        title=title,
        context=context,
        verified_content=content,
        safe_action="",
        donots="",
        reliability_score=reliability,
        confidence_level=confidence,
        status="APPROVED",
        verified_date=verified_date,
        source_url=source_url,
        organization_name=org_name,
        source=source_resp
    )

class EvidenceService:
    @staticmethod
    def get_domains() -> List[DomainResponse]:
        return [DomainResponse(**d) for d in DOMAINS]

    @staticmethod
    def list_cards(
        db: Session,
        country: Optional[str] = None,
        domain: Optional[str] = None,
        q: Optional[str] = None
    ) -> List[EvidenceCardResponse]:
        """
        Tra cứu kho tri thức thật từ aisc_data.knowledge.current_rag_chunks.
        Nếu gặp sự cố, tự động fallback về aisc_db.evidence_cards.
        """
        try:
            engine = get_transformed_engine()
            with engine.connect() as conn:
                query_sql = """
                    SELECT 
                        chunk_id, document_id, chunk_index, content, country_code,
                        source_kind, source_ref, title, metadata
                    FROM knowledge.current_rag_chunks
                    WHERE is_active = TRUE
                """
                params: Dict[str, Any] = {}

                if country and country != "ALL":
                    query_sql += " AND country_code = :country"
                    params["country"] = country

                if q and q.strip():
                    term = f"%{q.strip().lower()}%"
                    query_sql += " AND (title ILIKE :term OR content ILIKE :term OR source_ref ILIKE :term)"
                    params["term"] = term

                query_sql += " ORDER BY source_kind DESC, country_code, chunk_index"
                rows = conn.execute(text(query_sql), params).fetchall()

                cards: List[EvidenceCardResponse] = []
                for r in rows:
                    card = _map_chunk_to_card(r)
                    if domain and domain != "ALL":
                        if card.domain_id != domain:
                            continue
                    cards.append(card)

                logger.info(f"EvidenceService: Trả về {len(cards)} thẻ bằng chứng thật từ aisc_data.")
                return cards
        except Exception as e:
            logger.warning(f"Lỗi khi đọc aisc_data.knowledge, fallback về aisc_db.evidence_cards: {e}")

        # Fallback về database cũ aisc_db
        cards_legacy = EvidenceRepository.list_cards(db, country=country, domain=domain, q=q, status="APPROVED")
        result = []
        for c in cards_legacy:
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

    @staticmethod
    def get_card_detail(db: Session, card_id: str) -> EvidenceCardResponse:
        """
        Xem chi tiết một thẻ bằng chứng theo card_id (chunk_id từ aisc_data hoặc legacy card_id)
        """
        try:
            engine = get_transformed_engine()
            with engine.connect() as conn:
                row = conn.execute(
                    text("""
                        SELECT 
                            chunk_id, document_id, chunk_index, content, country_code,
                            source_kind, source_ref, title, metadata
                        FROM knowledge.current_rag_chunks
                        WHERE chunk_id = :card_id AND is_active = TRUE
                        LIMIT 1
                    """),
                    {"card_id": card_id}
                ).fetchone()

                if row:
                    return _map_chunk_to_card(row)
        except Exception as e:
            logger.warning(f"Lỗi khi tìm chi tiết thẻ trong aisc_data: {e}")

        # Fallback tìm trong database aisc_db
        card = EvidenceRepository.get_by_id(db, card_id)
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

