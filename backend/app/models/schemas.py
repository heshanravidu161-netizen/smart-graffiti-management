"""
Pydantic request/response models. These mirror database/schema.sql — keep them
in sync as the schema evolves.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ReportCreate(BaseModel):
    image_url: str
    latitude: float
    longitude: float
    notes: Optional[str] = None

    submitted_by_uuid: Optional[str] = None
    reporter_name: Optional[str] = None
    reporter_email: Optional[str] = None
    reporter_phone: Optional[str] = None


class ReportOut(BaseModel):
    id: int
    image_url: str
    latitude: float
    longitude: float
    status: str
    submitted_at: datetime
    notes: Optional[str] = None

    submitted_by_uuid: Optional[str] = None
    reporter_name: Optional[str] = None
    reporter_email: Optional[str] = None
    reporter_phone: Optional[str] = None


class ClassificationReviewUpdate(BaseModel):
    """Corrections submitted by authorised council staff."""

    surface_type: Optional[str] = None
    tag_category: Optional[str] = None
    location_type: Optional[str] = None
    size_category: Optional[str] = None
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None


class ClassificationOut(BaseModel):
    id: int
    report_id: int

    graffiti_detected: bool = False
    surface_type: Optional[str] = None
    tag_category: Optional[str] = None
    location_type: Optional[str] = None
    size_category: Optional[str] = None

    ai_surface_type: Optional[str] = None
    ai_tag_category: Optional[str] = None
    ai_location_type: Optional[str] = None
    ai_size_category: Optional[str] = None

    detection_confidence: Optional[float] = None
    manual_review_required: bool = True
    manually_reviewed: bool = False
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None

    detections: list[dict] = Field(default_factory=list)

    harm_score: Optional[int] = None
    severity_band: Optional[str] = None
    harm_breakdown: Optional[dict] = None

    model_version: Optional[str] = None
    classified_at: Optional[datetime] = None

class UserSignup(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
