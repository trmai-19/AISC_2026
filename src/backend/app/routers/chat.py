import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.chat import ChatHistory, UserFeedback
from app.models.contribution import CommunityContribution
from app.schemas.chat_schema import (
    ChatMessageRequest,
    ChatStructuredResponse,
    ChatFeedbackRequest,
    ChatHistoryItemResponse
)
from app.services.rag_service import execute_rag_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["RAG Chatbot Copilot"])

@router.post("/message", response_model=ChatStructuredResponse)
async def send_chat_message(req: ChatMessageRequest, db: Session = Depends(get_db)):
    """
    Tiếp nhận câu hỏi của người dùng và thực thi luồng RAG 2 giai đoạn:
    Lọc Metadata -> Tìm kiếm Vector trên PostgreSQL -> Sinh câu trả lời cấu trúc 4 phần
    """
    user_id = req.user_id if req.user_id and req.user_id != "00000000-0000-0000-0000-000000000000" else None

    # 1. Lưu tin nhắn của người dùng vào chat_history
    user_msg = ChatHistory(
        user_id=user_id,
        sender_type="USER",
        content=req.query
    )
    db.add(user_msg)
    db.commit()

    # 2. Thực thi RAG Pipeline
    rag_result = await execute_rag_pipeline(
        db=db,
        query=req.query,
        country=req.country or "JP",
        purpose=req.purpose or "DU_HOC",
        stage=req.stage or "PREPARING"
    )

    # 3. Lưu phản hồi của BOT vào chat_history
    matched_id = None
    if rag_result.get("success") and rag_result.get("matched_card"):
        matched_id = rag_result["matched_card"]["card_id"]
        bot_content = f"【Hành vi an toàn】: {rag_result.get('safe_action')}\n【Điều cần tránh】: {rag_result.get('donots')}"
    else:
        bot_content = rag_result.get("refusal_message", "Hệ thống từ chối đưa ra kết luận.")

    bot_msg = ChatHistory(
        user_id=user_id,
        sender_type="BOT",
        content=bot_content,
        matched_card_id=matched_id
    )
    db.add(bot_msg)
    db.commit()

    return rag_result

@router.get("/history/{user_id}", response_model=List[ChatHistoryItemResponse])
def get_chat_history(user_id: str, db: Session = Depends(get_db)):
    """Lấy lịch sử hội thoại gần nhất của người dùng"""
    logs = (
        db.query(ChatHistory)
        .filter(ChatHistory.user_id == user_id)
        .order_by(ChatHistory.created_at.desc())
        .limit(20)
        .all()
    )
    return logs[::-1]  # Trả về theo thứ tự thời gian tăng dần

@router.post("/feedback")
def submit_chat_feedback(req: ChatFeedbackRequest, db: Session = Depends(get_db)):
    """Đánh giá câu trả lời (LIKE) hoặc Báo lỗi (REPORT). Nếu báo lỗi sẽ tự động tạo Ticket gửi Admin"""
    user_id = req.user_id if req.user_id and req.user_id != "00000000-0000-0000-0000-000000000000" else "usr-2026-0000-0000-000000000001"

    feedback = UserFeedback(
        user_id=user_id,
        evidence_card_id=req.evidence_card_id,
        feedback_type=req.feedback_type
    )
    db.add(feedback)

    # Nếu người dùng bấm REPORT, tự động tạo ticket trong hàng đợi duyệt
    ticket_id = None
    if req.feedback_type == "REPORT":
        ticket_id = f"REV-TKT-{int(datetime.utcnow().timestamp()) % 10000:04d}"
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
        db.add(ticket)

    db.commit()

    return {
        "status": "success",
        "feedback_type": req.feedback_type,
        "ticket_id": ticket_id,
        "message": "Cảm ơn bạn đã gửi đánh giá để hoàn thiện hệ thống!"
    }
