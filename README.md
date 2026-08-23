# Smart Graffiti Management — Project Scaffold

This is a **starting-point scaffold**, not a finished product. It gives you working
folder structure, wiring, and example code so your team can build the actual
CSG3101 project on top of it, rather than starting from a blank folder.

Nothing here is "done" — models aren't trained, screens aren't styled, and the API
has no real business logic yet. Treat every file as a template to extend.

## Structure

```
smart-graffiti-scaffold/
├── mobile_app/       Flutter app skeleton (capture + submit + view reports)
├── backend/          FastAPI backend skeleton (API, DB models, routers)
├── database/         PostgreSQL schema (reports, users, classifications)
└── ml_pipeline/       Model training pipeline skeleton (data prep, train, eval)
```

## Suggested order of attack

1. **database/schema.sql** — agree on this first as a team; everything else depends on it.
2. **backend** — stand up the API skeleton against the schema (`/reports` endpoints work
   with dummy data before any AI model exists).
3. **mobile_app** — build the capture/submit screens against the backend's dummy endpoints.
4. **ml_pipeline** — train a real detection model once you have a labelled dataset, then
   swap it in behind `backend/app/services/classification_service.py`.

## What's intentionally NOT included

- A trained model (you need to source/label graffiti image data yourselves — note the
  ethics-clearance requirement in your project brief if you collect data from people)
- Authentication / production security hardening
- Deployment config (Docker, CI/CD) — add once the team has picked a hosting target
- Real map/GIS integration (placeholder API call only)

## Getting each part running

- **Backend**: `cd backend && pip install -r requirements.txt --break-system-packages && uvicorn app.main:app --reload`
- **Database**: `psql -f database/schema.sql` against a local Postgres instance
- **Mobile app**: needs Flutter SDK installed locally — `flutter pub get && flutter run`
- **ML pipeline**: `cd ml_pipeline && pip install -r requirements.txt --break-system-packages`
