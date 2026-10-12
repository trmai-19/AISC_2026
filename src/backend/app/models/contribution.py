from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class CommunityContribution(Base):
    __tablename__ = "community_contributions"

    contribution_id = Column(String(50), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    country_code = Column(String(10), nullable=False, index=True)
    domain_id = Column(String(50), nullable=False, index=True)
    exp_title = Column(String(255), nullable=False)
    exp_text = Column(Text, nullable=False)
    prep_level = Column(Integer, nullable=True)     # 1 - 5
    use_intention = Column(Integer, nullable=True)  # 1 - 5
    status = Column(String(20), nullable=False, default="PENDING", index=True)  # PENDING, APPROVED, REJECTED
    submitted_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="contributions")
    challenges = relationship("ContributionChallenge", back_populates="contribution", cascade="all, delete-orphan")

class ContributionChallenge(Base):
    __tablename__ = "contribution_challenges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contribution_id = Column(String(50), ForeignKey("community_contributions.contribution_id", ondelete="CASCADE"), nullable=False)
    challenge_code = Column(String(50), nullable=False)

    contribution = relationship("CommunityContribution", back_populates="challenges")

    __table_args__ = (
        UniqueConstraint('contribution_id', 'challenge_code', name='uq_cch_contribution_code'),
    )
