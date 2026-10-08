"""
SQLAlchemy database models.

These models must remain consistent with the PostgreSQL tables
stored in Supabase.
"""

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    email = Column(
        String(255),
        unique=True,
        nullable=False,
    )

    password_hash = Column(
        String(255),
        nullable=False,
    )

    display_name = Column(
        String(100),
        nullable=True,
    )

    role = Column(
        String(20),
        nullable=False,
        default="citizen",
    )

    created_at = Column(
        TIMESTAMP,
        server_default=func.now(),
    )


class Report(Base):
    __tablename__ = "reports"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    submitted_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    submitted_by_uuid = Column(
        UUID(as_uuid=False),
        nullable=True,
    )

    reporter_name = Column(
        String(100),
        nullable=True,
    )

    reporter_email = Column(
        String(255),
        nullable=True,
    )

    reporter_phone = Column(
        String(30),
        nullable=True,
    )

    image_url = Column(
        Text,
        nullable=False,
    )

    latitude = Column(
        Float,
        nullable=False,
    )

    longitude = Column(
        Float,
        nullable=False,
    )

    # Optional category supplied with the report.
    surface_type = Column(
        String(50),
        nullable=True,
    )

    # Optional category supplied with the report.
    location_type = Column(
        String(50),
        nullable=True,
    )

    status = Column(
        String(20),
        nullable=False,
        default="new",
    )

    submitted_at = Column(
        TIMESTAMP,
        server_default=func.now(),
    )

    notes = Column(
        Text,
        nullable=True,
    )


class Classification(Base):
    __tablename__ = "classifications"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    report_id = Column(
        Integer,
        ForeignKey(
            "reports.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    surface_type = Column(
        String(50),
        nullable=True,
    )

    tag_category = Column(
        String(50),
        nullable=True,
    )

    location_type = Column(
        String(50),
        nullable=True,
    )

    graffiti_detected = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    size_category = Column(
        String(20),
        nullable=True,
    )

    # Preserve the original AI predictions when council staff
    # correct the final accepted classification values.
    ai_surface_type = Column(
        String(50),
        nullable=True,
    )

    ai_tag_category = Column(
        String(50),
        nullable=True,
    )

    ai_location_type = Column(
        String(50),
        nullable=True,
    )

    ai_size_category = Column(
        String(20),
        nullable=True,
    )

    detection_confidence = Column(
        Float,
        nullable=True,
    )

    manual_review_required = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    manually_reviewed = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    reviewed_by = Column(
        String(255),
        nullable=True,
    )

    reviewed_at = Column(
        TIMESTAMP,
        nullable=True,
    )

    review_notes = Column(
        Text,
        nullable=True,
    )

    detections = Column(
        JSONB,
        nullable=False,
        default=list,
    )

    harm_score = Column(
        Integer,
        nullable=True,
    )

    severity_band = Column(
        String(20),
        nullable=True,
    )

    harm_breakdown = Column(
        JSONB,
        nullable=True,
    )

    # Text is used because the combined model-version description
    # can be longer than 50 characters.
    model_version = Column(
        Text,
        nullable=True,
    )

    classified_at = Column(
        TIMESTAMP,
        server_default=func.now(),
    )
