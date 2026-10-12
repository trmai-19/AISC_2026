from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.chat_schema import (
    ChatMessageRequest,
    ChatStructuredResponse,
    ChatFeedbackRequest,
    ChatHistoryItemResponse
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["RAG Chatbot Copilot"])

@router.post("/message", response_model=ChatStructuredResponse)
async def send_chat_message(req: ChatMessageRequest, db: Session = Depends(get_db)):
    """
    Tiếp nhận câu hỏi của người dùng và thực thi luồng RAG 2 giai đoạn:
    Lọc Metadata -> Tìm kiếm Vector trên PostgreSQL -> Sinh câu trả lời cấu trúc 4 phần
    """
    return await ChatService.handle_message(db, req)

@router.get("/history/{user_id}", response_model=List[ChatHistoryItemResponse])
def get_chat_history(user_id: str, db: Session = Depends(get_db)):
    """Lấy lịch sử hội thoại gần nhất của người dùng"""
    return ChatService.get_history(db, user_id)

@router.post("/feedback")
def submit_chat_feedback(req: ChatFeedbackRequest, db: Session = Depends(get_db)):
    """Đánh giá câu trả lời (LIKE) hoặc Báo lỗi (REPORT). Nếu báo lỗi sẽ tự động tạo Ticket gửi Admin"""
    return ChatService.submit_feedback(db, req)
