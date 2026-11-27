# RevoTask

RevoTask is a Trello-like task management application built through a disciplined AI-driven development workflow. Users create boards, organize work into columns, move cards by drag-and-drop, collaborate through comments, and track the cards assigned to them. Board administrators also manage member access, oversee all cards, and monitor team activity through analytics and notifications.

The project has two parts: a Flask REST API (`backend/`, deployed to Railway) and a Next.js frontend (`frontend/`, deployed to Vercel).

| | URL |
|---|---|
| Frontend (Vercel) | https://module-4-alzedmkrom.vercel.app/ |
| API (Vercel) | https://module-4-alzedmkrom.vercel.app/ |
| API docs (Swagger UI) | `<API URL>/api/docs` when `SWAGGER_ENABLED=true` (off by default in production) |

---

## Features implemented

**Authentication and access**
- Register and log in with a JWT. Registration signs the new user in automatically.
- The token is kept in an httpOnly cookie set by a Server Action. Protected routes (`/my-tasks`, `/profile`) redirect anonymous visitors to `/login`, and an expired token redirects to `/login?next=...` with one "Session expired" toast.
- Per-board roles (Admin, Member, Guest, Anonymous). Public boards can be read without logging in.

**Boards, columns and cards**
- Create, rename and delete boards. Toggle a board between public and private.
- Add, rename and delete columns, and mark one column per board as the done column.
- Create, edit, assign and delete cards (cards are soft-deleted). Members delete only their own work.
- Drag-and-drop between columns with the native HTML5 API, using the FLOAT order strategy (midpoint insertion, server-side rebalance). The UI updates at once and restores the exact position if the server rejects the move.
- A "Move to column" select in the card modal as the keyboard and touch fallback.
- Card search with a 300 ms debounce. It filters the cards already on the board in the browser, because the API has no search endpoint.

**Collaboration**
- Create, edit and delete comments on a card (owner only).
- Notifications polled every 30 seconds, paused while the tab is hidden, with an unread badge on the bell that comes from the API's `unread_count`.
- Board member management for Admins: add by email, change role, remove. The last Admin cannot be removed.

**Personal pages**
- My Tasks: cards assigned to you, grouped by board.
- Profile: change your name and email.

**Admin tools and API**
- Analytics per board: cards per column, completed this week, and member activity.
- Swagger UI and an OpenAPI 3 document generated from the Marshmallow schemas.

**Testing**
- Backend: 204 pytest tests on PostgreSQL 18 with 95.7% coverage.
- Frontend: 99 Vitest and React Testing Library tests, with MSW for the API.
- Playwright: 4 end-to-end tests (route states and registration). The full auth and Kanban E2E suite is **not written yet**; it is listed under optional tasks 16 to 24 in `.kiro/specs/frontend/tasks.md`.

---

## Technologies used

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, react-hot-toast |
| Frontend tests | Vitest, React Testing Library, MSW, fast-check, Playwright |
| Backend | Flask, SQLAlchemy, Flask-Migrate (Alembic), Flask-JWT-Extended, Flask-CORS, Marshmallow, apispec, python-dotenv, Gunicorn |
| Database | PostgreSQL 18 |
| Backend tests | pytest, Hypothesis |
| Deployment | Railway (backend, see `backend/railway.json`), Vercel (frontend, see `frontend/vercel.json`) |
| AI tools | Kiro (IDE, specs, steering and sub-agents). Kiro CLI: _not described yet, see the AI Workflow Summary_ |

---

## How to run the project locally

**Prerequisites:** Git, Python 3.11+, PostgreSQL 18, Node.js 20.9+, npm 12+.

### 1. Clone the repository

```bash
git clone https://github.com/Revou-FSSE-Jun26/module-4-alzedmkrom.git
cd module-4-alzedmkrom
```

### 2. Run the Flask API

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env     # then edit .env
flask db upgrade         # applies all migrations
flask seed               # optional: demo users, boards, cards
flask run                # http://localhost:5000
```

Edit `.env` using `.env.example` as the reference:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string, for example `postgresql://USER:PASSWORD@127.0.0.1:5432/revotask_db` |
| `JWT_SECRET_KEY` | Long random value used to sign JWTs |
| `JWT_EXPIRES_MINUTES` | Token lifetime in minutes (default 60) |
| `CORS_ORIGINS` | Comma-separated allowed origins (default `http://localhost:3000`) |
| `SEED_PASSWORD` | Password for the demo users created by `flask seed` (default `revotask-dev`) |
| `SWAGGER_ENABLED` | `true` or `false`. Defaults to `true` locally and `false` when `FLASK_ENV=production` |

With Swagger on, the API docs are at `http://localhost:5000/api/docs`.

### 3. Run the Next.js app

In a second terminal:

```bash
cd frontend
npm install              # .npmrc sets allow-remote=all, see the note below
cp .env.example .env.local   # then edit .env.local
npm run dev              # http://localhost:3000
```

Edit `.env.local` using `.env.example` as the reference:

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | API origin used in the browser, for example `http://localhost:5000`. No trailing slash and no `/api` |
| `API_BASE_URL` | Same origin, used by Server Components. Falls back to `NEXT_PUBLIC_API_BASE_URL` when unset |
| `PLAYWRIGHT_BASE_URL` | Frontend origin for the E2E tests, for example `http://localhost:3000` |

> `frontend/.npmrc` sets `allow-remote=all`. npm 12 blocks the tarball URL of Tailwind's optional WASM package and otherwise fails with `EALLOWREMOTE`.

After `flask seed`, you can log in as `alice@revotask.test`, `bob@revotask.test` or `carol@revotask.test` with the `SEED_PASSWORD` value.

### Other frontend commands

| Command | Description |
|---|---|
| `npm run build` | Run ESLint, then build for production |
| `npm run typecheck` | TypeScript check without emitting files |
| `npm run lint` | ESLint |

---

## How to run the test suite

There are three layers.

### 1. Backend: pytest

From the Flask project root (`backend/`, with the virtual environment active). The tests need PostgreSQL 18. With `TEST_DATABASE_URL` unset, they start a throwaway cluster from the PostgreSQL 18 install (set `PG_BIN_DIR` if it is not in the default location).

```bash
cd backend
pytest -v
```

### 2. Frontend: React Testing Library

From the Next.js project root (`frontend/`):

```bash
cd frontend
npm test
```

### 3. End to end: Playwright

Run the full Playwright suite against the live Vercel URL (set `PLAYWRIGHT_BASE_URL` to it, in `.env.local` or in the shell):

```bash
cd frontend
npx playwright install          # downloads the browsers (first run only)
npx playwright test             # runs against PLAYWRIGHT_BASE_URL
npx playwright show-report      # opens the HTML report
```

To run against a local app instead, start the API (seeded with `flask seed`) and `npm run dev`, then set `PLAYWRIGHT_BASE_URL=http://localhost:3000`.

---

## Screenshots

Screenshots are stored in `docs/screenshots/`. None are captured yet. They need the deployed app, except where noted.

| # | Screenshot | File | Status |
|---|---|---|---|
| 1 | Postman: all 8 blueprints reachable on the public API URL | `docs/screenshots/postman-blueprints.png` | Pending deployment |
| 2 | Dashboard | `docs/screenshots/dashboard.png` | Pending |
| 3 | Board Detail with columns and cards | `docs/screenshots/board-detail.png` | Pending |
| 4 | Card Detail Modal with comments | `docs/screenshots/card-modal.png` | Pending |
| 5 | My Tasks | `docs/screenshots/my-tasks.png` | Pending |
| 6 | Profile | `docs/screenshots/profile.png` | Pending |
| 7 | Register | `docs/screenshots/register.png` | Pending |
| 8 | Login | `docs/screenshots/login.png` | Pending |
| 9 | A card being dragged between columns | `docs/screenshots/drag-card.png` | Pending |
| 10 | Notification bell with an unread count | `docs/screenshots/notification-bell.png` | Pending |
| 11 | Playwright HTML report, all tests passed against the live URL | `docs/screenshots/playwright-report.png` | Pending deployment and the full E2E suite |

---

## Deploying

**Backend on Railway.** `backend/railway.json` sets the start command (`gunicorn ... "app:create_app()"`), runs `flask db upgrade` before each deploy, and uses `/api/health` as the health check. Set `DATABASE_URL`, `JWT_SECRET_KEY`, `CORS_ORIGINS` and `FLASK_ENV=production` in the Railway service. `SWAGGER_ENABLED` is off in production unless you set it to `true`.

**Frontend on Vercel.**
1. Import the repository and set **Root Directory** to `frontend`. `frontend/vercel.json` sets the framework and the install and build commands.
2. Set `NEXT_PUBLIC_API_BASE_URL` and `API_BASE_URL` to the API origin (the Railway URL, no trailing slash and no `/api`). `NEXT_PUBLIC_*` values are compiled in, so a change needs a redeploy.
3. `PLAYWRIGHT_BASE_URL` is not needed in Vercel.
4. After the first deployment, check the install step of the build log to confirm the `.npmrc` setting was read.

**CORS.** The backend `CORS_ORIGINS` must list the exact Vercel origin as `https://<host>` (no trailing slash, no path) and `http://localhost:3000`. Server Component requests are server-to-server and need no entry. A Vercel preview deployment has its own origin and needs its own entry.

---

## AI Workflow Summary

The full notes and running log are in [`docs/ai-workflow-notes.md`](docs/ai-workflow-notes.md).

### 1. Project brief

The course brief is not stored in the repo. The overview is restated in the Introduction of `.kiro/specs/backend/requirements.md`.

**User roles**
- **Board member:** creates boards, organizes columns, moves cards by drag-and-drop, comments, and tracks assigned tasks.
- **Board administrator:** all member actions, plus member management, board settings, analytics, and notifications.

**Non-functional requirements** (from steering files `backend.md` BE-SEC-01 to BE-SEC-03 and BE-ERR-03 to BE-ERR-04)
- Secrets come from environment variables; no default production values in source.
- CORS allows only listed origins; never `*` in production.
- All queries use SQLAlchemy expressions or bound parameters; no SQL string concatenation.
- Paginated endpoints cap `per_page` at 100; `500` responses return a generic message with no internals.

**Additions beyond the course brief**
- Roles are per board, not global. Any logged-in user can create a board and becomes its admin.
- Boards are public by default.
- Member management endpoints, `GET /api/cards?assignee=me`, soft-deleted cards, and Swagger UI were added.
- Registration signs the user in automatically.
- "Move to column" select in the card modal as a keyboard and touch fallback for drag-and-drop.

### 2. Specification generation and iteration with Kiro

Specs are split by layer: `database` (`.kiro/specs/database/`), `backend` (`.kiro/specs/backend/`) and `frontend` (`.kiro/specs/frontend/`). Each has `requirements.md`, `design.md`, `tasks.md` and `CHANGELOG.md`. The workflow was: requirements → design → tasks, with a requirements analysis pass and at least one refinement round per spec. The full version history is in the `CHANGELOG.md` of each spec folder.

**Example refinement (database):** requirement 11.6 originally said "fail on the first timeout". After the analysis pass I answered "retry one or more times". Kiro picked 3 attempts and recorded the change as V2. Criterion 7 raises the error without the password after all 3 fail.

**Example refinement (backend):** V1 had 23 requirements and no API docs. I added "Swagger UI for each blueprint". Kiro interpreted this as one Swagger UI page for the whole app (one tag per blueprint), which I accepted. V2 adds Requirement 24 (`GET /api/docs`, `GET /api/openapi.json`, Bearer JWT scheme, `SWAGGER_ENABLED` switch, tests).

**Example refinement (frontend):** V1 Decision 5 said registration redirects to `/login`. Kiro wrote that without asking. I changed it to auto-login: after a 201 from register, the page calls login with the same credentials and goes to `/`. Recorded as V2 in `CHANGELOG.md` and followed in `frontend.md` v10.

**Backend spec path:** requirements (23, then each one went through automatic detailing), then the Swagger revision (V2), then design, then tasks. The detailing step added decisions I did not give (an empty `PATCH /api/cards/<id>` returns 400, ties in `order` go after the sibling, reorder and move responses carry `rebalanced`). I kept each of them while changing what I needed.

**Database iterations:** V3 switched the test database from PostgreSQL 16 to PostgreSQL 18 already installed locally. The design also made decisions I reviewed: users who authored content cannot be hard-deleted (`RESTRICT`), and queries hide cards under soft-deleted columns. I accepted the AI suggestions while changing what I needed.

### 3. Steering guidelines

Six files in `.kiro/steering/`:
- `tool-usage.md` — use `rtk` commands for compact output.
- `change-management.md` — version every spec change in `CHANGELOG.md`.
- `database-testing.md` — run database tests on a throwaway PostgreSQL 18 cluster, never SQLite.
- `database.md` v4, `backend.md` v9, `frontend.md` v11 — project rules (each rule has an ID, Rule, Rationale, and RevoTask Example).

The three guideline files were written after the first code existed. `tool-usage.md` came first, before the specs. The baseline (tag `baseline-no-steering`, commit `e3fbedd`) was scored against each file, the code was regenerated to follow them, and the result was scored again. See `docs/violation_report.md` section 3.

Contradictions I found and resolved (recorded in `docs/violation_report.md` section 4):
- DB-ORD-01 needed `position < 'Infinity'` to reject NaN, which PostgreSQL accepts.
- DB-SCH-01 gave maximum lengths only, so an empty name was accepted.
- BE-STR-01 said "exactly eight domains", conflicting with the required `GET /api/health`.
- BE-AZ-03 and BE-VAL-01 disagreed on whether authorization or validation runs first.
- BE-NTF-03 listed ten notification types but the database CHECK listed four.
- `backend.md` v8 had no rule for OpenAPI or Swagger UI, so the code was deleted in regeneration.

### 4. Code generation and review

Generated code was scored against the guidelines. `docs/violation_report.md` records 12 violations (V-01 to V-12) with their fixes. The before/after comparison covers 27 checks across all three layers.

**Backend:** tasks 1 to 16 committed (commits `c25ba64` to `7100d5b`). Regenerated against `backend.md` v8 by a sub-agent (commits `260712f` to `1935b07`, one manual fix in `1935b07`). OpenAPI and Swagger UI (task 14) were lost when `app/common/` was deleted in regeneration; restored in `ca5df1e`. Last test run: 204 passed (149 API, 55 database), coverage 95.7%.

**Frontend:** tasks 1 to 15 committed (commits `5dd5a59` to `e3fbedd`). Regenerated against `frontend.md` by a sub-agent (commits `68a4358` to `95fd7f7`). Last checks: `npm run typecheck`, `npm run lint`, `npm test` (99 passing), and `npm run build` all pass.

**Database:** tasks 1 to 9 committed (commits `9b9c3c9` to `c02bc25`). Optional test tasks deferred.

**Selected review example:** the header showed "Log out" and navigation links to anonymous visitors. FE-AUTH-03 requires "Log in" after logout. I changed the header to check for a user, added a test for the signed-out state (`f247df9`). Unit tests had not caught it because every existing header test supplied a user.

**Prompt I had to refine:** the frontend regeneration prompt left out FE-UX-01 (loading, error and not-found states), FE-ROLE-03 (refresh after 403 or 404) and FE-UI-03 (dialog close guard). I added the missing groups in a later Kiro session.

**Things I fixed manually:**
- Tailwind v4 cannot `@apply` a custom component class, so `.btn` and the variant are applied together in markup.
- `KanbanColumn` put the title and buttons on one row, so the title wrapped mid-word. I moved the buttons below (`22b2297`).
- The expired-session wording was too broad. Only Server Component 401s leave the cookie in place. Corrected in `frontend.md` v11.

### 5. Violations found and resolved

| # | File | Guideline | Fix |
|---|------|-----------|-----|
| V-01 | `backend/app/models/notification.py` | DB-CAS-01 (wrong ON DELETE on board FK) | Fixed in regeneration |
| V-02 | `backend/app/models/` | DB-IDX-01 (3 of 12 indexes present) | Fixed in regeneration |
| V-03 | `backend/app/models/` | DB-ORD-01 (column named `order`, not `position`) | Fixed in regeneration |
| V-04 | `backend/app/blueprints/` | BE-STR-01 (nine domains, should be eight) | Fixed in regeneration |
| V-05 | `backend/app/common/validation.py` | BE-VAL-02 (LenientSchema silently dropped unknown fields) | Fixed in regeneration |
| V-06 | `backend/app/common/envelope.py` | BE-ERR-01 (plain string, not nested error object) | Fixed in regeneration |
| V-07 | `backend/app/blueprints/columns/service.py` | BE-AZ-04 (member could delete a column holding other members' cards) | Fixed in regeneration |
| V-08 | `frontend/lib/errors.ts` | FE-API-03 (`ApiError` lacked `code` and `details`) | `68a4358` |
| V-09 | `frontend/lib/session.ts` | FE-AUTH-01 (cookie written from browser, not httpOnly) | `043caf1` |
| V-10 | `frontend/app/`, `components/shared/` | FE-UX-03 (helper text 14px, badges 12px) | `341b4af` |
| V-11 | `frontend/hooks/useNotifications.ts` | FE-NTF-01 (no pause while tab hidden) | `e6fc207` |
| V-12 | `backend.md` v8 | BE-DOC-01/02 (Swagger omitted from steering; code deleted in regeneration) | `backend.md` v9; code restored in `ca5df1e` |
| V-13 | Regeneration prompt gap | The prompts said "rewrite against the steering". `backend.md` was silent about Swagger so the sub-agent deleted it. `frontend.md` was silent about the done-column behavior so `CardDetailModal` sent `completed` as a PATCH field, which the backend rejects. | `change-management.md` section 8 added. Swagger restored (`ca5df1e`). Completed toggle fixed in `CardDetailModal`. |

Full report: [`docs/violation_report.md`](docs/violation_report.md)

### 6. Kiro CLI for tests and documentation

- Tests generated with the CLI (pytest, React Testing Library, Playwright): the backend and database tests came from the backend sub-agent and the spec tasks. The frontend unit tests and the two Playwright specs were written in the Kiro IDE session in this pass, and I ran them. The e2e run needs the backend seeded (`flask seed`) and both dev servers running.
- Documentation generated with the CLI: the spec documents, changelogs and `docs/violation_report.md` were drafted by the agent and reviewed by me. The report's frontend section was first wrong about where the steering version lives (it said `frontend.md` had no version, but `docs/frontend-changelog.md` records v9, then v10 and v11). I corrected it in `b124327`.
- A prompt I had to refine, and why: the frontend regeneration prompt listed nine priority groups, but it left out FE-UX-01 (loading, error and not-found states), FE-ROLE-03 (refresh after 403 or 404) and FE-UI-03 (no dialog close while a submit is pending). The design reference was in the context section but not in a priority group, so the sub-agent did not apply it. The sub-agent's report also marked some rules as passing from code reading alone. I accepted that report too early, and only later added the missing groups in the Kiro session.
- Things I fixed manually:
  - Tailwind v4 cannot `@apply` a custom component class (`btn`), so the design classes apply `.btn` and the variant together in markup.
  - `RegisterForm.test.tsx` expected a lowercased email, but the form sends the email trimmed and not lowercased. The API lowercases it, so I corrected the test, not the form.
  - `KanbanColumn` put the title and the action buttons on one flex row, so the title wrapped mid-word. I moved the actions to their own row (`22b2297`).
  - The expired-session wording (FE-AUTH-04) was too broad. Client-side 401s do delete the cookie, and only Server Component 401s leave it in place. Corrected in `frontend.md` v11.

---

## Repository layout

```
.kiro/
  specs/        database/, backend/, frontend/ specs with requirements, design, tasks, CHANGELOG
  steering/     database.md, backend.md, frontend.md (rule files), plus tool-usage, change-management, database-testing
  design-visual/ design.html (visual reference for the frontend)
backend/
  app/          Flask application (blueprints, models, migrations, config, openapi)
  tests/        API and database tests (pytest, PostgreSQL 18)
  railway.json  Railway deployment config
docs/
  violation_report.md   before/after steering comparison, 12 violations
  ai-workflow-notes.md  full AI workflow summary
  backend-changelog.md  backend.md version history
  database-changelog.md database.md version history
  frontend-changelog.md frontend.md version history
frontend/
  app/          Next.js App Router pages and layouts
  components/   shared/, board/, layout/ components
  hooks/        useDragAndDrop, useNotifications, useErrorHandler
  lib/          apiClient, errors, ordering, roles, validation, toast, session
  context/      AuthContext
  types/        API payload types
  e2e/          Playwright specs
  vercel.json   Vercel deployment config
```
