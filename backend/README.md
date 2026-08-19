# MediFusion Backend (local demo)

## Render deployment

The backend requires a reachable PostgreSQL `DATABASE_URL`. In Render, attach the
`medical_system_db` database to the `project1-backend` service or copy the complete
connection string from the database's Connect page into the service environment.
Do not use a stale `dpg-...` hostname from a deleted or different database.

After changing `DATABASE_URL`, deploy the latest commit and check `/health` before
testing login. The application initializes missing tables and columns at startup,
but it cannot resolve an invalid database hostname.

## Quick start with Docker
1. Ensure Docker is installed.
2. From `backend/` directory run:
