# UrbanEyes Backend 

The backend is a FastAPI service that connects the UrbanEyes mobile application, council dashboard, Supabase database and AI classification pipeline.

It receives graffiti reports, stores report data, runs automatic classification and returns the results used by the council dashboard.

## Main features

- Create and retrieve graffiti reports
- Connect to the PostgreSQL database hosted through Supabase
- Run automatic graffiti detection and classification
- Calculate the harm score and priority level
- Use map data to classify the surrounding area
- Check nearby reports for visual recurrence
- Allow council staff to review and correct AI results
- Update report progress and status
- Provide interactive API documentation through FastAPI

## Project structure

```text
backend/
├── app/
│   ├── models/       # Database models and API schemas
│   ├── routers/      # Report and classification endpoints
│   ├── services/     # AI, scoring, location and similarity logic
│   ├── database.py   # Database connection and sessions
│   └── main.py       # FastAPI application entry point
├── .env.example      # Environment-variable template
├── requirements.txt  # Python dependencies
└── README.md
```

## Requirements

Before starting, make sure you have:

- Python 3 installed
- Git installed
- Access to the required Supabase project
- The trained model files included in the repository

## Local setup

From the project root, open the backend folder:

```bash
cd backend
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

On Windows PowerShell, use:

```powershell
.venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## Environment variables

Create a local `.env` file from the provided example:

```bash
cp .env.example .env
```

Open `.env` and add the real values for the environment variables listed in `.env.example`.

Do not commit `.env` to GitHub. It may contain database credentials, Supabase keys and other private configuration values.

## Run the backend

Start the development server with:

```bash
uvicorn app.main:app --reload
```

The backend should then be available at:

```text
http://127.0.0.1:8000
```

## Check that it is working

Open the database health endpoint:

```text
http://127.0.0.1:8000/health/db
```

A successful connection should return a response similar to:

```json
{
  "status": "database connected"
}
```

FastAPI's interactive documentation is available at:

```text
http://127.0.0.1:8000/docs
```

You can use this page to inspect the endpoints and test requests without installing a separate API client.

## Testing the report workflow

1. Start the backend and confirm that the database health check passes.
2. Open `/docs` in the browser.
3. Submit a test report through the reports endpoint or the UrbanEyes application.
4. Confirm that the report appears in the Supabase `reports` table.
5. Wait for automatic classification to complete.
6. Confirm that the classification result appears in the dashboard and the Supabase `classifications` table.

AI processing can take longer when the hosted backend is waking up or running with limited memory.

## Common problems

### Database connection fails

- Check that `.env` exists inside the `backend` folder.
- Confirm that the database connection string is correct.
- Make sure special characters in the connection string are URL encoded.
- Restart the backend after changing environment variables.

### A Python package is missing

Activate the virtual environment and run:

```bash
pip install -r requirements.txt
```

### AI classification does not start

- Confirm that the trained model files are present.
- Check the backend terminal for the full error message.
- Make sure the report has a valid image URL.
- Allow extra time if the backend has recently restarted.

## The dashboard cannot reach the local backend

Make sure the dashboard is configured to use:

```text
http://127.0.0.1:8000
```

Also confirm that the backend terminal is still running.

## Security notes

- Never commit `.env`, passwords, API keys or database credentials.
- Do not include reporter contact information in screenshots or public issues.
- Use test accounts and test reports when demonstrating the system publicly.
- Review all changes before pushing them to the main branch.

## Deployment

The production backend is deployed on Render. Render must be configured with the same required environment variables used locally.

The free hosting tier may take time to wake after inactivity and may process AI requests more slowly than a local machine.

___________________
Created By: Ravindu Heshan
(Mishal,Robert,Sai Read through the instructions to get it running)

Note: The .env files is shared seperately (in the group chat (This contains the database password which is in my supabase account)) 

The .env files is not shared to GitHub