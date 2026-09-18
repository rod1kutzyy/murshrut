# Repository Guidelines

## Purpose and Scope

This file defines how coding agents should work in this repository. It applies to
the whole repository unless a more deeply nested `AGENTS.md` overrides it.
Direct user instructions take precedence over this file.

Keep this file focused on project-specific decisions. Use `README.md` for current
product behavior and integration details, `.github/workflows/ci.yml` for the CI
source of truth, and the existing code and tests for implementation patterns.
`PROMPT.md` is historical product context; when it conflicts with the current
code, tests, README, or an explicit task, do not treat it as authoritative.

## Project Overview

Murshrut is a mobile-first MAX mini-app for discovering events. It provides
onboarding, personalized recommendations, swipe reactions, a filterable catalog,
favorites, event details, sharing, and a map. The stack is:

- React 19, Vite, TypeScript, Tailwind CSS, MAX UI, and Playwright;
- FastAPI, Pydantic, async SQLAlchemy, and Alembic;
- PostgreSQL 17 in Compose and CI; SQLite is supported for local development and
  part of the repository test matrix;
- Nginx as the public entry point;
- demo data locally or PRO.Культура.РФ data in live mode.

The current design intentionally has no ML service, worker, queue, or additional
backend service. Do not introduce one unless the task requires it.

## Repository Map

- `backend/app/bootstrap.py`: composition root and runtime lifecycle.
- `backend/app/service/`: framework-independent entities, commands, results,
  ports, use cases, recommendation/catalog logic, and synchronization.
- `backend/app/repository/`: SQLAlchemy models, queries, mappers, and Unit of Work.
- `backend/app/transport/api/`: FastAPI routes, dependencies, schemas, and error
  translation.
- `backend/app/transport/integrations/`: MAX, JWT, demo, and Culture adapters.
- `backend/alembic/versions/`: ordered database migrations.
- `backend/tests/`: unit, API, architecture, mapper, flow, and repository tests.
- `frontend/src/`: application code; shared API types live in `types.ts`.
- `frontend/tests/`: Playwright tests against the complete demo stack.
- `frontend/public/art/`: bundled fallback SVG artwork.
- `nginx/`, `docker-compose.yml`: local production-shaped stack.
- `.github/workflows/ci.yml`: required quality, backend, migration, Docker, and
  browser checks.

## Working Method

Before changing code:

1. Read the relevant implementation, nearby tests, and the corresponding README
   section.
2. Trace the complete boundary involved: UI -> HTTP schema/mapper -> service ->
   port -> adapter/repository, or the reverse for output.
3. Preserve existing public behavior unless the task explicitly changes it.
4. Prefer the smallest coherent change and extend established patterns.

Do not refactor unrelated code, rename public fields, add dependencies, or alter
infrastructure while solving a narrower task. If a request conflicts with an
invariant below, identify the conflict before making a broad architectural change.

## Backend Architecture

The dependency rule is enforced by `backend/tests/test_architecture.py`:

- `service` must not import transport, repository, configuration, FastAPI,
  SQLAlchemy, HTTP/JWT clients, or Pydantic;
- `repository` may depend on service ports/entities but not transport, FastAPI,
  bootstrap, or the application entry point;
- `transport` may depend on service types but not repository, SQLAlchemy,
  bootstrap, or the application entry point;
- `bootstrap.py` is the composition root that connects concrete adapters.

Keep business rules in `service`. API routes validate transport input, invoke a
service, and map results or service errors. Repositories perform persistence only.
External systems are adapters behind protocols declared in `service/ports.py`.

Use frozen dataclasses for service entities, commands, and results unless mutation
is part of the domain. Keep ORM models inside `repository`. Repositories must return
detached service entities, never ORM instances. Boundary mappers must enumerate
fields explicitly and copy mutable collections (`list` <-> `tuple`) so objects
remain usable after the SQLAlchemy session closes.

Each HTTP request gets one Unit of Work. Services own transaction boundaries and
call `commit()` only after a complete business operation succeeds. Repository
methods may query, mutate, and `flush()`, but must never commit or roll back.
`SqlAlchemyUnitOfWork` owns rollback and session cleanup. Multi-write operations,
including preferences plus onboarding and event upsert plus deactivation, must
remain atomic.

All request-path I/O must be asynchronous. Do not perform blocking network,
database, filesystem, or CPU-heavy work on the event loop. Keep time-dependent
logic testable through `ClockPort`; avoid adding direct wall-clock reads to service
code.

## Domain and Data Invariants

- Live and demo events must never be mixed. An event is visible only for the
  configured provider, active source snapshot, requested city, and relevant time.
- Invalid MAX init data must never fall back to demo authentication. Demo auth is
  available only when `DEMO_MODE=true`.
- MAX init data verification must preserve duplicate-parameter rejection,
  HMAC-SHA256 verification, timestamp limits, and integer ID bounds. JWTs use
  HS256, expire after 24 hours, and remain in frontend memory rather than browser
  storage.
- Production startup must fail without a non-demo JWT secret of at least 32
  characters and a MAX bot token. Culture mode must fail without its API key.
- Event synchronization is serialized per source scope and throttled by the sync
  interval. A successful complete snapshot may upsert events and deactivate
  missing ones in one transaction. A partial, malformed, or failed upstream fetch
  must not deactivate cached events.
- On `ProviderUnavailable`, rollback the failed transaction and use cached events
  only if current active cache exists. Do not silently inject demo data.
- Keep provider `external_id` stable. If a previously inactive event reappears,
  reactivate/update it without replacing its internal ID or losing reactions.
- Recommendations exclude reacted-to events. The catalog may include disliked
  events, applies all filters before pagination, and returns `is_saved`.
- Date filters use the event timezone and half-open day windows. Preserve the
  distinction between unknown price, free events, and paid events.
- A reaction is one upserted `like` or `dislike` per user/event. The swipe UI must
  remove a card only after the server saves the reaction successfully.

When changing scoring, catalog semantics, synchronization, authentication, or
source normalization, update focused tests and the matching README explanation.

## API and Error Handling

Preserve `/api/v1` contracts and deep links (`event_<UUID>`) unless a breaking
change is explicitly requested. Keep Pydantic request/response schemas in
`transport/api/schemas.py`, service commands/results in `service`, and conversions
in explicit transport mappers. Update frontend types and all affected callers when
an API field changes.

Expected business failures belong in `service/errors.py`. Map them centrally to
HTTP status codes in `transport/api/application.py`; do not raise FastAPI errors
from service or repository code. Do not expose secrets, SQL errors, stack traces,
or upstream URLs that can contain API keys.

## Database and Migrations

Use async SQLAlchemy APIs and parameterized expressions. Changes must work on the
supported PostgreSQL path and, where repository tests exercise it, SQLite. Keep
dialect-specific behavior explicit, as with conflict upserts.

Every schema change requires a new Alembic migration and matching model changes.
Do not edit or reorder existing migrations that may already be applied. Verify
both upgradeability and model parity with `alembic upgrade head` and
`alembic check`. Preserve data and stable IDs during migrations unless destructive
behavior is explicitly required.

## External Integrations and Security

Treat provider responses as untrusted: validate shapes and ranges, accept only
safe HTTP(S) URLs, sanitize upstream HTML, and handle invalid timezones and
timestamps. Do not guess asset URLs or change the documented coordinate order for
PRO.Культура.РФ. Never log tokens, JWT secrets, admin tokens, init data, provider
keys, or request URLs containing keys.

Keep external calls in backend adapters. Frontend code must not receive provider
or bot secrets. Preserve graceful cache fallback and clear user-facing Russian
errors without leaking internal details.

## Frontend Rules

TypeScript is strict. Prefer typed functional components and shared types over
`any`; keep server DTO shapes synchronized with `frontend/src/types.ts`. Use the
central `api()` helper so authentication and error behavior stay consistent.

Keep the app mobile-first and usable at the Playwright viewport (390x844). Preserve
loading, empty, failure, retry, and busy states. Avoid optimistic UI changes that
lose user intent on a failed request. Interactive icon-only controls need accessible
names, and asynchronous notices/errors should remain perceivable.

MAX Bridge features must be capability-checked because the app also runs in a
regular browser. Register and clean up Bridge callbacks. Sharing APIs must be
invoked from a user action. Keep external links safe with `rel="noreferrer"`.

Use existing CSS and MAX UI conventions before adding another UI system. Do not
manually edit `package-lock.json`; update it through npm only when dependencies
actually change. Do not replace bundled artwork or add remote assets without a
clear product need and appropriate attribution.

## Style

- Python: 4 spaces, `snake_case`, explicit boundary types, Ruff line length 88.
- TypeScript/React: 2 spaces, `camelCase` values/functions, `PascalCase`
  components, Prettier formatting.
- Follow existing names and user-facing Russian copy. Avoid drive-by formatting of
  untouched files; Python formatting is being adopted incrementally.
- Comments should explain non-obvious constraints, not restate the code.

## Validation Commands

Use CI versions: Python 3.13, Node.js 22, and PostgreSQL 17. Run the narrowest
relevant check while iterating, then the applicable final checks below.

Backend from the repository root:

```bash
python -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt
python -m ruff check backend
python -m ruff format --check <changed-python-files>
python -m pytest backend/tests -q
```

Format changed Python files with `python -m ruff format <files>`. Do not format the
entire legacy backend as part of an unrelated change. For PostgreSQL repository
coverage, point `TEST_REPOSITORY_DATABASE_URL` at an isolated disposable database;
the tests create and drop their own schema.

Migration validation from `backend/` with `DATABASE_URL` configured:

```bash
alembic upgrade head
alembic check
```

Frontend from `frontend/`:

```bash
npm ci
npm run format:check
npm run build
```

Full-stack/browser validation from the repository root:

```bash
docker compose config --quiet
docker compose up --build -d --wait --wait-timeout 180
curl --fail http://localhost:8080/api/health
cd frontend && npx playwright install chromium && npm run test:e2e
```

Playwright expects the demo stack at `TEST_BASE_URL` (default
`http://localhost:8080`) and intentionally uses one worker because tests share one
demo profile. Do not parallelize these tests without first isolating their state.
Use `docker compose down --volumes --remove-orphans` only for a disposable test
stack whose data is safe to delete.

Add or update regression tests for changed behavior. Service tests should use fake
ports and controlled clocks; integration tests must not depend on live MAX or
Culture credentials. If a required check cannot run, report exactly what was not
run and why.

## Git and Change Hygiene

Keep changes scoped and preserve unrelated user work. Do not rewrite history,
force-push, merge, create a pull request, or publish/deploy unless explicitly
requested. Use focused branches and short imperative English commit subjects when
commits are requested. Do not commit `.env`, credentials, test artifacts, browser
reports, local databases, or virtual environments.

## Definition of Done

A task is complete when:

- requested behavior works across every affected boundary;
- architectural and security invariants remain intact;
- database and API compatibility are preserved or explicitly documented;
- relevant regression tests are added or updated;
- changed files are formatted and applicable lint, build, test, and migration
  checks pass;
- README documentation is updated when user-visible behavior or setup changes;
- no unrelated files, dependencies, migrations, or generated lockfile changes are
  included.
