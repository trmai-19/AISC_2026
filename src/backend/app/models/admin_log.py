from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class AdminQueueLog(Base):
    __tablename__ = "admin_queue_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    admin_user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    reference_id = Column(String(50), nullable=False, index=True)
    action_taken = Column(String(20), nullable=False)  # APPROVE, REJECT
    processed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    admin_user = relationship("User")
