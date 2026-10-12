from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, ConfigDict

class UserBase(BaseModel):
    email: EmailStr
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
