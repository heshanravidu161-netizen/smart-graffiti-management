"""
/classifications endpoints — runs (or returns) the AI classification result for
a report.

Currently calls a stubbed classification_service that returns a hardcoded
placeholder result. Swap in the real model call once ml_pipeline/ has a
trained model.
"""

from fastapi import APIRouter
from app.models.schemas import ClassificationOut
from app.services import classification_service

router = APIRouter()


@router.post("/{report_id}/classify", response_model=ClassificationOut)
def classify_report(report_id: int, image_url: str):
    """Trigger classification for a given report's image."""
    result = classification_service.classify_image(image_url)
    result["report_id"] = report_id
    return result
