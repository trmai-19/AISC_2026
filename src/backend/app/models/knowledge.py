from datetime import datetime, date
from sqlalchemy import Column, String, Integer, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.database import Base

class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    source_id = Column(String(50), primary_key=True)
    country_code = Column(String(10), nullable=False, index=True)
    organization_name = Column(String(150), nullable=False)
    source_type = Column(String(100), nullable=False)
    document_title = Column(String(255), nullable=False)
    document_url = Column(Text, nullable=True)
    published_date = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)
    reliability_score = Column(Integer, default=98)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    evidence_cards = relationship("EvidenceCard", back_populates="source")

class EvidenceCard(Base):
    __tablename__ = "evidence_cards"

    card_id = Column(String(50), primary_key=True, index=True)
    source_id = Column(String(50), ForeignKey("knowledge_sources.source_id", ondelete="SET NULL"), nullable=True)
    country_code = Column(String(10), nullable=False, index=True)
    domain_id = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    context = Column(Text, nullable=False)
    verified_content = Column(Text, nullable=False)
    safe_action = Column(Text, nullable=False)
    donots = Column(Text, nullable=False)
    reliability_score = Column(Integer, default=95)
    confidence_level = Column(String(50), default="Rất cao (98%)")
    status = Column(String(20), nullable=False, default="APPROVED", index=True)
    verified_date = Column(Date, default=date.today)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    source = relationship("KnowledgeSource", back_populates="evidence_cards")
    vector_record = relationship("EvidenceVector", back_populates="card", uselist=False, cascade="all, delete-orphan")

class EvidenceVector(Base):
    __tablename__ = "evidence_vectors"

    vector_id = Column(Integer, primary_key=True, autoincrement=True)
    card_id = Column(String(50), ForeignKey("evidence_cards.card_id", ondelete="CASCADE"), unique=True, nullable=False)
    embedding_model = Column(String(50), nullable=False, default="bge-m3")
    embedding = Column(Vector(768), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    card = relationship("EvidenceCard", back_populates="vector_record")
