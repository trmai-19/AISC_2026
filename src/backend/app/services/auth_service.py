import uuid
from datetime import datetime
from typing import Optional
import bcrypt
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.repositories.user_repository import UserRepository
from app.models.user import User, UserProfile
from app.schemas.user_schema import (
    LoginRequest,
    RegisterRequest,
    AuthResponse,
    UserProfileSchema,
    UserProfileUpdate
)

def hash_password(password: str) -> str:
    """Mã hóa mật khẩu bằng thuật toán bcrypt với salt bảo mật cao"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu người dùng với chuỗi hash bcrypt trong CSDL"""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

class AuthService:
    @staticmethod
    def login(db: Session, req: LoginRequest) -> AuthResponse:
        clean_email = req.email.strip().lower()
        user = UserRepository.get_by_email(db, clean_email)
        if not user:
            raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không chính xác.")

        # Xác thực mật khẩu thực tế bằng bcrypt
        if not verify_password(req.password, str(user.password_hash or "")):
            raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không chính xác.")

        profile_schema = None
        if user.profile:
            profile_schema = UserProfileSchema(
                target_country=user.profile.target_country or "JP",
                purpose=user.profile.purpose or "DU_HOC",
                stage=user.profile.stage or "PREPARING"
            )

        return AuthResponse(
            status="success",
            message="Đăng nhập thành công",
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            token=f"token-{user.user_id[:8]}",
            profile=profile_schema
        )

    @staticmethod
    def register(db: Session, req: RegisterRequest) -> AuthResponse:
        clean_email = req.email.strip().lower()
        existing = UserRepository.get_by_email(db, clean_email)
        if existing:
            raise HTTPException(status_code=400, detail="Email này đã được đăng ký trong hệ thống.")

        # Mã hóa mật khẩu người dùng thực tế
        hashed_pw = hash_password(req.password)

        new_user_id = f"usr-2026-{uuid.uuid4().hex[:12]}"
        new_user = User(
            user_id=new_user_id,
            email=clean_email,
            password_hash=hashed_pw,
            full_name=req.full_name.strip(),
            role="USER",
            created_at=datetime.utcnow()
        )
        new_profile = UserProfile(
            user_id=new_user_id,
            target_country=req.target_country or "JP",
            purpose=req.purpose or "DU_HOC",
            stage=req.stage or "PREPARING"
        )

        user = UserRepository.create_user(db, new_user, new_profile)

        return AuthResponse(
            status="success",
            message="Đăng ký tài khoản thành công!",
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            token=f"token-{user.user_id[:8]}",
            profile=UserProfileSchema(
                target_country=new_profile.target_country,
                purpose=new_profile.purpose,
                stage=new_profile.stage
            )
        )

    @staticmethod
    def get_current_user(db: Session, user_id: Optional[str]) -> AuthResponse:
        if not user_id or user_id == "00000000-0000-0000-0000-000000000000":
            return AuthResponse(
                status="success",
                message="Khách vãng lai",
                user_id="00000000-0000-0000-0000-000000000000",
                email="guest@aisc.vn",
                full_name="Khách Vãng Lai",
                role="GUEST",
                profile=UserProfileSchema(target_country="JP", purpose="DU_HOC", stage="PREPARING")
            )

        user = UserRepository.get_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

        profile_schema = None
        if user.profile:
            profile_schema = UserProfileSchema(
                target_country=user.profile.target_country or "JP",
                purpose=user.profile.purpose or "DU_HOC",
                stage=user.profile.stage or "PREPARING"
            )

        return AuthResponse(
            status="success",
            message="Thành công",
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            profile=profile_schema
        )

    @staticmethod
    def update_profile(db: Session, req: UserProfileUpdate) -> dict:
        UserRepository.update_profile(
            db=db,
            user_id=req.user_id,
            target_country=req.target_country or "JP",
            purpose=req.purpose or "DU_HOC",
            stage=req.stage or "PREPARING"
        )
        return {"status": "success", "message": "Đã lưu hồ sơ ngữ cảnh thành công"}
