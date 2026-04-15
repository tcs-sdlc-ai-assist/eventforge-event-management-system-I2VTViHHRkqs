# EventForge Deployment Guide

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Vercel Configuration](#vercel-configuration)
- [Deployment Steps](#deployment-steps)
- [Database Considerations for Serverless](#database-considerations-for-serverless)
- [CI/CD Notes](#cicd-notes)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before deploying EventForge, ensure you have the following:

1. **Node.js 18+** installed locally (required by Vercel CLI)
2. **Python 3.11+** installed locally for testing before deployment
3. **Vercel account** — sign up at [vercel.com](https://vercel.com)
4. **Vercel CLI** installed globally:
   ```bash
   npm install -g vercel
   ```
5. **Git** repository initialized and code pushed to a remote (GitHub, GitLab, or Bitbucket)

### Verify Local Setup

```bash
python --version        # Should be 3.11+
vercel --version        # Should be 33+
pip install -r requirements.txt
uvicorn app.main:app --reload  # Confirm app starts locally
```

---

## Environment Variables

EventForge requires the following environment variables. Set these in the Vercel dashboard under **Project Settings → Environment Variables**, or via the Vercel CLI.

| Variable | Required | Description | Example |
|---|---|---|---|
| `SECRET_KEY` | **Yes** | Secret key for JWT signing and session security. Must be a strong random string (min 32 chars). | `openssl rand -hex 32` |
| `DATABASE_URL` | **Yes** | Database connection string. See [Database Considerations](#database-considerations-for-serverless). | `postgresql+asyncpg://user:pass@host:5432/eventforge` |
| `ENVIRONMENT` | No | Deployment environment identifier. Defaults to `production`. | `production` |
| `DEBUG` | No | Enable debug mode. **Must be `false` in production.** Defaults to `false`. | `false` |
| `ALLOWED_ORIGINS` | No | Comma-separated list of allowed CORS origins. | `https://eventforge.example.com,https://www.eventforge.example.com` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | JWT access token lifetime in minutes. Defaults to `30`. | `60` |
| `LOG_LEVEL` | No | Python logging level. Defaults to `INFO`. | `INFO` |

### Setting Environment Variables via Vercel CLI

```bash
# Add a secret (prompted for value)
vercel env add SECRET_KEY production

# Add a plain environment variable
vercel env add DATABASE_URL production

# List all environment variables
vercel env ls
```

### Generating a Secure SECRET_KEY

```bash
# Option 1: OpenSSL
openssl rand -hex 32

# Option 2: Python
python -c "import secrets; print(secrets.token_hex(32))"
```

> **Security Note:** Never commit secrets to version control. Always use environment variables or a secrets manager.

---

## Vercel Configuration

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
      "src": "/static/(.*)",
      "dest": "/app/static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "app/main.py"
    }
  ],
  "env": {
    "ENVIRONMENT": "production",
    "DEBUG": "false"
  }
}
```

### Key Configuration Details

- **`@vercel/python` runtime:** Vercel's Python runtime supports ASGI applications. It automatically detects the `app` object exported from the entry point.
- **Routes:** The first route serves static files directly. The catch-all route forwards all other requests to the FastAPI application.
- **Build output:** Vercel installs dependencies from `requirements.txt` automatically during the build step.

### Required Project Structure

Ensure your project root contains:

```
├── app/
│   ├── main.py          # FastAPI app entry point (must export `app`)
│   ├── core/
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   ├── templates/
│   └── static/
├── requirements.txt     # Python dependencies
├── vercel.json          # Vercel configuration
└── .env                 # Local only — never commit
```

### Entry Point Requirements

The `app/main.py` file must export a FastAPI application instance named `app` at the module level:

```python
from fastapi import FastAPI

app = FastAPI(title="EventForge")

# ... routes, middleware, lifespan, etc.
```

Vercel's Python runtime looks for an ASGI-compatible `app` object in the specified source file.

---

## Deployment Steps

### Option 1: Deploy via Vercel CLI

```bash
# 1. Login to Vercel (first time only)
vercel login

# 2. Link your project (first time only)
vercel link

# 3. Deploy to preview environment
vercel

# 4. Deploy to production
vercel --prod
```

### Option 2: Deploy via Git Integration

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your Git repository
3. Vercel auto-detects the Python framework
4. Configure environment variables in the dashboard
5. Click **Deploy**

Subsequent pushes to the `main` branch trigger automatic production deployments. Pull requests create preview deployments.

### Option 3: Deploy via GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Vercel

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: python -m pytest tests/ -v
        env:
          SECRET_KEY: test-secret-key-for-ci-only
          DATABASE_URL: sqlite+aiosqlite:///./test.db
          ENVIRONMENT: testing

      - name: Install Vercel CLI
        run: npm install -g vercel

      - name: Deploy to Production
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        run: vercel --prod --token=${{ secrets.VERCEL_TOKEN }}
        env:
          VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
          VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}

      - name: Deploy Preview
        if: github.event_name == 'pull_request'
        run: vercel --token=${{ secrets.VERCEL_TOKEN }}
        env:
          VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
          VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}
```

Required GitHub Secrets:
- `VERCEL_TOKEN` — Generate at [vercel.com/account/tokens](https://vercel.com/account/tokens)
- `VERCEL_ORG_ID` — Found in `.vercel/project.json` after running `vercel link`
- `VERCEL_PROJECT_ID` — Found in `.vercel/project.json` after running `vercel link`

---

## Database Considerations for Serverless

### SQLite Limitations on Vercel

**SQLite is NOT suitable for production on Vercel.** Vercel serverless functions run in ephemeral, read-only file systems. This means:

- The SQLite database file is **recreated on every cold start** — all data is lost
- Concurrent function invocations **cannot share** a SQLite file
- The `/tmp` directory is writable but **not persistent** across invocations
- File-based databases provide **no durability guarantees** in serverless environments

**SQLite is acceptable only for:**
- Local development
- CI/CD test pipelines
- Single-instance non-serverless deployments

### Recommended Production Databases

| Provider | Connection String Format | Free Tier |
|---|---|---|
| **Neon** (PostgreSQL) | `postgresql+asyncpg://user:pass@ep-xxx.us-east-2.aws.neon.tech/dbname?sslmode=require` | Yes |
| **Supabase** (PostgreSQL) | `postgresql+asyncpg://postgres:pass@db.xxx.supabase.co:5432/postgres` | Yes |
| **PlanetScale** (MySQL) | `mysql+aiomysql://user:pass@aws.connect.psdb.cloud/dbname?ssl=true` | Yes |
| **Railway** (PostgreSQL) | `postgresql+asyncpg://postgres:pass@xxx.railway.app:5432/railway` | Trial |
| **AWS RDS** (PostgreSQL) | `postgresql+asyncpg://user:pass@xxx.rds.amazonaws.com:5432/dbname` | Free tier |

### Migration to PostgreSQL

1. **Update `requirements.txt`:**
   ```
   asyncpg>=0.29.0
   ```

2. **Set the `DATABASE_URL` environment variable** to your PostgreSQL connection string.

3. **Run database migrations** (if using Alembic):
   ```bash
   alembic upgrade head
   ```

4. **Connection pooling:** For serverless, configure connection pool limits to avoid exhausting database connections:
   ```python
   # In app/core/database.py
   engine = create_async_engine(
       DATABASE_URL,
       pool_size=5,          # Max persistent connections
       max_overflow=10,      # Max temporary connections
       pool_timeout=30,      # Seconds to wait for a connection
       pool_recycle=300,     # Recycle connections after 5 minutes
       pool_pre_ping=True,   # Verify connections before use
   )
   ```

5. **Use a connection pooler** like [PgBouncer](https://www.pgbouncer.org/) or Neon's built-in pooler to handle serverless connection patterns efficiently.

### Database Initialization

For first-time deployment, ensure tables are created. The application's lifespan handler should handle this:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
```

For production, prefer explicit migrations with Alembic over `create_all`.

---

## CI/CD Notes

### Pre-Deployment Checklist

- [ ] All tests pass locally: `python -m pytest tests/ -v`
- [ ] No hardcoded secrets in source code
- [ ] `requirements.txt` is up to date: `pip freeze > requirements.txt`
- [ ] `vercel.json` is present and valid
- [ ] Environment variables are configured in Vercel dashboard
- [ ] `DATABASE_URL` points to a persistent database (not SQLite)
- [ ] `DEBUG` is set to `false` for production
- [ ] `SECRET_KEY` is a unique, strong random value (not reused from development)
- [ ] CORS `ALLOWED_ORIGINS` is set to your actual domain(s)

### Branch Strategy

| Branch | Vercel Environment | Auto-Deploy |
|---|---|---|
| `main` | Production | Yes |
| `develop` | Preview | Yes |
| Pull Requests | Preview (unique URL) | Yes |

### Running Tests in CI

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests with coverage
python -m pytest tests/ -v --tb=short

# Run with coverage report
python -m pytest tests/ --cov=app --cov-report=term-missing
```

### Build Caching

Vercel caches Python dependencies between deployments. To force a clean install:

```bash
vercel --force
```

Or add a build command in `vercel.json`:

```json
{
  "builds": [
    {
      "src": "app/main.py",
      "use": "@vercel/python",
      "config": {
        "maxLambdaSize": "50mb"
      }
    }
  ]
}
```

---

## Troubleshooting

### Common Issues

#### 1. `ModuleNotFoundError: No module named 'app'`

**Cause:** Vercel cannot resolve the Python module path.

**Fix:** Ensure `app/__init__.py` exists and `vercel.json` points to the correct entry file:
```json
{
  "builds": [
    {
      "src": "app/main.py",
      "use": "@vercel/python"
    }
  ]
}
```

#### 2. `ImportError: email-validator is not installed`

**Cause:** A Pydantic schema uses `EmailStr` but `email-validator` is missing from `requirements.txt`.

**Fix:** Add to `requirements.txt`:
```
email-validator>=2.1.0
```

#### 3. `500 Internal Server Error` on all routes

**Cause:** Usually a startup crash. Check Vercel function logs.

**Fix:**
```bash
# View deployment logs
vercel logs <deployment-url>

# Or check in Vercel dashboard:
# Project → Deployments → (select deployment) → Functions → (select function) → Logs
```

#### 4. Database connection failures

**Cause:** SQLite path issues in serverless, or PostgreSQL connection string misconfigured.

**Fix:**
- Verify `DATABASE_URL` is set in Vercel environment variables
- For PostgreSQL, ensure `?sslmode=require` is appended to the connection string
- Check that `asyncpg` (PostgreSQL) or `aiomysql` (MySQL) is in `requirements.txt`
- Verify the database server allows connections from Vercel's IP ranges

#### 5. `RuntimeError: no running event loop` or `MissingGreenlet`

**Cause:** Synchronous database operations called in an async context.

**Fix:** Ensure all database operations use `async/await` with `AsyncSession`. Ensure all SQLAlchemy relationships use `lazy="selectin"`.

#### 6. Static files returning 404

**Cause:** Static file route not configured in `vercel.json`.

**Fix:** Add the static route before the catch-all:
```json
{
  "routes": [
    {
      "src": "/static/(.*)",
      "dest": "/app/static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "app/main.py"
    }
  ]
}
```

#### 7. `CORS error` in browser console

**Cause:** `ALLOWED_ORIGINS` not configured or doesn't include the frontend domain.

**Fix:** Set the `ALLOWED_ORIGINS` environment variable to include your domain:
```
ALLOWED_ORIGINS=https://eventforge.example.com,https://www.eventforge.example.com
```

#### 8. Cold start timeouts

**Cause:** Vercel serverless functions have a default timeout of 10 seconds (Hobby) or 60 seconds (Pro).

**Fix:**
- Minimize startup imports — use lazy loading where possible
- Reduce `requirements.txt` to only necessary packages
- Use Vercel Pro for longer timeouts if needed
- Consider edge functions for latency-sensitive routes

#### 9. `Function size exceeds maximum` (50MB limit)

**Cause:** Too many or too large dependencies.

**Fix:**
- Audit `requirements.txt` and remove unused packages
- Use lighter alternatives (e.g., `orjson` instead of heavy JSON libraries)
- Exclude development dependencies from production builds

#### 10. Template files not found (`TemplateNotFound`)

**Cause:** Template directory path is relative and breaks in Vercel's execution environment.

**Fix:** Use absolute paths for template directories:
```python
from pathlib import Path
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)
```

### Viewing Logs

```bash
# Real-time logs for the latest deployment
vercel logs <project-name>.vercel.app

# Logs for a specific deployment
vercel logs <deployment-url>

# In the Vercel dashboard
# Project → Deployments → Select deployment → Function Logs
```

### Rolling Back a Deployment

```bash
# List recent deployments
vercel ls

# Promote a previous deployment to production
vercel promote <deployment-url>
```

Or in the Vercel dashboard: **Deployments → (select previous deployment) → ⋮ → Promote to Production**.

### Getting Help

- **Vercel Documentation:** [vercel.com/docs](https://vercel.com/docs)
- **FastAPI Documentation:** [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **Vercel Python Runtime:** [vercel.com/docs/functions/runtimes/python](https://vercel.com/docs/functions/runtimes/python)
- **Project Issues:** File an issue in the project repository