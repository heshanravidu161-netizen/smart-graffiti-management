"""
Database connection setup for the UrbanEyes backend.

SQLAlchemy connects to the Supabase PostgreSQL database using the
DATABASE_URL value stored in backend/.env.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# Find the backend directory:
# smart-graffiti-scaffold/backend
BACKEND_DIR = Path(__file__).resolve().parent.parent

# Load variables from backend/.env.
load_dotenv(BACKEND_DIR / ".env")


# Read the Supabase PostgreSQL connection string.
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not configured. "
        "Add it to the backend/.env file."
    )


# Create the SQLAlchemy database engine.
#
# pool_pre_ping checks that a connection is still active before using it.
# This helps prevent errors caused by expired Supabase connections.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


# Create database sessions for API requests.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# Base class used by the SQLAlchemy database models.
Base = declarative_base()


def get_db():
    """
    Provide a database session to a FastAPI endpoint.

    The session is always closed after the request finishes.
    """

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
