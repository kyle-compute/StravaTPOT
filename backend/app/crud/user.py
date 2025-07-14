from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from models.models import User
from app.schemas.user import UserCreate


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email address."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_strava_id(db: Session, strava_id: int) -> Optional[User]:
    """Get user by Strava athlete ID."""
    return db.query(User).filter(User.strava_athlete_id == strava_id).first()


def get_user_by_x_id(db: Session, x_user_id: str) -> Optional[User]:
    """Get user by X.com user ID."""
    return db.query(User).filter(User.x_user_id == x_user_id).first()


def create_user_from_x(db: Session, x_user_data: Dict[str, Any]) -> User:
    """Create a new user from X.com OAuth data."""
    db_user = User(
        x_user_id=x_user_data['id'],
        x_username=x_user_data['username'],
        x_display_name=x_user_data.get('name'),
        profile_picture_url=x_user_data.get('profile_image_url')
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_user(db: Session, user: UserCreate) -> User:
    """Create a new user (for OAuth)."""
    db_user = User(
        email=user.email,
        username=user.username
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user