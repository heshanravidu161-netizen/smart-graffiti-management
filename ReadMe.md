# Smart Graffiti Management — Project Scaffold

This is a basic starting point for our CSG3101 Smart Graffiti project. It gives us the main folders and some example code so we don't have to start everything from zero.

It is **not a finished project yet**. The AI model is not trained, the app design is not finished, and the backend still needs the actual project logic.

## Project Structure

```text
smart-graffiti-scaffold/
├── mobile_app/       Flutter mobile app
├── backend/          FastAPI backend
├── database/         PostgreSQL database
└── ml_pipeline/      Machine learning files
```

## Recommended Order

1. **Database** — Set up the database structure first.
2. **Backend** — Set up the API and test it with some dummy data.
3. **Mobile App** — Build the screens for taking and submitting graffiti reports.
4. **ML Pipeline** — Train the AI model once we have enough labelled images.

## What Is Not Included Yet

* Trained AI model
* User login and security
* Deployment setup
* Real map/GPS integration
* Final app design

These parts can be added as the project develops.

## How to Run Each Part

**Backend:**

```bash
cd backend
pip install -r requirements.txt --break-system-packages
uvicorn app.main:app --reload
```

**Database:**

```bash
psql -f database/schema.sql
```

**Mobile App:**

```bash
flutter pub get
flutter run
```

**ML Pipeline:**

```bash
cd ml_pipeline
pip install -r requirements.txt --break-system-packages
```

This scaffold is just the base of the project. We can build and improve each part as the project progresses. 

Note: This is just the initial setup for our project. Some parts are still basic and will need to be changed or improved as we work on the project. The main purpose of this scaffold is to give us a starting point and keep the project organised.
