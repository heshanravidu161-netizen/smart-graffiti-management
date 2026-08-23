"""
Database connection setup — SQLAlchemy engine + session, pointed at Supabase.

The connection string comes from an environment variable, NOT hardcoded here.
This is important: if this file ever gets committed to a public GitHub repo,
you don't want the database password sitting in it in plain text.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Reads from environment variable DATABASE_URL.
# Set this in a .env file locally (see .env.example), and as a real
# environment variable wherever you deploy the backend (Railway/Render/Codespaces).
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Copy .env.example to .env and fill in your Supabase connection string."
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — gives each request its own DB session, closes it after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
