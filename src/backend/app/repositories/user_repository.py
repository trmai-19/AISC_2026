from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.user import User, UserProfile

class UserRepository:
    @staticmethod
    def get_by_id(db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.user_id == user_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        clean_email = email.strip().lower()
        return db.query(User).filter(User.email == clean_email).first()

    @staticmethod
    def create_user(db: Session, user: User, profile: Optional[UserProfile] = None) -> User:
        db.add(user)
        db.flush()
        if profile:
            db.add(profile)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_profile(
        db: Session,
        user_id: str,
        target_country: str = "JP",
        purpose: str = "DU_HOC",
        stage: str = "PREPARING"
    ) -> UserProfile:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            profile = UserProfile(
                user_id=user_id,
                target_country=target_country,
                purpose=purpose,
                stage=stage
            )
            db.add(profile)
        else:
            setattr(profile, "target_country", target_country)
            setattr(profile, "purpose", purpose)
            setattr(profile, "stage", stage)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def get_first_user(db: Session) -> Optional[User]:
        return db.query(User).first()

    @staticmethod
    def get_sample_users(db: Session, limit: int = 10) -> List[User]:
        return db.query(User).limit(limit).all()
