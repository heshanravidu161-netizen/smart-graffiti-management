# Backend Database Integration — Drop-in Update

This replaces the fake in-memory data in your original scaffold with real
Supabase Postgres connections. Files here mirror the structure of
`smart-graffiti-scaffold/backend/` — copy them into that folder, replacing
the originals.

## What's new
- `app/database.py` — SQLAlchemy engine/session setup, reads DATABASE_URL from environment
- `app/models/db_models.py` — ORM models matching your Supabase schema exactly
- `app/routers/reports.py` — rewritten to use real database queries instead of the fake list
- `app/main.py` — loads .env, adds a `/health/db` endpoint to test the connection
- `.env.example` — template for your connection string (copy to `.env`, fill in, never commit `.env`)
- `.gitignore` — makes sure `.env` never gets committed
- `requirements.txt` — added `python-dotenv`

## Setup steps (Mishal — do this)

1. Copy these files into your local `smart-graffiti-scaffold/backend/` folder, overwriting the old versions.
2. `cd backend`
3. `pip install -r requirements.txt --break-system-packages`
4. `cp .env.example .env`
5. Open `.env` and paste in the real, URL-encoded Supabase connection string (ask Ravindu for it).
6. Run: `uvicorn app.main:app --reload`
7. Open `http://localhost:8000/health/db` in your browser — you should see `{"status": "database connected"}`. If you see an error instead, check your `.env` connection string first.
8. Test it for real: POST to `http://localhost:8000/docs` (FastAPI's interactive docs) — try submitting a report via `/reports/`, then check it actually shows up in Supabase's Table Editor.

## Note on classifications.py

`classifications.py` and `classification_service.py` are unchanged from the
original scaffold — they still use placeholder/random logic since there's no
trained model yet. That's the next integration point once Robert has a
working model (see `ml_pipeline/`).
