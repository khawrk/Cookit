# Cookit

Scan your fridge with a photo — AI detects what's inside and recommends recipes you can make right now.

## Features

- **Fridge scanning** — take a photo, Claude Vision identifies every item
- **Manual add** — searchable condiments catalogue + free-text input
- **Recipe recommendations** — three-strategy engine (SQL overlap + vector similarity + Claude creative)
- **Recipe database** — nightly scraper pulls from AllRecipes & BBC Good Food
- **Auth** — JWT via httpOnly cookie

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, TanStack Query v5, Zustand, Tailwind CSS |
| Backend | FastAPI, Python 3.12, Pydantic v2, SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 + pgvector |
| AI | Anthropic Claude (Sonnet for vision/reasoning, Haiku for classification) |
| Queue | Redis + Celery |
| Scraping | Scrapy + BeautifulSoup4 |
| Storage | AWS S3 |

## Prerequisites

- Docker & Docker Compose
- Python 3.12
- Node.js 18+ and pnpm (`npm i -g pnpm`)

## Quickstart

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd cookit

# 2. Set up environment variables
cp .env.example backend/.env
# Edit backend/.env — required fields:
#   ANTHROPIC_API_KEY=sk-ant-...
#   JWT_SECRET=<any long random string>
# Optional (for image storage):
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET

# 3. Run everything
./dev.sh
```

That's it. Visit **http://localhost:3000**.

## Manual setup (step by step)

### Infrastructure
```bash
docker-compose up -d          # starts Postgres 16 + Redis
```

### Backend
```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run DB migration
cd ../db
DATABASE_URL=postgresql+asyncpg://cookit:cookit@localhost:5432/cookit \
  alembic upgrade head
cd ../backend

# Seed condiments catalogue
DATABASE_URL=postgresql+asyncpg://cookit:cookit@localhost:5432/cookit \
  python -m scripts.seed_condiments

# Start API server
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
pnpm install
pnpm dev
```

### Celery worker (optional — for recipe scraping)
```bash
# Worker
cd worker
celery -A celeryconfig worker --loglevel=info

# Scheduler (separate terminal)
celery -A celeryconfig beat --loglevel=info
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | yes | Postgres async URL |
| `REDIS_URL` | yes | Redis URL |
| `ANTHROPIC_API_KEY` | yes | Anthropic API key |
| `JWT_SECRET` | yes | Secret for signing JWTs |
| `AWS_ACCESS_KEY_ID` | no | S3 image upload |
| `AWS_SECRET_ACCESS_KEY` | no | S3 image upload |
| `AWS_S3_BUCKET` | no | S3 bucket name (default: cookit-images) |
| `AWS_REGION` | no | S3 region (default: ap-southeast-1) |
| `JWT_EXPIRE_MINUTES` | no | Token TTL (default: 10080 = 7 days) |

See `backend/.env.example` for a full template.

## Project structure

```
cookit/
├── frontend/          # Next.js 14 app
│   ├── app/           # Pages (App Router)
│   ├── components/ui/ # Button, Card, Input, Select, Badge, Spinner, Modal
│   ├── lib/           # API client, TanStack Query hooks, Zustand stores
│   └── types/         # Shared TypeScript types
├── backend/
│   ├── app/
│   │   ├── api/       # Route handlers (auth, fridge, recipes)
│   │   ├── services/  # Vision, normalise, recommend, S3
│   │   ├── models/    # SQLAlchemy ORM + Pydantic schemas
│   │   └── core/      # DB session, JWT security
│   ├── scripts/       # seed_condiments.py
│   └── tests/         # pytest suite
├── db/                # Alembic migrations + seed CSV
├── worker/            # Celery tasks + Scrapy spiders
├── docker-compose.yml
└── dev.sh             # One-command dev launcher
```

## API overview

```
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/logout

POST   /api/fridge/scan          # Upload photo → detect items
GET    /api/fridge/items
POST   /api/fridge/items
PATCH  /api/fridge/items/{id}
DELETE /api/fridge/items/{id}
GET    /api/fridge/catalog        # Condiments catalogue

GET    /api/recipes/recommend     # Personalised recommendations
GET    /api/recipes/search?q=
GET    /api/recipes/{id}

GET    /health
```

Interactive docs at **http://localhost:8000/docs** when the backend is running.

## Running tests

```bash
# Backend
cd backend
pytest -v

# Frontend
cd frontend
pnpm test
```

## How recommendations work

Three strategies run in parallel and their scores are merged:

1. **SQL overlap (40%)** — counts how many recipe ingredients you already have
2. **Vector similarity (35%)** — embeds your fridge contents and finds semantically similar recipes
3. **Claude creative (25%)** — only fires when strategies 1+2 return fewer than 5 results

Final score: `0.4 × overlap + 0.35 × cosine + 0.25 × ai`

## Notes

- Images are resized client-side to max 2048px before upload to save API tokens
- S3 upload failures are non-fatal — scanning still works, images just aren't stored
- The recipe DB starts empty; run the Celery worker overnight or trigger manually:
  ```bash
  celery -A celeryconfig call worker.tasks.scraper.run_spiders
  ```
