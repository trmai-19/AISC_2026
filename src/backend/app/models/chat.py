from datetime import datetime
from sqlalchemy import Column, String, Integer, BigInteger, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class ChatHistory(Base):
    __tablename__ = "chat_history"

    message_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    sender_type = Column(String(10), nullable=False)  # USER, BOT
    content = Column(Text, nullable=False)
    matched_card_id = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="chat_logs")

class UserFeedback(Base):
    __tablename__ = "user_feedbacks"

    feedback_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    evidence_card_id = Column(String(50), nullable=False, index=True)
    feedback_type = Column(String(20), nullable=False)  # LIKE, REPORT
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="feedbacks")
