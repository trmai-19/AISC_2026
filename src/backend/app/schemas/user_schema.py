from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict

class UserBase(BaseModel):
    email: str
    full_name: str
    role: Literal["GUEST", "USER", "ADMIN"]

class UserProfileSchema(BaseModel):
    target_country: Optional[str] = "JP"
    purpose: Optional[Literal["DU_HOC", "LAO_DONG", "DINH_CU"]] = "DU_HOC"
    stage: Optional[str] = "PREPARING"

    model_config = ConfigDict(from_attributes=True)

class UserResponse(UserBase):
    user_id: str
    created_at: datetime
    profile: Optional[UserProfileSchema] = None

    model_config = ConfigDict(from_attributes=True)

class SwitchRoleRequest(BaseModel):
    role: Literal["GUEST", "USER", "ADMIN"]
    user_id: Optional[str] = None

class UserProfileUpdate(BaseModel):
    user_id: str
    target_country: Optional[str] = "JP"
    purpose: Optional[str] = "DU_HOC"
    stage: Optional[str] = "PREPARING"

# Schemas phục vụ luồng Đăng nhập & Đăng ký
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    target_country: Optional[str] = "JP"
    purpose: Optional[Literal["DU_HOC", "LAO_DONG", "DINH_CU"]] = "DU_HOC"
    stage: Optional[str] = "PREPARING"

class AuthResponse(BaseModel):
    status: str
    message: str
    user_id: str
    email: str
    full_name: str
    role: str
    token: Optional[str] = None
    profile: Optional[UserProfileSchema] = None
