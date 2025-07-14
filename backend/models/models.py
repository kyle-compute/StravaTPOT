import enum
from datetime import datetime

from sqlalchemy import (
    create_engine,
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



class BackfillStatus(enum.Enum):
    """Tracks the status of a user's historical activity import."""
    PENDING = "PENDING"
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


# --- Table Definitions ---

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    strava_athlete_id = Column(BigInteger, unique=True, nullable=False, index=True)

    email = Column(String(255), unique=True, nullable=True, index=True) 
    
    username = Column(String(255))
    profile_picture_url = Column(String(512))
    
    # Status of the overall backfill process
    backfill_status = Column(SQLAlchemyEnum(BackfillStatus), default=BackfillStatus.PENDING, nullable=False)
    
    # Timestamp of the oldest activity backfilled so far. 
    backfill_oldest_activity_date = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    authorization = relationship("StravaAuthorization", back_populates="user", uselist=False, cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")
    personal_records = relationship("PersonalRecord", back_populates="user", cascade="all, delete-orphan")
class StravaAuthorization(Base):
    __tablename__ = "strava_authorizations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # CRITICAL: These tokens should be encrypted in your application before storing.
    access_token = Column(String(512), nullable=False)
    refresh_token = Column(String(512), nullable=False)
    
    token_expires_at = Column(DateTime, nullable=False)
    scopes = Column(String(512))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="authorization")


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    strava_activity_id = Column(BigInteger, nullable=False, index=True)
    
    name = Column(String(255))
    total_distance_meters = Column(Float)
    moving_time_seconds = Column(Integer)
    total_elevation_gain_meters = Column(Float)
    activity_start_date = Column(DateTime, nullable=False)

    # A user cannot have the same activity imported twice.
    __table_args__ = (UniqueConstraint("user_id", "strava_activity_id", name="uq_user_strava_activity"),)

    # Relationships
    user = relationship("User", back_populates="activities")
    best_efforts = relationship("ActivityBestEffort", back_populates="activity", cascade="all, delete-orphan")
    # An activity can be the source for multiple PRs (e.g., a 5k PR set during a 10k run)
    source_for_prs = relationship("PersonalRecord", back_populates="source_activity")


class ActivityBestEffort(Base):
    __tablename__ = "activity_best_efforts"

    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False, index=True)
    
    # Using an ENUM for the distance ensures data consistency.
    distance = Column(SQLAlchemyEnum(PRDistance), nullable=False)
    elapsed_time_seconds = Column(Integer, nullable=False)

    # Relationships
    activity = relationship("Activity", back_populates="best_efforts")


class PersonalRecord(Base):
    __tablename__ = "personal_records"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    
    distance = Column(SQLAlchemyEnum(PRDistance), nullable=False)
    elapsed_time_seconds = Column(Integer, nullable=False)
    achieved_on = Column(Date, nullable=False)
    
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # A user can only have one official PR for each distance type.
    __table_args__ = (UniqueConstraint("user_id", "distance", name="uq_user_distance_pr"),)

    # Relationships
    user = relationship("User", back_populates="personal_records")
    source_activity = relationship("Activity", back_populates="source_for_prs")