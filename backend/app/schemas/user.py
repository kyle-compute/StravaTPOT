from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    strava_athlete_id: Optional[int] = None
    profile_picture_url: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    profile_picture_url: Optional[str] = None