"""
Report API endpoints.

These endpoints save and retrieve reports from the PostgreSQL
database connected through Supabase.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Report
from app.models.schemas import ReportCreate, ReportOut


router = APIRouter()


@router.post("/", response_model=ReportOut)
def submit_report(
    report: ReportCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new graffiti report.

    The user's image is uploaded to Supabase Storage by the
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

    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    return new_report


@router.get("/", response_model=list[ReportOut])
def list_reports(
    status: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Return all reports for the council dashboard.

    A status can optionally be provided:
    new, scheduled or resolved.
    """

    query = db.query(Report)

    if status:
        query = query.filter(
            Report.status == status,
        )

    return query.order_by(
        Report.submitted_at.desc(),
    ).all()


@router.get("/{report_id}", response_model=ReportOut)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
):
    """Return one report using its ID."""

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

    db.commit()
    db.refresh(report)

    return report
