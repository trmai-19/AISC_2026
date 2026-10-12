from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.chat import ChatHistory, UserFeedback

class ChatRepository:
    @staticmethod
    def save_message(
        db: Session,
        user_id: Optional[str],
        sender_type: str,
        content: str,
        matched_card_id: Optional[str] = None
    ) -> ChatHistory:
        msg = ChatHistory(
            user_id=user_id,
            sender_type=sender_type,
            content=content,
            matched_card_id=matched_card_id,
            created_at=datetime.utcnow()
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg

    @staticmethod
    def get_history(db: Session, user_id: str, limit: int = 20) -> List[ChatHistory]:
        logs = (
            db.query(ChatHistory)
            .filter(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.created_at.desc())
            .limit(limit)
            .all()
        )
        return logs[::-1]  # Thời gian tăng dần

    @staticmethod
    def save_feedback(
        db: Session,
        user_id: str,
        evidence_card_id: str,
        feedback_type: str
    ) -> UserFeedback:
        feedback = UserFeedback(
            user_id=user_id,
            evidence_card_id=evidence_card_id,
            feedback_type=feedback_type,
            created_at=datetime.utcnow()
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        return feedback
