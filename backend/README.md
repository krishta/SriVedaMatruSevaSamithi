# SVMSS Backend

FastAPI service for the SVMSS donation and receipt application. The local setup uses SQLite and stores uploaded files and generated receipts under `backend/data/`.

## Requirements

- Python 3.13.1 (the version specified in `.python-version`)
- `pip`

## Run locally

Run these commands from the `backend/` directory.

1. Create and activate a virtual environment.

   **macOS/Linux**

   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate
   ```

   **Windows PowerShell**

   ```powershell
   py -3.13 -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

2. Install the backend dependencies.

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Create a local environment file from the example.

   **macOS/Linux**

   ```bash
   cp .env.example .env
   ```

   **Windows PowerShell**

   ```powershell
   Copy-Item .env.example .env
   ```

   For local development, the example configures SQLite at `./data/svmss.db` and permits the frontend at `http://localhost:4200`. Before seeding, change `JWT_SECRET` and `SEED_ADMIN_PASSWORD` in `.env` to values of your own. The example admin credentials are `admin` / `admin`; do not use them outside a disposable local setup. The NGO address and bank details are prefilled; SMTP values can remain unset/placeholders if you do not need email delivery.

4. Create the local storage directories.

   **macOS/Linux**

   ```bash
   mkdir -p data/uploads data/receipts
   ```

   **Windows PowerShell**

   ```powershell
   New-Item -ItemType Directory -Force data/uploads, data/receipts
   ```

5. Create the initial database records and admin account.

   ```bash
   python -m scripts.seed
   ```

   The seed script is safe to run again: existing admin settings are preserved except for replacing old NGO/bank placeholders and syncing the bundled logo path. The password for an existing admin is not changed by re-running it; use `python reset_admin.py` after changing `SEED_ADMIN_PASSWORD` if you need to reset that account.

6. Start the API server.

   ```bash
   python -m uvicorn app.main:app --reload
   ```

   Keep this terminal open while using the app. The API listens on `http://localhost:8000`.

## Verify the backend

- Health check: <http://localhost:8000/api/health> (should return `{"status":"ok"}`)
- Interactive API documentation: <http://localhost:8000/docs>

The first server start creates any missing database tables. Alembic is configured in the project, but there are currently no migration revisions to run for local setup.

## Run backend tests

The test suite uses `pytest` and FastAPI's `TestClient`. These development dependencies are not listed in `requirements.txt`; install them in the active virtual environment if needed:

```bash
python -m pip install pytest httpx
python -m pytest
```

## Troubleshooting

- **The app cannot connect to SQLite:** run the API from `backend/` and ensure `data/` exists. The relative database URL is resolved from the current working directory.
- **Browser reports a CORS error:** check that `CORS_ALLOWED_ORIGINS` in `.env` includes the frontend origin, normally `http://localhost:4200`, then restart the API.
- **Admin login fails:** check `SEED_ADMIN_USERNAME` and `SEED_ADMIN_PASSWORD` in `.env`. If the account was already seeded, run `python reset_admin.py` after updating the password.
- **The NGO logo is missing from an existing local database:** after updating the code, run `python -m scripts.seed` from `backend/` to sync the bundled logo path into the existing NGO settings row.
