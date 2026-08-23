"""
Smart Graffiti Management — Backend API entrypoint.

Now connected to a real Supabase Postgres database. Loads DATABASE_URL from
a local .env file (for local development) — in production/deployment, set
DATABASE_URL as a real environment variable instead of relying on .env.
"""

from dotenv import load_dotenv
load_dotenv()  # reads .env file into environment variables — must run before database.py is imported

from fastapi import FastAPI
from app.routers import reports, classifications
from app.database import Base, engine
from app.models import db_models  # noqa: F401 — import so SQLAlchemy registers the models

app = FastAPI(
    title="Smart Graffiti Management API",
    description="API for citizen graffiti reporting, AI classification, and council prioritisation.",
    version="0.2.0",
)

app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(classifications.router, prefix="/classifications", tags=["classifications"])


@app.get("/health")
def health_check():
    """Simple liveness check — useful once you deploy this somewhere."""
    return {"status": "ok"}


@app.get("/health/db")
def health_check_db():
    """Confirms the backend can actually reach the database — hit this first
    if something seems broken, to rule the database connection in or out."""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "database connected"}
    except Exception as e:
        return {"status": "database connection failed", "error": str(e)}
