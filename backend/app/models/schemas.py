"""
Pydantic request/response models. These mirror database/schema.sql — keep them
in sync as the schema evolves.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ReportCreate(BaseModel):
    image_url: str
    latitude: float
    longitude: float
    notes: Optional[str] = None


class ReportOut(BaseModel):
    id: int
    image_url: str
    latitude: float
    longitude: float
    status: str
    submitted_at: datetime
    notes: Optional[str] = None


class ClassificationOut(BaseModel):
    id: int
    report_id: int
    surface_type: Optional[str]
    tag_category: Optional[str]
    detection_confidence: Optional[float]
    harm_score: Optional[int]
    model_version: Optional[str]
