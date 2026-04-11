# CLAUDE.md — Cookit

This file is the single source of truth for Claude Code when working on this project.
Read it fully before writing any code, running any command, or making any architectural decision.

---

## Project overview

**Cookit** is a full-stack application that lets users:
1. Scan their fridge with a photo → AI detects and classifies food items
2. Manually add condiments and sauces via dropdown or free text
3. Browse a scraped recipe database kept fresh by a background pipeline
4. Receive personalised recipe recommendations based on what's in their fridge

**Monorepo layout:**
```
cookit/
├── frontend/          # Next.js 14 (App Router), TypeScript
├── backend/           # FastAPI (Python 3.11+)
├── db/                # Alembic migrations
├── worker/            # Celery tasks (scraper pipeline)
└── CLAUDE.md
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, TanStack Query v5, Zustand, Tailwind CSS v3 |
| Backend | FastAPI, Python 3.11+, Pydantic v2, SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 + pgvector extension |
| Migrations | Alembic |
| AI | Anthropic SDK (Python) — claude-sonnet-4-20250514 for vision/reasoning, claude-haiku-4-5-20251001 for classification/normalization |
| Storage | AWS S3 (fridge images) |
| Queue | Redis + Celery (scraping jobs) |
| Scraping | `recipe-scrapers` + `httpx` + Celery (Phase 2+); TheMealDB API (Phase 1 seed) |
| Auth | JWT (python-jose) + httpOnly cookie |
| Testing | pytest + pytest-asyncio (backend), Vitest + Testing Library (frontend) |
| Containerisation | Docker + docker-compose for local dev |

---

## Repository structure

```
frontend/
├── app/
│   ├── (auth)/
│   │   └── login/page.tsx
│   ├── fridge/
│   │   ├── page.tsx           # Fridge dashboard (current items)
│   │   ├── scan/page.tsx      # Camera / upload UI
│   │   └── manual/page.tsx    # Manual add / condiments
│   └── recipes/
│       ├── page.tsx           # Recommendation results
│       └── [id]/page.tsx      # Recipe detail
├── components/
│   ├── fridge/
│   ├── recipes/
│   └── ui/                    # Shared primitives (Button, Card, etc.)
├── lib/
│   ├── api.ts                 # Typed API client (fetch wrapper)
│   ├── hooks/                 # TanStack Query hooks
│   └── stores/                # Zustand stores
└── types/                     # Shared TypeScript types

backend/
├── app/
│   ├── main.py                # FastAPI app, lifespan, CORS
│   ├── config.py              # Settings (pydantic-settings)
│   ├── dependencies.py        # Shared FastAPI deps (db session, current user)
│   ├── api/
│   │   ├── auth.py
│   │   ├── fridge.py          # POST /fridge/scan, CRUD /fridge/items
│   │   └── recipes.py         # GET /recipes/recommend, GET /recipes/{id}
│   ├── services/
│   │   ├── vision.py          # Claude Sonnet vision calls
│   │   ├── normalize.py       # Claude Haiku normalization
│   │   ├── recommend.py       # 3-strategy recommendation cascade
│   │   └── storage.py         # S3 upload helpers
│   ├── models/
│   │   ├── db.py              # SQLAlchemy ORM models
│   │   └── schemas.py         # Pydantic request/response schemas
│   └── core/
│       ├── security.py        # JWT helpers
│       └── database.py        # Async engine + session factory

worker/
├── celeryconfig.py
└── tasks/
    ├── seed.py                # Phase 1: TheMealDB bulk import
    ├── scraper.py             # Phase 2+: recipe-scrapers + httpx crawler
    └── embedder.py            # Embedding generation task

scripts/
└── seed_recipes.py            # One-shot Phase 1 seed script (run manually)

db/
├── alembic.ini
└── versions/                  # Migration files
```

---

## Database schema

### Core tables

```sql
-- Users
users (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email        VARCHAR(255) UNIQUE NOT NULL,
  name         VARCHAR(255),
  password_hash TEXT NOT NULL,
  created_at   TIMESTAMPTZ DEFAULT now()
)

-- Fridge contents per user
fridge_items (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  item_name    VARCHAR(255) NOT NULL,
  category     VARCHAR(100),          -- 'produce', 'dairy', 'protein', 'condiment', 'leftover', 'other'
  quantity     DECIMAL(10,2),
  unit         VARCHAR(50),           -- 'g', 'ml', 'count', 'tbsp', etc.
  source       VARCHAR(20) NOT NULL,  -- 'vision' | 'manual'
  confidence   FLOAT,                 -- 0-1, null for manual
  updated_at   TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, item_name)          -- upsert target
)

-- Pre-seeded condiments / sauces catalogue (~200 rows)
condiments_catalog (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name         VARCHAR(255) UNIQUE NOT NULL,
  category     VARCHAR(100),
  default_unit VARCHAR(50)
)

-- Scraped recipes
recipes (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title        VARCHAR(500) NOT NULL,
  source_url   TEXT UNIQUE NOT NULL,  -- dedup key
  ingredients  JSONB NOT NULL,        -- [{name, quantity, unit}]
  steps        JSONB NOT NULL,        -- [{step_number, instruction}]
  cuisine      VARCHAR(100),
  tags         TEXT[],
  embedding    vector(384),           -- sentence-transformers/all-MiniLM-L6-v2
  scraped_at   TIMESTAMPTZ DEFAULT now()
)

-- Normalised ingredient rows (for SQL overlap queries)
recipe_ingredients (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recipe_id       UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
  canonical_name  VARCHAR(255) NOT NULL,
  quantity        DECIMAL(10,2),
  unit            VARCHAR(50)
)

CREATE INDEX ON recipe_ingredients(canonical_name);
CREATE INDEX ON recipes USING hnsw (embedding vector_cosine_ops);
```

**Upsert pattern for fridge_items:**
```sql
INSERT INTO fridge_items (user_id, item_name, category, quantity, unit, source, confidence)
VALUES (...)
ON CONFLICT (user_id, item_name) DO UPDATE
  SET quantity = EXCLUDED.quantity,
      category = EXCLUDED.category,
      source   = EXCLUDED.source,
      confidence = EXCLUDED.confidence,
      updated_at = now();
```

---

## AI model selection rules

| Task | Model | Reason |
|---|---|---|
| Fridge photo analysis | `claude-sonnet-4-20250514` | Best vision accuracy; counting items requires strong spatial reasoning |
| Ingredient name normalisation | `claude-haiku-4-5-20251001` | Fast, cheap; classification task with clear schema |
| Recipe recommendations (creative) | `claude-sonnet-4-20250514` | Multi-step reasoning over fridge contents |
| Tag extraction from scraped HTML | `claude-haiku-4-5-20251001` | High-volume, low-complexity |

**Never swap Haiku in for vision tasks.** The quality drop on spatial counting is significant.

---

## API contract

### Fridge endpoints

```
POST   /api/fridge/scan              Upload photo → detect items
GET    /api/fridge/items             List current fridge contents
POST   /api/fridge/items             Add item manually
PATCH  /api/fridge/items/{id}        Update quantity / unit
DELETE /api/fridge/items/{id}        Remove item

GET    /api/fridge/catalog           Condiments catalogue (for dropdown)
```

**POST /api/fridge/scan** — multipart/form-data
- Request: `file` (image, max 10 MB), `user_id` from JWT
- Response:
```json
{
  "detected": [
    { "item_name": "chicken breast", "category": "protein", "quantity": 2, "unit": "count", "confidence": 0.94 }
  ],
  "saved_count": 3
}
```

**POST /api/fridge/items** — manual add
```json
{
  "item_name": "fish sauce",
  "quantity": 1,
  "unit": "bottle",
  "source": "manual"
}
```

### Recipe endpoints

```
GET    /api/recipes/recommend        Ranked recommendations for current user
GET    /api/recipes/{id}             Full recipe detail
GET    /api/recipes/search?q=        Text search
```

**GET /api/recipes/recommend** — response:
```json
{
  "recommendations": [
    {
      "recipe_id": "uuid",
      "title": "Thai Basil Chicken",
      "match_score": 0.87,
      "matched_ingredients": ["chicken breast", "fish sauce", "garlic"],
      "missing_ingredients": ["thai basil", "oyster sauce"],
      "cuisine": "Thai",
      "source_url": "https://..."
    }
  ]
}
```

---

## Service implementation details

### Vision service (`backend/app/services/vision.py`)

```python
VISION_SYSTEM_PROMPT = """
You are a kitchen inventory assistant. Analyse the provided fridge photo and identify all visible food items.

Return ONLY a JSON array with no additional text, markdown, or explanation:
[
  {
    "item_name": "<canonical lowercase name>",
    "category": "<one of: produce|dairy|protein|condiment|leftover|beverage|other>",
    "quantity": <number>,
    "unit": "<count|g|ml|pack|bottle|jar|bunch|other>",
    "confidence": <0.0-1.0>
  }
]

Rules:
- Use canonical names: "chicken breast" not "raw chicken", "whole milk" not "milk"
- Estimate quantity conservatively when unclear
- Set confidence < 0.7 for partially visible or ambiguous items
- Do not invent items; only include what is clearly visible
"""
```

Call pattern — always pass image as base64 URL:
```python
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    system=VISION_SYSTEM_PROMPT,
    messages=[{
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64_data}},
            {"type": "text", "text": "Identify all food items in this fridge photo."}
        ]
    }]
)
```

Strip any markdown fences before `json.loads()`. Validate each item with a Pydantic model. Drop items with confidence < 0.5.

### Normalisation service (`backend/app/services/normalize.py`)

Used for free-text manual entries and scraped ingredient names.

```python
NORMALIZE_SYSTEM_PROMPT = """
Normalise the following ingredient name to a canonical form.
Return ONLY a JSON object, no markdown:
{
  "canonical_name": "<lowercase, singular, no brand names>",
  "category": "<produce|dairy|protein|condiment|grain|spice|other>",
  "default_unit": "<count|g|ml|tbsp|tsp|cup|bunch>"
}
"""
```

Batch scraped ingredients: send up to 20 per Haiku call to reduce API calls.

### Recommendation service (`backend/app/services/recommend.py`)

Three strategies run in parallel via `asyncio.gather`. Results are merged and re-ranked by a weighted score.

**Strategy A — SQL overlap (weight: 0.4):**
```sql
SELECT
  r.id,
  r.title,
  COUNT(ri.id) FILTER (WHERE ri.canonical_name = ANY(:user_items)) AS matched,
  COUNT(ri.id) AS total,
  COUNT(ri.id) FILTER (WHERE ri.canonical_name = ANY(:user_items))::float / COUNT(ri.id) AS overlap_score
FROM recipes r
JOIN recipe_ingredients ri ON ri.recipe_id = r.id
GROUP BY r.id
HAVING overlap_score >= 0.4
ORDER BY overlap_score DESC
LIMIT 20;
```

**Strategy B — pgvector cosine similarity (weight: 0.35):**
- Embed the user's ingredient list as a single comma-separated string
- Use `sentence-transformers/all-MiniLM-L6-v2` (same model used at scrape time)
- Query: `ORDER BY embedding <=> :query_embedding LIMIT 20`

**Strategy C — Claude Sonnet creative (weight: 0.25):**
- Only called if strategies A+B return < 5 results, or if explicitly requested
- Pass top-10 fridge items in the prompt, ask for recipe names + reasoning
- Do NOT stream this response; parse as JSON

**Final ranking:** `final_score = 0.4 * overlap + 0.35 * cosine + 0.25 * ai_score`, deduplicated by recipe_id.

---

## Recipe database pipeline

The recipe DB is built in three phases. Do not skip ahead — each phase unblocks the next.

---

### Phase 1 — Seed immediately (TheMealDB API)

Run this once on first deploy to populate ~280 recipes before the scraper pipeline is ready.
This gives the recommendation engine something to work with from day one.

**Script:** `scripts/seed_recipes.py`

```python
import httpx
from app.models.db import Recipe, RecipeIngredient
from app.services.normalize import batch_normalize_ingredients

MEALDB_BASE = "https://www.themealdb.com/api/json/v1/1"

async def seed_from_mealdb(session):
    # Fetch all meal IDs by iterating categories
    categories_resp = httpx.get(f"{MEALDB_BASE}/categories.php").json()
    categories = [c["strCategory"] for c in categories_resp["categories"]]

    for category in categories:
        meals = httpx.get(f"{MEALDB_BASE}/filter.php?c={category}").json()
        for meal_stub in meals["meals"] or []:
            # Fetch full detail
            detail = httpx.get(
                f"{MEALDB_BASE}/lookup.php?i={meal_stub['idMeal']}"
            ).json()["meals"][0]

            # Map TheMealDB fields → recipes schema
            ingredients = [
                detail[f"strIngredient{i}"]
                for i in range(1, 21)
                if detail.get(f"strIngredient{i}")
            ]
            measures = [
                detail[f"strMeasure{i}"]
                for i in range(1, 21)
                if detail.get(f"strIngredient{i}")
            ]

            recipe = Recipe(
                title=detail["strMeal"],
                source_url=f"https://www.themealdb.com/meal/{detail['idMeal']}",
                ingredients=[
                    {"name": ing, "measure": meas}
                    for ing, meas in zip(ingredients, measures)
                ],
                steps=[{"step_number": 1, "instruction": detail["strInstructions"]}],
                cuisine=detail.get("strArea"),
                tags=(detail.get("strTags") or "").split(","),
            )
            session.add(recipe)

    await session.commit()
```

Run with:
```bash
cd backend
python -m scripts.seed_recipes
```

**TheMealDB key endpoints used:**
```
GET /categories.php                    # list all categories
GET /filter.php?c={Category}           # meal stubs per category
GET /lookup.php?i={idMeal}             # full recipe detail
GET /filter.php?i={ingredient}         # meals by ingredient (useful for testing)
```

No API key required for the free tier.

---

### Phase 2 — Grow the DB (recipe-scrapers + httpx + Celery)

**Do not use Scrapy.** Use `recipe-scrapers` (631 supported sites, MIT licence) for HTML parsing
and `httpx` for async HTTP. Scrapy is synchronous and must never be imported into the FastAPI process.

```bash
pip install recipe-scrapers httpx tenacity
```

**Core fetch + parse pattern** (`worker/tasks/scraper.py`):

```python
import asyncio
import httpx
from recipe_scrapers import scrape_html
from tenacity import retry, wait_exponential, stop_after_attempt
from urllib.robotparser import RobotFileParser

HEADERS = {"User-Agent": "Cookit-Bot/1.0 (personal project; respectful crawler)"}
CRAWL_DELAY = 2.0  # seconds between requests per domain

@retry(wait=wait_exponential(min=2, max=30), stop=stop_after_attempt(3))
async def fetch_and_parse(url: str) -> dict:
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    scraper = scrape_html(resp.text, org_url=url)
    return scraper.to_json()   # maps directly to recipes schema

def is_allowed(url: str, user_agent: str = "Cookit-Bot") -> bool:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)
    rp.read()
    return rp.can_fetch(user_agent, url)
```

**Crawl targets and sitemap entry points:**

| Site | Sitemap / start URL | Notes |
|---|---|---|
| AllRecipes | `https://www.allrecipes.com/sitemap.xml` | Huge volume; use category sitemaps |
| BBC Good Food | `https://www.bbcgoodfood.com/sitemap.xml` | High quality; European cuisine |
| Food.com | `https://www.food.com/sitemap` | robots.txt only blocks `/members/` and search pages; recipe pages open |

**Celery schedule:**
```python
# worker/celeryconfig.py
beat_schedule = {
    "scrape-recipes-nightly": {
        "task": "worker.tasks.scraper.crawl_all_sources",
        "schedule": crontab(hour=2, minute=0),   # 2 AM daily
    },
    "generate-embeddings": {
        "task": "worker.tasks.embedder.embed_pending",
        "schedule": crontab(minute="*/30"),       # every 30 min
    },
}
```

**Dedup strategy:**
- Primary: `ON CONFLICT (source_url) DO NOTHING`
- Secondary: normalise title + Levenshtein distance < 5 before insert

---

### Phase 3 — Southeast Asia coverage (cookpad + Thai food blogs)

Add after Phase 2 is stable. These sites require the same `recipe-scrapers` + `httpx` pattern.
`recipe-scrapers` natively supports `cookpad.com`.

**Additional crawl targets:**

| Site | URL | Notes |
|---|---|---|
| Cookpad | `https://cookpad.com/th` | Large Thai user base; supported by `recipe-scrapers` |
| Thai Food Master | `https://thaifoodmaster.com` | Authentic Thai recipes, well-structured HTML |
| Arroy-D | `https://www.arroy-d.com/recipes` | Thai cuisine; structured markup |
| Archana's Kitchen | `https://www.archanaskitchen.com` | Southeast/South Asian; `recipe-scrapers` supported |

**wild_mode fallback** for unsupported sites:
```python
from recipe_scrapers import scrape_html

scraper = scrape_html(html, org_url=url, wild_mode=True)
# wild_mode attempts Schema.org JSON-LD extraction on any site
# Output quality is lower — validate before inserting
if scraper.title() and len(scraper.ingredients()) > 2:
    return scraper.to_json()
```

Flag `wild_mode=True` results with `source='scraped_wild'` in the DB so they can be reviewed or
re-processed later.

---

## Environment variables

```bash
# backend/.env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/cookit
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=sk-ant-...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=cookit-images
AWS_REGION=ap-southeast-1
JWT_SECRET=...
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080     # 7 days

# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Never commit `.env` files. Use `.env.example` with placeholder values.

---

## Development setup

```bash
# 1. Start infrastructure
docker-compose up -d postgres redis

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. Celery worker (separate terminal)
cd worker
celery -A celeryconfig worker --loglevel=info
celery -A celeryconfig beat --loglevel=info

# 4. Frontend
cd frontend
pnpm install
pnpm dev
```

**pgvector setup** (run once after Postgres is up):
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## Coding conventions

### Python (backend + worker)

- Python 3.11+, type hints on every function signature
- Pydantic v2 for all request/response schemas — use `model_validate`, not `parse_obj`
- SQLAlchemy 2.0 async style: `async with session.begin()`, not `session.commit()` manually
- All Anthropic API calls wrapped in a retry helper with exponential backoff (max 3 retries)
- Service functions return Pydantic models, never raw dicts
- No `print()` — use `logging.getLogger(__name__)` everywhere
- Keep route handlers thin: validate input, call service, return response. Business logic lives in `services/`

```python
# Good pattern
@router.post("/scan", response_model=ScanResponse)
async def scan_fridge(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await vision_service.detect_items(file, db, current_user.id)
    return result
```

### TypeScript (frontend)

- Strict mode on (`"strict": true` in tsconfig)
- No `any` — use `unknown` and narrow properly
- All API calls go through `lib/api.ts` typed client, never raw `fetch` in components
- Server Components for data fetching where possible; Client Components only for interactivity
- TanStack Query for all async state — no `useEffect` + `fetch` patterns
- Zustand only for truly global client state (auth, fridge item cache)
- Component files: one component per file, named export + default export both

```typescript
// Good: typed API hook
export function useFridgeItems() {
  return useQuery({
    queryKey: ['fridge', 'items'],
    queryFn: () => api.get<FridgeItem[]>('/fridge/items'),
  })
}
```

### General rules

- Meaningful variable names — `detectedItems` not `data`, `recipeMatchScore` not `score`
- No magic numbers — extract to named constants
- Error handling: never silently swallow exceptions. Log + re-raise or return a typed error response
- All database queries must use parameterised inputs — no f-string SQL

---

## Testing

### Backend

```bash
cd backend
pytest -v                     # all tests
pytest tests/services/        # services only
pytest -k "test_vision"       # specific test
```

- Unit test each service in isolation — mock the Anthropic client
- Integration tests use a test Postgres DB spun up by docker-compose
- Fixture for seeded `condiments_catalog` and sample `recipes` in `tests/conftest.py`
- Coverage target: 80% on `services/` and `api/`

```python
# Mock pattern for Claude calls
@pytest.fixture
def mock_anthropic(monkeypatch):
    mock = MagicMock()
    mock.messages.create.return_value = MockResponse(
        content=[MockContent(text='[{"item_name":"chicken breast",...}]')]
    )
    monkeypatch.setattr("app.services.vision.client", mock)
    return mock
```

### Frontend

```bash
cd frontend
pnpm test           # Vitest
pnpm test:e2e       # Playwright (requires backend running)
```

- Unit test hooks and utility functions
- Component tests with Testing Library for interactive components (scan upload, condiment dropdown)
- Mock API responses with `msw`

---

## Common tasks

### Add a new API endpoint
1. Add Pydantic schemas to `backend/app/models/schemas.py`
2. Add service logic to appropriate file in `backend/app/services/`
3. Add route to `backend/app/api/<router>.py`
4. Register router in `backend/app/main.py` if new file
5. Add typed API function to `frontend/lib/api.ts`
6. Add TanStack Query hook to `frontend/lib/hooks/`

### Add a DB migration
```bash
cd db
alembic revision --autogenerate -m "add_column_x_to_recipes"
alembic upgrade head
```

Always review the generated migration file before applying. Never edit existing migrations.

### Seed condiments catalogue
```bash
cd backend
python -m scripts.seed_condiments   # runs db/seeds/condiments.csv
```

### Seed recipes (Phase 1 — run once)
```bash
cd backend
python -m scripts.seed_recipes
```

### Run scraper manually (Phase 2+)
```bash
cd worker
celery -A celeryconfig call worker.tasks.scraper.crawl_all_sources
```

---

## Known constraints and gotchas

- **Image size**: Claude Vision performs well up to ~5 MB. Resize client-side to max 2048px before upload to save tokens.
- **pgvector dimension**: The embedding model (`all-MiniLM-L6-v2`) outputs 384-dimensional vectors. Do not change the model without a full re-embedding migration.
- **No Scrapy**: The scraper uses `recipe-scrapers` + `httpx`, not Scrapy. Scrapy is synchronous — never import it into the FastAPI process or anywhere outside Celery workers.
- **recipe-scrapers is a parser, not a fetcher**: It handles HTML parsing only. You must implement your own HTTP fetching, rate limiting, and `robots.txt` compliance. Use the `is_allowed()` helper in `worker/tasks/scraper.py` before every request.
- **TheMealDB free tier**: No API key required for the public API key `1`. The DB has ~280 meals — enough to seed, not enough to rely on long-term. Phase 2 scraping is what grows the DB.
- **wild_mode recipes**: Rows with `source='scraped_wild'` came from unsupported sites via Schema.org fallback. Quality is lower — validate ingredient count (> 2) and title presence before inserting.
- **Rate limits**: Haiku batching is capped at 20 items per call. Sonnet vision calls are one image per call. Wrap both in `asyncio.Semaphore(5)` to avoid hitting API rate limits during bulk operations.
- **S3 image lifecycle**: Set a 90-day S3 lifecycle rule on the fridge-images bucket. Images are only needed at scan time; the detected items are persisted in the DB.
- **pgvector HNSW index**: Requires Postgres 16 + pgvector 0.5+. The HNSW index is built at migration time. Rebuilding it on a large dataset is slow — do not drop and recreate in production without a maintenance window.
- **fridge_items upsert**: The unique constraint is `(user_id, item_name)`. If a user scans twice, quantities are overwritten, not summed. This is intentional — the photo is the source of truth.
