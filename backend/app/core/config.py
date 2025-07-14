import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/strava_leaderboard")
    
    
    # X.com OAuth 2.0 settings
    x_client_id: Optional[str] = os.getenv("X_CLIENT_ID")
    x_client_secret: Optional[str] = os.getenv("X_CLIENT_SECRET")
    x_redirect_uri: Optional[str] = os.getenv("X_REDIRECT_URI")
    
    strava_client_id: Optional[str] = os.getenv("STRAVA_CLIENT_ID")
    strava_client_secret: Optional[str] = os.getenv("STRAVA_CLIENT_SECRET")
    strava_redirect_uri: Optional[str] = os.getenv("STRAVA_REDIRECT_URI")
    
    environment: str = os.getenv("ENVIRONMENT", "development")

    class Config:
        env_file = ".env"


settings = Settings()