# Taraba State Election Portal

One Django project, hosted on Vercel with a Neon Postgres database:

- **`/`** - the portal itself (app `web/`): live results with the state map and charts,
  projector mode (`/present/`), clerk sign in, and the dashboard for entering results,
  progress, reports and downloads, change history and clerk assignments.
- **`/api/`** - the REST API (app `election/`), still used by the apc portal.
- **`/admin/`** - Django admin.

The pages are server-rendered Django templates styled with Tailwind CSS
(`web/static_src/styles.css` -> `web/static/web/css/styles.css`).

## Run it locally

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_portal        # parties + 16 LGAs, 168 wards, 3,597 polling units
python manage.py createsuperuser     # becomes an admin
DJANGO_DEBUG=1 python manage.py runserver
```

Without `DATABASE_URL` the project uses a local `db.sqlite3`.

After changing templates, rebuild the CSS and commit the result:

```bash
npm install
npm run build-css
```

## Deploy on Vercel

1. Import the repository into Vercel (framework preset: Other). `vercel.json` runs
   `collectstatic`, `migrate` and `setup_portal` on every build.
2. Add a Neon database from Vercel Storage and connect it to the project (sets `DATABASE_URL`).
3. Set environment variables:
   - `DJANGO_SECRET_KEY` - a long random string (required).
   - `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED_ORIGINS` - only for extra custom domains
     (`*.vercel.app` and `tarabaelection.pheedev.online` are already allowed).
4. Redeploy, then create the first admin from your machine against the Neon database:
   `DATABASE_URL=... python manage.py createsuperuser`.

The build fails on purpose if `DJANGO_SECRET_KEY` or the database is missing, rather than
serving a site that would lose its data.

Party logos live in `media/party_logos/` and ship with the code. Vercel's file system is
read-only, so add new logos by committing them, not by uploading in the admin.

## User roles

- **Admin** (`role=admin`): every LGA, change history, clerk management.
- **Data clerk** (`role=clerk`): only the LGAs assigned to them.

## API Endpoints

### Authentication
- `POST /api/auth/login/` - Login (username, password)
- `POST /api/auth/logout/` - Logout
- `GET /api/auth/me/` - Get current user

### Local Government Areas
- `GET /api/lgas/` - List all LGAs
- `GET /api/lgas/{id}/` - Get LGA details
- `GET /api/lgas/{id}/wards/` - Get wards for an LGA

### Wards
- `GET /api/wards/` - List all wards (optional `?lga={id}` filter)
- `GET /api/wards/{id}/` - Get ward details
- `GET /api/wards/{id}/polling_units/` - Get polling units for a ward

### Polling Units
- `GET /api/polling-units/` - List all polling units (optional `?ward={id}` or `?lga={id}` filters)
- `GET /api/polling-units/{id}/` - Get polling unit details
- `GET /api/polling-units/{id}/results/` - Get results for a polling unit

### Political Parties
- `GET /api/parties/` - List all parties
- `GET /api/parties/{id}/` - Get party details

### Election Results
- `GET /api/results/` - List all results (optional filters: `?polling_unit={id}`, `?lga={id}`, `?party={id}`)
- `POST /api/results/bulk_create/` - Bulk create/update results for a polling unit
  ```json
  {
    "polling_unit_id": 1,
    "results": [
      {"party_id": 1, "votes": 5200},
      {"party_id": 2, "votes": 4300}
    ]
  }
  ```
- `GET /api/results/chart_data/` - Get data formatted for charts (bar, radial, line)
- `GET /api/results/summary/` - Get summary grouped by LGA and party

## Admin Panel

Access the Django admin at `http://localhost:8000/admin/` with your superuser credentials.

