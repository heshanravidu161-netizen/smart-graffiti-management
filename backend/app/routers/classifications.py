"""
Classification endpoints.

These endpoints run AI classification, return the latest result and
allow council staff to review uncertain predictions. Manual corrections
recalculate the harm score while preserving the original AI values.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Classification, Report
from app.models.schemas import (
    ClassificationOut,
    ClassificationReviewUpdate,
)
from app.services import classification_service
from app.services.harm_classifier import compute_harm_score


router = APIRouter()


ALLOWED_SURFACE_TYPES = {
    "private_fence",
    "temporary_hoarding",
    "commercial_shopfront",
    "public_signage",
    "heritage_building",
    "public_monument",
    "community_facility",
    "fence",
    "shopfront",
    "wall_or_hoarding",
    "pavement_or_footpath",
    "other",
    "unknown",
}

ALLOWED_TAG_CATEGORIES = {
    "tag",
    "stencil",
    "mural",
    "offensive_content",
    "other",
    "unknown",
}

ALLOWED_LOCATION_TYPES = {
    "laneway",
    "rear_wall",
    "side_street",
    "main_street",
    "school_zone",
    "transport_hub",
    "unknown",
}

ALLOWED_SIZE_CATEGORIES = {
    "small",
    "medium",
    "large",
}

# Convert surface labels produced by the surface classifier into the
# equivalent categories used by the harm-scoring framework.
SURFACE_SCORING_MAP = {
    "fence": "private_fence",
    "shopfront": "commercial_shopfront",
    "wall_or_hoarding": "temporary_hoarding",
    "pavement_or_footpath": "unknown",
    "other": "unknown",
}


def get_latest_result(
    report_id: int,
    db: Session,
) -> Classification:
    """Return the latest classification or raise a clear API error."""

    classification = (
        db.query(Classification)
        .filter(Classification.report_id == report_id)
        .order_by(Classification.classified_at.desc())
        .first()
    )

    if not classification:
        raise HTTPException(
            status_code=404,
            detail="This report has not been classified yet",
        )

    return classification


def validate_category(
    field_name: str,
    value: str | None,
    allowed_values: set[str],
) -> None:
    """Reject category values that the scoring framework cannot use."""

    if value is None:
        return

    if value not in allowed_values:
        options = ", ".join(sorted(allowed_values))

        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid {field_name}. "
                f"Allowed values: {options}"
            ),
        )


def get_occurrence_count(
    classification: Classification,
) -> int:
    """Read the saved recurrence count used by the harm framework."""

    breakdown = classification.harm_breakdown or {}
    recurrence = breakdown.get("recurrence", {})

    try:
        occurrence_count = int(
            recurrence.get("occurrence_count", 1)
        )
    except (TypeError, ValueError):
        occurrence_count = 1

    return max(1, min(3, occurrence_count))


def preserve_recurrence_details(
    old_breakdown: dict | None,
    new_breakdown: dict,
) -> dict:
    """Keep distance, image-match and time-window evidence."""

    old_recurrence = (
        (old_breakdown or {}).get("recurrence", {})
    )

    new_recurrence = new_breakdown.setdefault(
        "recurrence",
        {},
    )

    scoring_keys = {
        "raw",
        "weight",
        "weighted",
        "category",
    }

    for key, value in old_recurrence.items():
        if key not in scoring_keys:
            new_recurrence[key] = value

    return new_breakdown


@router.post(
    "/{report_id}/classify",
    response_model=ClassificationOut,
)
def classify_report(
    report_id: int,
    db: Session = Depends(get_db),
):
    """Run the AI classification and save its complete result."""

    report = (
        db.query(Report)
        .filter(Report.id == report_id)
        .first()
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    if not report.image_url:
        raise HTTPException(
            status_code=400,
            detail="This report does not contain an image URL",
        )

    try:
        result = classification_service.classify_image(
            image_url=report.image_url,
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Image classification failed: {error}",
        ) from error

    classification = Classification(
        report_id=report.id,
        graffiti_detected=result["graffiti_detected"],
        surface_type=result["surface_type"],
        tag_category=result["tag_category"],
        location_type=result["location_type"],
        size_category=result["size_category"],
        ai_surface_type=result["surface_type"],
        ai_tag_category=result["tag_category"],
        ai_location_type=result["location_type"],
        ai_size_category=result["size_category"],
        detection_confidence=result["detection_confidence"],
        manual_review_required=result["manual_review_required"],
        manually_reviewed=False,
        detections=result["detections"],
        harm_score=result["harm_score"],
        severity_band=result["severity_band"],
        harm_breakdown=result["harm_breakdown"],
        model_version=result["model_version"],
    )

    db.add(classification)
    db.commit()
    db.refresh(classification)

    return classification


@router.get(
    "/{report_id}/latest",
    response_model=ClassificationOut,
)
def get_latest_classification(
    report_id: int,
    db: Session = Depends(get_db),
):
    """Return the most recent classification for a report."""

    report = (
        db.query(Report)
        .filter(Report.id == report_id)
        .first()
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    return get_latest_result(report_id, db)


@router.patch(
    "/{report_id}/review",
    response_model=ClassificationOut,
)
def review_classification(
    report_id: int,
    review: ClassificationReviewUpdate,
    db: Session = Depends(get_db),
):
    """
    Save council corrections and recalculate the harm score.

    The original AI values remain stored in the ai_* columns.
    """

    report = (
        db.query(Report)
        .filter(Report.id == report_id)
        .first()
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    classification = get_latest_result(report_id, db)

    if not classification.graffiti_detected:
        raise HTTPException(
            status_code=400,
            detail=(
                "A no-graffiti result cannot receive a "
                "graffiti harm review"
            ),
        )

    supplied_values = review.model_dump(
        exclude_unset=True,
    )

    if not supplied_values:
        raise HTTPException(
            status_code=400,
            detail="No review values were supplied",
        )

    validate_category(
        "surface_type",
        review.surface_type,
        ALLOWED_SURFACE_TYPES,
    )
    validate_category(
        "tag_category",
        review.tag_category,
        ALLOWED_TAG_CATEGORIES,
    )
    validate_category(
        "location_type",
        review.location_type,
        ALLOWED_LOCATION_TYPES,
    )
    validate_category(
        "size_category",
        review.size_category,
        ALLOWED_SIZE_CATEGORIES,
    )

    # Preserve the original prediction before changing final values.
    if classification.ai_surface_type is None:
        classification.ai_surface_type = (
            classification.surface_type
        )

    if classification.ai_tag_category is None:
        classification.ai_tag_category = (
            classification.tag_category
        )

    if classification.ai_location_type is None:
        classification.ai_location_type = (
            classification.location_type
        )

    if classification.ai_size_category is None:
        classification.ai_size_category = (
            classification.size_category
        )

    if review.surface_type is not None:
        classification.surface_type = review.surface_type

    if review.tag_category is not None:
        classification.tag_category = review.tag_category

    if review.location_type is not None:
        classification.location_type = review.location_type

    if review.size_category is not None:
        classification.size_category = review.size_category

    surface_for_scoring = SURFACE_SCORING_MAP.get(
        classification.surface_type,
        classification.surface_type,
    )

    occurrence_count = get_occurrence_count(
        classification
    )

    harm_result = compute_harm_score(
        content_category=classification.tag_category,
        surface_category=surface_for_scoring,
        location_category=classification.location_type,
        size_category=classification.size_category,
        occurrence_count=occurrence_count,
    )

    classification.harm_score = harm_result["harm_score"]
    classification.severity_band = harm_result[
        "severity_band"
    ]
    classification.harm_breakdown = (
        preserve_recurrence_details(
            classification.harm_breakdown,
            harm_result["breakdown"],
        )
    )

    classification.manually_reviewed = True
    classification.manual_review_required = False
    classification.reviewed_by = (
        review.reviewed_by or "Council staff"
    )
    classification.reviewed_at = datetime.utcnow()
    classification.review_notes = review.review_notes

    db.commit()
    db.refresh(classification)

    return classification
