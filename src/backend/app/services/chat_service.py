from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from app.repositories.chat_repository import ChatRepository
from app.repositories.contribution_repository import ContributionRepository
from app.models.contribution import CommunityContribution
from app.schemas.chat_schema import (
    ChatMessageRequest,
    ChatStructuredResponse,
    ChatFeedbackRequest,
    ChatHistoryItemResponse
)
from app.services.rag_service import execute_rag_pipeline

class ChatService:
    @staticmethod
    async def handle_message(db: Session, req: ChatMessageRequest) -> ChatStructuredResponse:
        user_id = req.user_id if req.user_id and req.user_id != "00000000-0000-0000-0000-000000000000" else None

        # 1. Lưu tin nhắn của người dùng vào chat_history
        ChatRepository.save_message(
            db=db,
            user_id=user_id,
            sender_type="USER",
            content=req.query
        )

        # 2. Thực thi RAG Pipeline (Dynamic Hybrid)
        rag_result = await execute_rag_pipeline(
            db=db,
            query=req.query,
            country=req.country or "JP",
            purpose=req.purpose or "DU_HOC",
            stage=req.stage or "PREPARING"
        )

        # 3. Lưu phản hồi của BOT vào chat_history
        matched_id = None
        if rag_result.get("direct_message"):
            bot_content = rag_result["direct_message"]
        elif rag_result.get("success") and rag_result.get("matched_card"):
            card = rag_result["matched_card"]
            matched_id = getattr(card, "card_id", None) if not isinstance(card, dict) else card.get("card_id")
            if matched_id and len(matched_id) > 50:
                matched_id = matched_id[:50]
            bot_content = f"【Hành vi an toàn】: {rag_result.get('safe_action')}\n【Điều cần tránh】: {rag_result.get('donots')}"
        else:
            bot_content = rag_result.get("refusal_message", "Hệ thống từ chối đưa ra kết luận.")

        ChatRepository.save_message(
            db=db,
            user_id=user_id,
            sender_type="BOT",
            content=bot_content,
            matched_card_id=matched_id
        )

        return ChatStructuredResponse(**rag_result)

    @staticmethod
    def get_history(db: Session, user_id: str) -> List[ChatHistoryItemResponse]:
        return ChatRepository.get_history(db, user_id=user_id, limit=20)

    @staticmethod
    def submit_feedback(db: Session, req: ChatFeedbackRequest) -> dict:
        user_id = req.user_id if req.user_id and req.user_id != "00000000-0000-0000-0000-000000000000" else "usr-2026-0000-0000-000000000001"

        ChatRepository.save_feedback(
            db=db,
            user_id=user_id,
            evidence_card_id=req.evidence_card_id,
            feedback_type=req.feedback_type
        )

        ticket_id = None
        if req.feedback_type == "REPORT":
            ticket_id = f"REV-TKT-{int(datetime.now(timezone.utc).timestamp()) % 10000:04d}"
            ticket = CommunityContribution(
                contribution_id=ticket_id,
                user_id=user_id,
                country_code="JP",
                domain_id="giao_tiep",
                exp_title=f"Báo lỗi nội dung thẻ {req.evidence_card_id}",
                exp_text="Người dùng gửi phản hồi đề nghị kiểm tra lại nguồn trích dẫn và nội dung ứng xử của thẻ này.",
                prep_level=3,
                use_intention=4,
                status="PENDING"
            )
            ContributionRepository.create_contribution(db, ticket)

        return {
            "status": "success",
            "feedback_type": req.feedback_type,
            "ticket_id": ticket_id,
            "message": "Cảm ơn bạn đã gửi đánh giá để hoàn thiện hệ thống!"
        }
