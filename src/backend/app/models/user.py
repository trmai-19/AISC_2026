from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="USER")  # GUEST, USER, ADMIN
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    contributions = relationship("CommunityContribution", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship("UserFeedback", back_populates="user", cascade="all, delete-orphan")
    chat_logs = relationship("ChatHistory", back_populates="user")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    profile_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False)
    target_country = Column(String(10), nullable=True)  # JP, KR, AU
    purpose = Column(String(50), nullable=True)         # DU_HOC, LAO_DONG, DINH_CU
    stage = Column(String(50), nullable=True)           # PREPARING, RECENT_ARRIVED, LIVING_STUDYING, RETURNED

    # Relationship
    user = relationship("User", back_populates="profile")
