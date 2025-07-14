import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Float,
    DateTime,
    Date,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# --- ENUM Definitions ---
# Using Enums is excellent practice for data integrity.

class BackfillStatus(enum.Enum):
    """Tracks the status of a user's historical Strava activity import."""
    PENDING = "PENDING"      # User has signed up but not yet connected Strava.
    QUEUED = "QUEUED"        # User connected Strava, backfill is ready to start.
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class PRDistance(enum.Enum):
    """
    Defines the specific, official distances for Personal Records.
    This prevents data inconsistency from free-form strings like '1k' vs '1km'.
    """
    METER_400 = "400m"
    METER_800 = "800m"
    KM_1 = "1km"
    MILE_1 = "1 Mile"
    KM_5 = "5km"
    KM_10 = "10km"
    HALF_MARATHON = "Half Marathon"
    MARATHON = "Marathon"


# --- Table Model Definitions ---

class User(Base):
    """
    The central user model for your application. Identity is now based on X.com OAuth.
    A user can exist before ever connecting their Strava account.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    
    # X.com OAuth fields (primary identity)
    x_user_id = Column(String(50), unique=True, nullable=False, index=True)  # X's user ID
    x_username = Column(String(255), nullable=False, index=True)  # @username
    x_display_name = Column(String(255))  # Display name from X
    
    # Optional fields - can be populated from X profile or user input
    email = Column(String(255), unique=True, nullable=True, index=True) 
    username = Column(String(255), unique=True, nullable=True, index=True)
    
    # Strava-specific link. Nullable until the user connects their account.
    # Unique ensures one Strava account can only be linked to one user.
    strava_athlete_id = Column(BigInteger, unique=True, nullable=True, index=True)
    
    profile_picture_url = Column(String(512))
    backfill_status = Column(SQLAlchemyEnum(BackfillStatus), default=BackfillStatus.PENDING, nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # --- Relationships ---
    # Defines how this User object connects to other tables.
    x_authorization = relationship("XAuthorization", back_populates="user", uselist=False, cascade="all, delete-orphan")
    strava_authorization = relationship("StravaAuthorization", back_populates="user", uselist=False, cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")
    personal_records = relationship("PersonalRecord", back_populates="user", cascade="all, delete-orphan")
    # This relationship is added for convenience to easily access all best efforts for a user.
    best_efforts = relationship("ActivityBestEffort", back_populates="user", cascade="all, delete-orphan")

class XAuthorization(Base):
    """Stores the secure OAuth tokens for a user's X.com account."""
    __tablename__ = "x_authorizations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # NOTE: These fields store the *encrypted* tokens.
    access_token = Column(String(512), nullable=False)
    refresh_token = Column(String(512))  # X OAuth 2.0 may not always provide refresh tokens
    
    token_expires_at = Column(DateTime)
    scopes = Column(String(512))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="x_authorization")


class StravaAuthorization(Base):
    """Stores the secure OAuth tokens for a user's linked Strava account."""
    __tablename__ = "strava_authorizations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # NOTE: These fields store the *encrypted* tokens.
    access_token = Column(String(512), nullable=False)
    refresh_token = Column(String(512), nullable=False)
    
    token_expires_at = Column(DateTime, nullable=False)
    scopes = Column(String(512))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="strava_authorization")


class Activity(Base):
    """Stores the high-level data for a single imported Strava activity."""
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    strava_activity_id = Column(BigInteger, nullable=False, index=True)
    
    name = Column(String(255))
    total_distance_meters = Column(Float)
    moving_time_seconds = Column(Integer)
    total_elevation_gain_meters = Column(Float)
    activity_start_date = Column(DateTime, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "strava_activity_id", name="uq_user_strava_activity"),)

    user = relationship("User", back_populates="activities")
    best_efforts = relationship("ActivityBestEffort", back_populates="activity", cascade="all, delete-orphan")
    source_for_prs = relationship("PersonalRecord", back_populates="source_activity")


class ActivityBestEffort(Base):
    """
    Stores every individual best effort found within a single activity.
    There will be many rows here for each row in the 'activities' table.
    """
    __tablename__ = "activity_best_efforts"

    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False, index=True)
    # MODIFICATION: Added a direct user_id link for much faster querying.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    distance = Column(SQLAlchemyEnum(PRDistance), nullable=False)
    elapsed_time_seconds = Column(Integer, nullable=False)

    activity = relationship("Activity", back_populates="best_efforts")
    # MODIFICATION: Added the corresponding relationship for the new user_id column.
    user = relationship("User", back_populates="best_efforts")


class PersonalRecord(Base):
    """
    The final 'display' table. Stores only a user's single best time for each
    official distance, calculated from all their historical data.
    """
    __tablename__ = "personal_records"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # Link to the activity where this PR was actually set.
    source_activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    
    distance = Column(SQLAlchemyEnum(PRDistance), nullable=False)
    elapsed_time_seconds = Column(Integer, nullable=False)
    achieved_on = Column(Date, nullable=False)
    
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (UniqueConstraint("user_id", "distance", name="uq_user_distance_pr"),)

    user = relationship("User", back_populates="personal_records")
    source_activity = relationship("Activity", back_populates="source_for_prs")