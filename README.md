# Kaan Gallery

A personal art gallery in development, built step by step with Django REST Framework. The current backend supports artwork, artists, categories, tags, search, filtering, sorting, and pagination.

## Status and planned architecture

This is a learning project, not a production deployment. Current local settings permit anonymous writes; private admin access and production permissions must be implemented before hosting it publicly.

- Frontend: Next.js and TypeScript on Vercel (planned).
- Backend: Django and DRF on Render (planned, free tier initially).
- Production database: Neon PostgreSQL (planned, free tier initially).
- Images: separate persistent object storage (provider to be chosen).
- First release: public gallery and private administration; sales are out of scope.

Local development currently uses SQLite. Database files, credentials, and uploaded artwork are excluded from version control.

## Run

```bash
./.venv/bin/python manage.py migrate
./.venv/bin/python manage.py runserver
```

Open http://127.0.0.1:8000/items/ for the browsable API.

For a fresh installation:

```bash
python3.12 -m venv .venv
./.venv/bin/python -m pip install -r requirements-lock.txt
./.venv/bin/python manage.py migrate
./.venv/bin/python manage.py runserver
```

The repository does not include the local database; migrations create an empty one.

## Endpoints

| URL | Method | Behavior |
| --- | --- | --- |
| `/items/` | GET | List items with pagination (5 per page) |
| `/items/` | POST | Create an item |
| `/items/<id>/` | GET | Retrieve an item |
| `/items/<id>/` | PATCH | Update selected fields; returns 200 with no body |
| `/items/<id>/` | DELETE | Delete an item; returns 204 |

Items have a name, decimal price, quantity, and generated ID and creation timestamp.
The serializer requires price to be greater than zero.

```bash
curl -X POST http://127.0.0.1:8000/items/ \
  -H 'Content-Type: application/json' \
  -d '{"name":"Vase","price":"25.00","quantity":2}'
```

## Files

- `items/models.py`: Item database model.
- `items/serializers.py`: Item fields and price validation.
- `items/views.py`: Your list/create and detail/update/delete functions.
- `config/urls.py`: URL mappings.
- `items/tests.py`: Place API tests here.
- `items/migrations/`: Database schema history.
- `db.sqlite3`: Local database, excluded from version control.

The Python app is named `items`. Its internal Django app label remains `tasks` to preserve existing database tables and applied migrations.
Historical migrations mention the removed Task model; a subsequent migration deletes its table.

## Checks

```bash
./.venv/bin/python manage.py check
./.venv/bin/python manage.py test
./.venv/bin/python manage.py makemigrations --check --dry-run
```

After changing a model, run `makemigrations` followed by `migrate`.
This project uses local development settings and anonymous API access.
