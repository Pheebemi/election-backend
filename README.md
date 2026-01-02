# Taraba Election Portal - Django Backend

Django REST API backend for the Taraba Election Portal.

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Create Superuser (Admin)

```bash
python manage.py createsuperuser
```

When prompted, set:
- Username: admin (or your choice)
- Email: (optional)
- Password: (choose a secure password)
- Set `role` to 'admin' when asked (or create via admin panel)

### 4. Create Sample Data (Optional)

You can create sample data via Django admin or use management commands:

```bash
python manage.py shell
```

Then in the shell:

```python
from election.models import *

# Create LGAs
jalingo = LocalGovernmentArea.objects.create(name="Jalingo", code="JAL")
wukari = LocalGovernmentArea.objects.create(name="Wukari", code="WUK")

# Create Wards
ward1 = Ward.objects.create(name="Ward 1", lga=jalingo, code="JAL-W1")
ward2 = Ward.objects.create(name="Ward 2", lga=wukari, code="WUK-W1")

# Create Polling Units
pu1 = PollingUnit.objects.create(name="PU 001", ward=ward1, code="JAL-W1-PU001", registered_voters=500)
pu2 = PollingUnit.objects.create(name="PU 002", ward=ward2, code="WUK-W1-PU002", registered_voters=600)

# Create Parties
pdp = PoliticalParty.objects.create(name="People's Democratic Party", abbreviation="PDP", color="#0EA44A")
apc = PoliticalParty.objects.create(name="All Progressives Congress", abbreviation="APC", color="#64CCFF")
lp = PoliticalParty.objects.create(name="Labour Party", abbreviation="LP", color="#00A651")
nnpp = PoliticalParty.objects.create(name="New Nigeria People's Party", abbreviation="NNPP", color="#FF6B00")
apga = PoliticalParty.objects.create(name="All Progressives Grand Alliance", abbreviation="APGA", color="#FFD700")

# Create a clerk user
from django.contrib.auth import get_user_model
User = get_user_model()
clerk = User.objects.create_user(username="clerk1", password="password123", role="clerk")
```

### 5. Run Development Server

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`

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

## User Roles

- **Admin**: Full access via Django admin panel (`/admin/`)
- **Clerk**: Can login via API and submit election results

## Frontend Connection

The frontend (Next.js) connects to this API. Make sure to set:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

## Admin Panel

Access the Django admin at `http://localhost:8000/admin/` with your superuser credentials.

