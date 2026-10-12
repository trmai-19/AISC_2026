from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserProfile
from app.schemas.user_schema import UserResponse, SwitchRoleRequest, UserProfileUpdate

router = APIRouter(prefix="/auth", tags=["Auth & User Profiles"])

ROLE_PRESETS = {
    "GUEST": {
        "user_id": "00000000-0000-0000-0000-000000000000",
        "email": "guest@aisc.vn",
        "full_name": "Khách Vãng Lai",
        "role": "GUEST"
    },
    "USER": {
        "user_id": "usr-2026-0000-0000-000000000001",
        "email": "respondent.1@survey.aisc.vn",
        "full_name": "Nguyễn Văn An",
        "role": "USER"
    },
    "ADMIN": {
        "user_id": "11111111-aaaa-0000-0000-000000000001",
        "email": "phuctrandinh2006@gmail.com",
        "full_name": "Trần Đình Phúc",
        "role": "ADMIN"
    }
}

@router.get("/users")
def get_sample_users(db: Session = Depends(get_db)):
    """Lấy danh sách các tài khoản người dùng mẫu"""
    users = db.query(User).limit(10).all()
    if not users:
        return list(ROLE_PRESETS.values())
    return [
        {
            "user_id": u.user_id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "profile": {
                "target_country": u.profile.target_country if u.profile else "JP",
                "purpose": u.profile.purpose if u.profile else "DU_HOC",
                "stage": u.profile.stage if u.profile else "PREPARING"
            } if u.profile else None
        }
        for u in users
    ]

@router.post("/switch-role")
def switch_role(req: SwitchRoleRequest, db: Session = Depends(get_db)):
    """Chuyển đổi vai trò người dùng kiểm thử (Guest, Member, Admin)"""
    role = req.role
    if role not in ROLE_PRESETS:
        raise HTTPException(status_code=400, detail="Vai trò không hợp lệ")

    preset = ROLE_PRESETS[role]
    # Tìm hoặc dùng mock user
    user = db.query(User).filter(User.user_id == preset["user_id"]).first()
    if user:
        return {
            "status": "success",
            "user_id": user.user_id,
            "full_name": user.full_name,
            "role": user.role,
            "email": user.email
        }
    return {
        "status": "success",
        **preset
    }

@router.put("/profile")
def update_profile(req: UserProfileUpdate, db: Session = Depends(get_db)):
    """Cập nhật ngữ cảnh cá nhân hóa của người dùng"""
    profile = db.query(UserProfile).filter(UserProfile.user_id == req.user_id).first()
    if not profile:
        profile = UserProfile(
            user_id=req.user_id,
            target_country=req.target_country,
            purpose=req.purpose,
            stage=req.stage
        )
        db.add(profile)
    else:
        profile.target_country = req.target_country
        profile.purpose = req.purpose
        profile.stage = req.stage
    db.commit()
    return {"status": "success", "message": "Đã lưu hồ sơ ngữ cảnh thành công"}
