import logging
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.knowledge import EvidenceCard, EvidenceVector, KnowledgeSource

logger = logging.getLogger(__name__)

class EvidenceRepository:
    @staticmethod
    def get_by_id(db: Session, card_id: str) -> Optional[EvidenceCard]:
        return db.query(EvidenceCard).filter(EvidenceCard.card_id == card_id).first()

    @staticmethod
    def count_cards(db: Session) -> int:
        return db.query(EvidenceCard).count()

    @staticmethod
    def list_cards(
        db: Session,
        country: Optional[str] = None,
        domain: Optional[str] = None,
        q: Optional[str] = None,
        status: str = "APPROVED"
    ) -> List[EvidenceCard]:
        query = db.query(EvidenceCard).filter(EvidenceCard.status == status)

        if country and country != "ALL":
            query = query.filter(EvidenceCard.country_code == country)
        if domain and domain != "ALL":
            query = query.filter(EvidenceCard.domain_id == domain)
        if q and q.strip():
            term = f"%{q.strip().lower()}%"
            query = query.filter(
                (EvidenceCard.title.ilike(term)) |
                (EvidenceCard.context.ilike(term)) |
                (EvidenceCard.verified_content.ilike(term))
            )

        return query.order_by(EvidenceCard.reliability_score.desc()).all()

    @staticmethod
    def create_card(db: Session, card: EvidenceCard) -> EvidenceCard:
        db.add(card)
        db.commit()
        db.refresh(card)
        return card

    @staticmethod
    def save_vector(db: Session, card_id: str, embedding: List[float], model: str = "bge-m3") -> EvidenceVector:
        existing = db.query(EvidenceVector).filter(EvidenceVector.card_id == card_id).first()
        if existing:
            setattr(existing, "embedding", embedding)
            setattr(existing, "embedding_model", model)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            vec_rec = EvidenceVector(
                card_id=card_id,
                embedding_model=model,
                embedding=embedding
            )
            db.add(vec_rec)
            db.commit()
            db.refresh(vec_rec)
            return vec_rec

    @staticmethod
    def get_master_sources(db: Session) -> List[KnowledgeSource]:
        return db.query(KnowledgeSource).order_by(KnowledgeSource.reliability_score.desc()).all()

    @staticmethod
    def search_hybrid(
        db: Session,
        query: str,
        country: str,
        query_vector: List[float],
        limit: int = 3
    ) -> List[Tuple[EvidenceCard, float]]:
        """
        Dynamic Hybrid Search kết hợp:
        1. Dense Vector Cosine Similarity (pgvector)
        2. Sparse Fuzzy Trigram Matching (pg_trgm) - chống lỗi chính tả (typo tolerance)
        3. Full-Text Search Rank (ts_rank) - nhận diện từ ngữ chính xác
        Tất cả tính toán trực tiếp trên PostgreSQL, không cần hardcode từ khóa hay bản đồ tĩnh.
        """
        vec_str = "[" + ",".join(str(x) for x in query_vector) + "]"
        clean_query = query.strip()

        sql = text("""
            SELECT 
                ec.card_id,
                -- 1. Điểm cosine similarity từ pgvector [0.0 -> 1.0]
                COALESCE(1.0 - (ev.embedding <=> CAST(:vec AS vector)), 0.0) AS vec_score,
                -- 2. Điểm trigram fuzzy similarity (chịu lỗi gõ phím/chính tả) [0.0 -> 1.0]
                GREATEST(
                    similarity(ec.title, :q),
                    similarity(ec.verified_content, :q),
                    similarity(ec.safe_action, :q)
                ) AS trigram_score,
                -- 3. Điểm full-text ts_rank [0.0 -> 1.0]
                COALESCE(
                    ts_rank(
                        to_tsvector('simple', ec.title || ' ' || ec.verified_content || ' ' || ec.safe_action),
                        plainto_tsquery('simple', :q)
                    ),
                    0.0
                ) AS ft_score
            FROM evidence_cards ec
            LEFT JOIN evidence_vectors ev ON ec.card_id = ev.card_id
            WHERE ec.country_code = :country 
              AND ec.status = 'APPROVED'
        """)

        try:
            rows = db.execute(sql, {
                "vec": vec_str,
                "q": clean_query,
                "country": country
            }).fetchall()

            scored_cards = []
            for row in rows:
                card_id = row[0]
                vec_s = float(row[1]) if row[1] is not None else 0.0
                tri_s = float(row[2]) if row[2] is not None else 0.0
                ft_s = float(row[3]) if row[3] is not None else 0.0
                # Trọng số phối hợp đa tầng (Dynamic Hybrid Fusion):
                # 1. Cosine Vector (không gian ngữ nghĩa): max ~0.45
                # 2. Trigram Fuzzy (chống lỗi chính tả & từ đồng nghĩa): max ~0.40
                # 3. Full-Text Search Rank (từ ngữ chính xác): max ~0.20
                raw_score = (0.50 * vec_s) + (0.30 * tri_s) + (0.20 * min(ft_s * 2.5, 1.0))
                # Chuẩn hóa về thang đo độ tin cậy [0.0 -> 1.0]
                normalized_score = min(raw_score * 2.0, 1.0)
                scored_cards.append((card_id, normalized_score))

            # Sắp xếp giảm dần theo composite score
            scored_cards.sort(key=lambda x: x[1], reverse=True)

            top_results = []
            for card_id, score in scored_cards[:limit]:
                card = db.query(EvidenceCard).filter(EvidenceCard.card_id == card_id).first()
                if card:
                    top_results.append((card, score))

            return top_results

        except Exception as e:
            logger.error(f"Lỗi truy vấn hybrid search trong EvidenceRepository: {e}")
            db.rollback()
            return []
