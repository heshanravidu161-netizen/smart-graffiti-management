"""
SQLAlchemy ORM models — these mirror database/schema.sql exactly.

If you ever change the schema (add a column, rename something), update BOTH
schema.sql (source of truth for the actual database) AND this file (how
Python code talks to it) — they need to stay in sync manually.
"""

from sqlalchemy import Column, Integer, String, Float, Text, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(100))
    role = Column(String(20), nullable=False, default="citizen")
    created_at = Column(TIMESTAMP, server_default=func.now())


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    submitted_by = Column(Integer, ForeignKey("users.id"))
    image_url = Column(Text, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, default="new")
    submitted_at = Column(TIMESTAMP, server_default=func.now())
    notes = Column(Text)


class Classification(Base):
    __tablename__ = "classifications"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    surface_type = Column(String(50))
    tag_category = Column(String(50))
    detection_confidence = Column(Float)
    harm_score = Column(Integer)
    model_version = Column(String(50))
    classified_at = Column(TIMESTAMP, server_default=func.now())
