from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.contribution import CommunityContribution, ContributionChallenge

class ContributionRepository:
    @staticmethod
    def get_by_id(db: Session, contribution_id: str) -> Optional[CommunityContribution]:
        return db.query(CommunityContribution).filter(
            CommunityContribution.contribution_id == contribution_id
        ).first()

    @staticmethod
    def count_contributions(db: Session) -> int:
        return db.query(CommunityContribution).count()

    @staticmethod
    def create_contribution(
        db: Session,
        contribution: CommunityContribution,
        challenges: Optional[List[str]] = None
    ) -> CommunityContribution:
        db.add(contribution)
        db.flush()

        if challenges:
            for code in challenges:
                challenge = ContributionChallenge(
                    contribution_id=contribution.contribution_id,
                    challenge_code=code
                )
                db.add(challenge)

        db.commit()
        db.refresh(contribution)
        return contribution

    @staticmethod
    def get_review_queue(
        db: Session,
        status: Optional[str] = "PENDING",
        subfilter: Optional[str] = "ALL",
        limit: int = 100
    ) -> List[CommunityContribution]:
        query = db.query(CommunityContribution)

        if status == "PENDING":
            query = query.filter(CommunityContribution.status == "PENDING")
        else:
            query = query.filter(CommunityContribution.status != "PENDING")
            if subfilter in ["APPROVED", "REJECTED"]:
                query = query.filter(CommunityContribution.status == subfilter)

        return query.order_by(CommunityContribution.submitted_at.desc()).limit(limit).all()

    @staticmethod
    def update_status(db: Session, contribution_id: str, new_status: str) -> Optional[CommunityContribution]:
        item = db.query(CommunityContribution).filter(
            CommunityContribution.contribution_id == contribution_id
        ).first()
        if item:
            setattr(item, "status", new_status)
            db.commit()
            db.refresh(item)
        return item
