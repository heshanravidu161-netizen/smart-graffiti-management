"""
Report API endpoints.

These endpoints save and retrieve reports from the PostgreSQL
database connected through Supabase.

After a new report is saved, automatic AI classification starts as a
background task. This allows the mobile application to receive the
submission response without waiting for the AI models to finish.
"""

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Report
from app.models.schemas import ReportCreate, ReportOut
from app.services.classification_workflow import (
    classify_report_in_background,
)


router = APIRouter()


@router.post("/", response_model=ReportOut)
def submit_report(
    report: ReportCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Create a new graffiti report.

    The mobile application uploads the image to Supabase Storage
    before sending its public image URL to this endpoint.

    After the report is saved, the automatic AI classification
    workflow starts in the background. The AI determines graffiti
    presence, bounding boxes, confidence, approximate size, style,
    offensive content and surface type.
    """

    new_report = Report(
        submitted_by=None,
        submitted_by_uuid=report.submitted_by_uuid,
        reporter_name=report.reporter_name,
        reporter_email=report.reporter_email,
        reporter_phone=report.reporter_phone,
        image_url=report.image_url,
        latitude=report.latitude,
        longitude=report.longitude,
        notes=report.notes,
        status="new",
    )

    try:
        db.add(new_report)
        db.commit()
        db.refresh(new_report)

    except Exception:
        db.rollback()
        raise

    # Start AI classification after the report has been saved.
    # The mobile application does not need to wait for the models.
    background_tasks.add_task(
        classify_report_in_background,
        new_report.id,
    )

    return new_report


@router.get("/", response_model=list[ReportOut])
def list_reports(
    status: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Return reports for the council dashboard.

    Reports can optionally be filtered by workflow status:
    new, scheduled or resolved.
    """

    query = db.query(Report)

    if status:
        allowed_statuses = [
            "new",
            "scheduled",
            "resolved",
        ]

        if status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Status must be new, "
                    "scheduled or resolved"
                ),
            )

        query = query.filter(
            Report.status == status,
        )

    return (
        query
        .order_by(Report.submitted_at.desc())
        .all()
    )


@router.get("/{report_id}", response_model=ReportOut)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
):
    """Return one report using its database ID."""

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

    return report


@router.patch(
    "/{report_id}/status",
    response_model=ReportOut,
)
def update_report_status(
    report_id: int,
    status: str,
    db: Session = Depends(get_db),
):
    """Update a report's council workflow status."""

    allowed_statuses = [
        "new",
        "scheduled",
        "resolved",
    ]

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=(
                "Status must be new, "
                "scheduled or resolved"
            ),
        )

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

    report.status = status

    try:
        db.commit()
        db.refresh(report)

    except Exception:
        db.rollback()
        raise

    return report
