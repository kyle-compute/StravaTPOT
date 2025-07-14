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
    Enum,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Define the ENUM type for backfill status
class BackfillStatus(enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    strava_athlete_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255))
    profile_picture_url = Column(String(512))
    backfill_status = Column(Enum(BackfillStatus), default=BackfillStatus.PENDING)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    # A User has one StravaAuthorization (one-to-one)
    authorization = relationship("StravaAuthorization", back_populates="user", uselist=False, cascade="all, delete-orphan")
    # A User has many Activities (one-to-many)
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")
    # A User has many PersonalRecords (one-to-many)
    personal_records = relationship("PersonalRecord", back_populates="user", cascade="all, delete-orphan")
    # A User has many best efforts (convenience relationship)
    best_efforts = relationship("ActivityBestEffort", back_populates="user", cascade="all, delete-orphan")


class StravaAuthorization(Base):
    __tablename__ = "strava_authorizations"

    id = Column(Integer, primary_key=True)
    # The one-to-one link to the User
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # NOTE: These should be encrypted before being stored.
    # The database stores the encrypted string.
    access_token = Column(String(512), nullable=False)
    refresh_token = Column(String(512), nullable=False)
    
    token_expires_at = Column(DateTime, nullable=False)
    scopes = Column(String(512))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship back to User
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

    # Unique constraint per user
    __table_args__ = (UniqueConstraint("user_id", "strava_activity_id", name="uq_user_strava_activity"),)

    # Relationships
    user = relationship("User", back_populates="activities")
    # An Activity has many best efforts (one-to-many)
    best_efforts = relationship("ActivityBestEffort", back_populates="activity", cascade="all, delete-orphan")


class ActivityBestEffort(Base):
    __tablename__ = "activity_best_efforts"

    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # Denormalized for faster queries
    
    distance_name = Column(String(50), nullable=False)
    elapsed_time_seconds = Column(Integer, nullable=False)

    # Relationships
    activity = relationship("Activity", back_populates="best_efforts")
    user = relationship("User", back_populates="best_efforts")


class PersonalRecord(Base):
    __tablename__ = "personal_records"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    distance_name = Column(String(50), nullable=False)
    elapsed_time_seconds = Column(Integer, nullable=False)
    
    # Link to the activity where the PR was set
    source_activity_id = Column(Integer, ForeignKey("activities.id"))
    achieved_on = Column(Date)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # A user can only have one PR for each distance
    __table_args__ = (UniqueConstraint("user_id", "distance_name", name="uq_user_distance_pr"),)

    # Relationships
    user = relationship("User", back_populates="personal_records")
    source_activity = relationship("Activity")