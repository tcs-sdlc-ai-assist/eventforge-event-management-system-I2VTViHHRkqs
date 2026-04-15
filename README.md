# EventForge

A comprehensive event management platform built with Python 3.11+ and FastAPI, featuring event creation, registration, ticketing, and attendee management.

## Features

- **Event Management** — Create, update, and manage events with rich details
- **User Authentication** — JWT-based authentication with role-based access control
- **Registration & Ticketing** — Event registration with multiple ticket types and availability tracking
- **Attendee Management** — Track attendees, check-ins, and attendance status
- **Category & Tag System** — Organize events with categories and tags
- **Search & Filtering** — Full-text search and advanced filtering for events
- **Audit Logging** — Track all significant actions for accountability
- **RESTful API** — Clean, well-documented API endpoints with OpenAPI/Swagger docs
- **Async Architecture** — Fully asynchronous request handling with SQLAlchemy 2.0 and aiosqlite

## Tech Stack

| Layer | Technology |
|---|---|
| **Runtime** | Python 3.11+ |
| **Framework** | FastAPI 0.109+ |
| **Database** | SQLite (via aiosqlite) |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Auth** | JWT (python-jose) + bcrypt |
| **Validation** | Pydantic v2 |
| **Config** | pydantic-settings (.env) |
| **Server** | Uvicorn |
| **Templates** | Jinja2 + Tailwind CSS (CDN) |

## Project Structure

```
eventforge/
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # Application settings (BaseSettings)
│   │   ├── database.py        # Async SQLAlchemy engine & session
│   │   └── security.py        # JWT creation/verification, password hashing
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py            # User model
│   │   ├── event.py           # Event model + association tables
│   │   ├── category.py        # Category model
│   │   ├── tag.py             # Tag model
│   │   ├── ticket.py          # Ticket / TicketType models
│   │   ├── registration.py    # Registration model
│   │   └── audit_log.py       # AuditLog model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py            # User request/response schemas
│   │   ├── event.py           # Event request/response schemas
│   │   ├── category.py        # Category schemas
│   │   ├── tag.py             # Tag schemas
│   │   ├── ticket.py          # Ticket schemas
│   │   ├── registration.py    # Registration schemas
│   │   └── audit_log.py       # AuditLog schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_service.py    # User CRUD operations
│   │   ├── event_service.py   # Event CRUD + search
│   │   ├── registration_service.py  # Registration logic
│   │   └── audit_service.py   # Audit log operations
│   ├── dependencies/
│   │   ├── __init__.py
│   │   └── auth.py            # get_current_user, role checks
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py            # Login, register, token refresh
│   │   ├── users.py           # User profile endpoints
│   │   ├── events.py          # Event CRUD endpoints
│   │   ├── categories.py      # Category endpoints
│   │   ├── tags.py            # Tag endpoints
│   │   ├── tickets.py         # Ticket type endpoints
│   │   ├── registrations.py   # Registration endpoints
│   │   └── audit_logs.py      # Audit log endpoints
│   ├── templates/             # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── auth/
│   │   ├── events/
│   │   └── dashboard/
│   └── main.py                # FastAPI app entry point
├── .env                       # Environment variables (not committed)
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd eventforge
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Then edit `.env` with your values (see [Environment Variables](#environment-variables) below).

### 5. Run Database Migrations

The database tables are created automatically on first startup via SQLAlchemy's `create_all()`. No separate migration step is required for initial setup.

For production environments, consider using Alembic for migrations:

```bash
# Optional: Initialize Alembic (if added later)
alembic init alembic
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### 6. Start the Server

**Development:**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Production:**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The application will be available at:

- **App:** [http://localhost:8000](http://localhost:8000)
- **API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Docs (ReDoc):** [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Environment Variables

| Variable | Description | Default | Required |
|---|---|---|---|
| `SECRET_KEY` | JWT signing secret (min 32 chars) | `change-me-to-a-secure-random-string` | **Yes** |
| `DATABASE_URL` | SQLite connection string | `sqlite+aiosqlite:///./eventforge.db` | No |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiry in minutes | `30` | No |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiry in days | `7` | No |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000,http://localhost:8000` | No |
| `APP_NAME` | Application display name | `EventForge` | No |
| `APP_VERSION` | Application version string | `1.0.0` | No |
| `DEBUG` | Enable debug mode | `false` | No |

### Generating a Secure Secret Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

## API Endpoints Reference

### Authentication

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/auth/register` | Register a new user | No |
| `POST` | `/api/auth/login` | Login and receive JWT tokens | No |
| `POST` | `/api/auth/refresh` | Refresh access token | Yes |
| `GET` | `/api/auth/me` | Get current user profile | Yes |

### Users

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/users` | List all users (admin) | Admin |
| `GET` | `/api/users/{id}` | Get user by ID | Yes |
| `PUT` | `/api/users/{id}` | Update user profile | Owner/Admin |
| `DELETE` | `/api/users/{id}` | Delete user | Admin |

### Events

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/events` | List events (with search & filters) | No |
| `POST` | `/api/events` | Create a new event | Yes |
| `GET` | `/api/events/{id}` | Get event details | No |
| `PUT` | `/api/events/{id}` | Update event | Owner/Admin |
| `DELETE` | `/api/events/{id}` | Delete event | Owner/Admin |
| `GET` | `/api/events/{id}/attendees` | List event attendees | Owner/Admin |

### Categories

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/categories` | List all categories | No |
| `POST` | `/api/categories` | Create a category | Admin |
| `GET` | `/api/categories/{id}` | Get category by ID | No |
| `PUT` | `/api/categories/{id}` | Update category | Admin |
| `DELETE` | `/api/categories/{id}` | Delete category | Admin |

### Tags

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/tags` | List all tags | No |
| `POST` | `/api/tags` | Create a tag | Yes |
| `GET` | `/api/tags/{id}` | Get tag by ID | No |
| `DELETE` | `/api/tags/{id}` | Delete tag | Admin |

### Tickets

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/events/{event_id}/tickets` | List ticket types for event | No |
| `POST` | `/api/events/{event_id}/tickets` | Create ticket type | Owner/Admin |
| `PUT` | `/api/tickets/{id}` | Update ticket type | Owner/Admin |
| `DELETE` | `/api/tickets/{id}` | Delete ticket type | Owner/Admin |

### Registrations

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/events/{event_id}/register` | Register for an event | Yes |
| `GET` | `/api/registrations` | List user's registrations | Yes |
| `GET` | `/api/registrations/{id}` | Get registration details | Owner/Admin |
| `PUT` | `/api/registrations/{id}` | Update registration status | Owner/Admin |
| `DELETE` | `/api/registrations/{id}` | Cancel registration | Owner/Admin |
| `POST` | `/api/registrations/{id}/checkin` | Check in attendee | Owner/Admin |

### Audit Logs

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/audit-logs` | List audit logs | Admin |
| `GET` | `/api/audit-logs/{id}` | Get audit log entry | Admin |

### Template Pages (HTML)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Home page — event listing |
| `GET` | `/auth/login` | Login page |
| `GET` | `/auth/register` | Registration page |
| `GET` | `/events/{id}` | Event detail page |
| `GET` | `/dashboard` | User dashboard |

## Query Parameters

### Event Listing (`GET /api/events`)

| Parameter | Type | Description |
|---|---|---|
| `q` | string | Full-text search in title and description |
| `category_id` | string (UUID) | Filter by category |
| `tag_ids` | string (comma-separated UUIDs) | Filter by tags |
| `start_date` | string (ISO 8601) | Events starting after this date |
| `end_date` | string (ISO 8601) | Events ending before this date |
| `status` | string | Filter by status (`draft`, `published`, `cancelled`, `completed`) |
| `page` | integer | Page number (default: 1) |
| `per_page` | integer | Items per page (default: 20, max: 100) |
| `sort_by` | string | Sort field (`created_at`, `start_date`, `title`) |
| `sort_order` | string | Sort direction (`asc`, `desc`) |

## Authentication

EventForge uses JWT (JSON Web Tokens) for API authentication.

### Obtaining a Token

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "yourpassword"}'
```

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Using the Token

Include the token in the `Authorization` header:

```bash
curl -X GET http://localhost:8000/api/events \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

## Deployment Guide (Vercel)

### Prerequisites

- A [Vercel](https://vercel.com) account
- Vercel CLI installed: `npm i -g vercel`

### 1. Create `vercel.json`

Create a `vercel.json` file in the project root:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "app/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app/main.py"
    }
  ]
}
```

### 2. Configure Environment Variables

Set environment variables in the Vercel dashboard:

1. Go to your project → **Settings** → **Environment Variables**
2. Add all required variables from the [Environment Variables](#environment-variables) section
3. **Important:** Set `SECRET_KEY` to a strong random value for production
4. Set `DATABASE_URL` to your production database connection string

> **Note:** SQLite is not recommended for Vercel deployments due to the ephemeral filesystem. Consider using a hosted PostgreSQL database (e.g., Vercel Postgres, Supabase, Neon) and updating the `DATABASE_URL` and database driver accordingly.

### 3. Deploy

```bash
# Login to Vercel
vercel login

# Deploy to preview
vercel

# Deploy to production
vercel --prod
```

### 4. Production Database Considerations

For production deployments, switch from SQLite to PostgreSQL:

1. Update `requirements.txt`:
   ```
   asyncpg==0.29.0
   ```

2. Update `DATABASE_URL` environment variable:
   ```
   DATABASE_URL=postgresql+asyncpg://user:password@host:5432/eventforge
   ```

3. The application's async SQLAlchemy setup is compatible with both SQLite (aiosqlite) and PostgreSQL (asyncpg) — no code changes required beyond the connection string.

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

### Code Formatting

```bash
# Install formatters
pip install black isort

# Format code
black app/
isort app/
```

### Linting

```bash
# Install linter
pip install ruff

# Run linter
ruff check app/

# Auto-fix issues
ruff check app/ --fix
```

## License

Private — All rights reserved.