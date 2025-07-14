from typing import Optional
from pydantic import BaseModel


class XAuthInitiate(BaseModel):
    """Response for initiating X.com OAuth flow"""
    auth_url: str
    state: str


class XAuthCallback(BaseModel):
    """Request body for X.com OAuth callback"""
    code: Optional[str] = None
    state: str
    error: Optional[str] = None
    error_description: Optional[str] = None


class UserToken(BaseModel):
    """Response after successful authentication"""
    access_token: str
    token_type: str
    user_id: int
    x_username: str
    x_display_name: Optional[str] = None


class StravaConnectInitiate(BaseModel):
    """Response for initiating Strava OAuth flow"""
    auth_url: str
    state: str


class StravaCallback(BaseModel):
    """Request body for Strava OAuth callback"""
    code: Optional[str] = None
    state: str
    error: Optional[str] = None
    error_description: Optional[str] = None