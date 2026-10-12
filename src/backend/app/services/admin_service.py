from typing import List, Optional
from datetime import datetime, date
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.repositories.contribution_repository import ContributionRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.audit_repository import AuditRepository
from app.models.knowledge import EvidenceCard
from app.schemas.admin_schema import AdminQueueItemResponse, QueueActionRequest
from app.schemas.evidence_schema import KnowledgeSourceResponse
from app.services.rag_service import generate_query_vector

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

class AdminService:
    @staticmethod
    def get_review_queue(
        db: Session,
        status: Optional[str] = "PENDING",
        subfilter: Optional[str] = "ALL"
    ) -> List[AdminQueueItemResponse]:
        items = ContributionRepository.get_review_queue(db, status=status, subfilter=subfilter)
        result = []
        for item in items:
            country_code = str(item.country_code or "JP")
            domain_id = str(item.domain_id or "phap_ly")
            country_name = str(COUNTRY_MAP.get(country_code, country_code))
            domain_name = str(DOMAIN_MAP.get(domain_id, domain_id))

            result.append(
                AdminQueueItemResponse(
                    id=item.contribution_id,
                    type="SURVEY_SUBMISSION",
                    submitter=f"{item.user.full_name} (Thành viên)" if item.user else "Ẩn danh",
                    country=country_code,
                    country_name=country_name,
                    domain_id=domain_id,
                    domain_name=domain_name,
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

    @staticmethod
    def process_queue_action(
        db: Session,
        contribution_id: str,
        req: QueueActionRequest
    ) -> dict:
        item = ContributionRepository.get_by_id(db, contribution_id)
        if not item:
            raise HTTPException(status_code=404, detail="Không tìm thấy mục trong hàng đợi")

        admin_id = req.admin_user_id or "11111111-aaaa-0000-0000-000000000001"

        # 1. Cập nhật trạng thái đóng góp (Tuân thủ CHECK constraint 'ck_cc_status')
        new_status = "APPROVED" if req.action in ["APPROVE", "APPROVED"] else "REJECTED"
        ContributionRepository.update_status(db, contribution_id, new_status)

        # 2. Ghi Audit Log
        AuditRepository.save_audit_log(
            db=db,
            admin_user_id=admin_id,
            reference_id=item.contribution_id,
            action_taken=req.action
        )

        # 3. NẾU APPROVE: Thăng hạng thành Evidence Card và sinh vector tự động
        new_card_id = None
        if req.action == "APPROVE":
            total_cards = EvidenceRepository.count_cards(db)
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
            EvidenceRepository.create_card(db, new_card)

            # Tự động sinh vector và nạp vào evidence_vectors
            vec = generate_query_vector(item.exp_title + " " + item.exp_text, item.country_code)
            EvidenceRepository.save_vector(db, new_card_id, vec, model="bge-m3")

        return {
            "status": "success",
            "action": req.action,
            "contribution_id": contribution_id,
            "promoted_card_id": new_card_id,
            "message": f"Đã {('phê duyệt và chuyển thành công vào Kho Evidence Hub' if req.action == 'APPROVE' else 'từ chối')} thành công!"
        }

    @staticmethod
    def get_master_sources(db: Session) -> List[KnowledgeSourceResponse]:
        return EvidenceRepository.get_master_sources(db)
