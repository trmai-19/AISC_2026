from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.contribution import CommunityContribution
from app.models.admin_log import AdminQueueLog
from app.models.knowledge import KnowledgeSource, EvidenceCard, EvidenceVector
from app.schemas.admin_schema import AdminQueueItemResponse, QueueActionRequest, AuditLogResponse
from app.schemas.evidence_schema import KnowledgeSourceResponse
from app.services.rag_service import generate_query_vector

router = APIRouter(prefix="/admin", tags=["Admin Service & Review Queue"])

COUNTRY_MAP = {"JP": "Nhật Bản", "KR": "Hàn Quốc", "AU": "Australia"}
DOMAIN_MAP = {
    "phap_ly": "Hành chính – Pháp lý",
    "cong_viec": "Học tập – Công việc",
    "giao_tiep": "Giao tiếp – Văn hoá ứng xử",
    "nha_o": "Nhà ở – Tiện ích",
    "tai_chinh": "Tài chính – Ngân hàng",
    "y_te": "Y tế – Bảo hiểm",
    "giao_thong": "Giao thông – Đi lại",
    "doi_song": "Đời sống hằng ngày – Ẩm thực",
    "cong_dong": "Cộng đồng – Mạng lưới hỗ trợ"
}

@router.get("/queue", response_model=List[AdminQueueItemResponse])
def get_review_queue(
    status: Optional[str] = Query("PENDING", description="Lọc theo trạng thái: PENDING hoặc PROCESSED"),
    subfilter: Optional[str] = Query("ALL", description="Lọc con: ALL, APPROVED, REJECTED"),
    db: Session = Depends(get_db)
):
    """Lấy danh sách hàng đợi kiểm duyệt (Chờ duyệt hoặc Lịch sử đã xử lý)"""
    query = db.query(CommunityContribution)

    if status == "PENDING":
        query = query.filter(CommunityContribution.status == "PENDING")
    else:
        query = query.filter(CommunityContribution.status != "PENDING")
        if subfilter in ["APPROVED", "REJECTED"]:
            query = query.filter(CommunityContribution.status == subfilter)

    items = query.order_by(CommunityContribution.submitted_at.desc()).limit(100).all()

    result = []
    for item in items:
        result.append(
            AdminQueueItemResponse(
                id=item.contribution_id,
                type="SURVEY_SUBMISSION",
                submitter=f"{item.user.full_name} (Thành viên)" if item.user else "Ẩn danh",
                country=item.country_code,
                country_name=COUNTRY_MAP.get(item.country_code, item.country_code),
                domain_id=item.domain_id,
                domain_name=DOMAIN_MAP.get(item.domain_id, item.domain_id),
                submitted_at=item.submitted_at.strftime("%Y-%m-%d %H:%M"),
                title=item.exp_title,
                experience_text=item.exp_text,
                source_credibility="Đóng góp cộng đồng (Đã khử PII)",
                status=item.status,
                prep_level=item.prep_level,
                use_intention=item.use_intention
            )
        )
    return result

@router.post("/queue/{contribution_id}/action")
def process_queue_action(
    contribution_id: str,
    req: QueueActionRequest,
    db: Session = Depends(get_db)
):
    """
    Xử lý kiểm duyệt: APPROVE hoặc REJECT.
    Khi APPROVE: Tự động thăng hạng bài thành Evidence Card chính thức và sinh vector nhúng!
    """
    item = db.query(CommunityContribution).filter(CommunityContribution.contribution_id == contribution_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy mục trong hàng đợi")

    admin_id = req.admin_user_id or "11111111-aaaa-0000-0000-000000000001"

    # 1. Cập nhật trạng thái
    item.status = req.action
    db.commit()

    # 2. Ghi Audit Log
    log = AdminQueueLog(
        admin_user_id=admin_id,
        reference_id=item.contribution_id,
        action_taken=req.action,
        processed_at=datetime.utcnow()
    )
    db.add(log)

    # 3. NẾU APPROVE: Thăng hạng thành Evidence Card mới vào Kho Tri Thức
    new_card_id = None
    if req.action == "APPROVE":
        total_cards = db.query(EvidenceCard).count()
        new_card_id = f"EVD-{item.country_code}-{(total_cards + 1):03d}"

        new_card = EvidenceCard(
            card_id=new_card_id,
            source_id=None,
            country_code=item.country_code,
            domain_id=item.domain_id,
            title=item.exp_title,
            context=f"Kinh nghiệm thực tiễn từ cộng đồng người Việt tại {COUNTRY_MAP.get(item.country_code, item.country_code)}.",
            verified_content=item.exp_text,
            safe_action=item.exp_text[:120] + "...",
            donots="Tránh các hành vi tự phát vi phạm quy định cơ quan sở tại.",
            reliability_score=95,
            confidence_level="Đã thẩm định (95%)",
            status="APPROVED",
            verified_date=date.today()
        )
        db.add(new_card)
        db.commit()

        # Tự động sinh vector và nạp vào evidence_vectors
        vec = generate_query_vector(item.exp_title + " " + item.exp_text, item.country_code)
        new_vec = EvidenceVector(
            card_id=new_card_id,
            embedding_model="bge-m3",
            embedding=vec
        )
        db.add(new_vec)

    db.commit()

    return {
        "status": "success",
        "action": req.action,
        "contribution_id": contribution_id,
        "promoted_card_id": new_card_id,
        "message": f"Đã {('phê duyệt và chuyển thành công vào Kho Evidence Hub' if req.action == 'APPROVE' else 'từ chối')} thành công!"
    }

@router.get("/sources", response_model=List[KnowledgeSourceResponse])
def get_master_sources(db: Session = Depends(get_db)):
    """Lấy danh mục Master Data các nguồn đối soát chính thống"""
    sources = db.query(KnowledgeSource).order_by(KnowledgeSource.reliability_score.desc()).all()
    return sources
