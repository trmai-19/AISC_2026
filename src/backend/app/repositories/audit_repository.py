from typing import List
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.admin_log import AdminQueueLog

class AuditRepository:
    @staticmethod
    def save_audit_log(
        db: Session,
        admin_user_id: str,
        reference_id: str,
        action_taken: str
    ) -> AdminQueueLog:
        log = AdminQueueLog(
            admin_user_id=admin_user_id,
            reference_id=reference_id,
            action_taken=action_taken,
            processed_at=datetime.utcnow()
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def list_logs(db: Session, limit: int = 50) -> List[AdminQueueLog]:
        return (
            db.query(AdminQueueLog)
            .order_by(AdminQueueLog.processed_at.desc())
            .limit(limit)
            .all()
        )
