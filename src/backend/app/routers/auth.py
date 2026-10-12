from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user_schema import (
    UserProfileUpdate,
    LoginRequest,
    RegisterRequest,
    AuthResponse
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth & User Profiles"])

@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Xác thực đăng nhập người dùng từ CSDL thực tế"""
    return AuthService.login(db, req)

@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Đăng ký tài khoản thành viên mới và khởi tạo hồ sơ ngữ cảnh ban đầu"""
    return AuthService.register(db, req)

@router.get("/me", response_model=AuthResponse)
def get_current_user(user_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Lấy thông tin người dùng hiện tại"""
    return AuthService.get_current_user(db, user_id)

@router.put("/profile")
def update_profile(req: UserProfileUpdate, db: Session = Depends(get_db)):
    """Cập nhật hồ sơ ngữ cảnh cá nhân hóa của người dùng"""
    return AuthService.update_profile(db, req)
