"""
Smart Graffiti Management — Backend API entrypoint.

Now connected to a real Supabase Postgres database. Loads DATABASE_URL from
a local .env file (for local development) — in production/deployment, set
DATABASE_URL as a real environment variable instead of relying on .env.
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import reports, classifications
from app.database import Base, engine
from app.models import db_models  # noqa: F401
from app.routers import auth


app = FastAPI(
    title="Smart Graffiti Management API",
    description="API for citizen graffiti reporting, AI classification, and council prioritisation.",
    version="0.2.0",
)

# Allows the Flutter web app (running on a different localhost port) to
# actually reach this backend. In production, restrict allow_origins to
# your real deployed frontend URL instead of "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])

app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(classifications.router, prefix="/classifications", tags=["classifications"])


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
def health_check_db():
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "database connected"}
    except Exception as e:
        return {"status": "database connection failed", "error": str(e)}
