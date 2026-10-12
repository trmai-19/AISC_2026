from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.admin_schema import AdminQueueItemResponse, QueueActionRequest
from app.schemas.evidence_schema import KnowledgeSourceResponse
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["Admin Service & Review Queue"])

@router.get("/queue", response_model=List[AdminQueueItemResponse])
def get_review_queue(
    status: Optional[str] = Query("PENDING", description="Lọc theo trạng thái: PENDING hoặc PROCESSED"),
    subfilter: Optional[str] = Query("ALL", description="Lọc con: ALL, APPROVED, REJECTED"),
    db: Session = Depends(get_db)
):
    """Lấy danh sách hàng đợi kiểm duyệt (Chờ duyệt hoặc Lịch sử đã xử lý)"""
    return AdminService.get_review_queue(db, status=status, subfilter=subfilter)

@router.post("/queue/{contribution_id}/action")
def process_queue_action(
    contribution_id: str,
    req: QueueActionRequest,
    db: Session = Depends(get_db)
):
    """
    Xử lý kiểm duyệt: APPROVE hoặc REJECT.
    Khi APPROVE: Tự động thăng hạng bài thành Evidence Card chính thức và sinh vector nhúng!
    """
    return AdminService.process_queue_action(db, contribution_id, req)

@router.get("/sources", response_model=List[KnowledgeSourceResponse])
def get_master_sources(db: Session = Depends(get_db)):
    """Lấy danh mục Master Data các nguồn đối soát chính thống"""
    return AdminService.get_master_sources(db)
