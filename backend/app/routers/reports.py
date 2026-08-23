"""
/reports endpoints — now backed by the real Supabase Postgres database
instead of the placeholder in-memory list.

Every endpoint takes `db: Session = Depends(get_db)` — FastAPI automatically
gives each request its own database session and closes it afterward.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import Report
from app.models.schemas import ReportCreate, ReportOut

router = APIRouter()


@router.post("/", response_model=ReportOut)
def submit_report(report: ReportCreate, db: Session = Depends(get_db)):
    """Citizen submits a new graffiti report. Triggering AI classification is
    a separate call — see classifications.router — or wire it in here later
    once the ML pipeline is ready, so classification happens automatically
    on submission."""
    new_report = Report(
        image_url=report.image_url,
        latitude=report.latitude,
        longitude=report.longitude,
        notes=report.notes,
        status="new",
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)  # loads the auto-generated id, submitted_at, etc.
    return new_report


@router.get("/", response_model=list[ReportOut])
def list_reports(status: str | None = None, db: Session = Depends(get_db)):
    """Council dashboard uses this to list/filter reports, e.g. ?status=new"""
    query = db.query(Report)
    if status:
        query = query.filter(Report.status == status)
    return query.order_by(Report.submitted_at.desc()).all()


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.patch("/{report_id}/status", response_model=ReportOut)
def update_report_status(report_id: int, status: str, db: Session = Depends(get_db)):
    """Council staff update a report's status, e.g. 'scheduled', 'resolved'."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report.status = status
    db.commit()
    db.refresh(report)
    return report
