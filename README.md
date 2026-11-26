# RevoTask

A Trello-like task manager. Board members create boards, organize work into columns, move cards by drag-and-drop, comment, and track the cards assigned to them. Board administrators manage member access, oversee all cards, and monitor team activity through analytics and notifications.

- `frontend/` — Next.js 16 client app (TypeScript, Tailwind CSS)
- `backend/` — Flask REST API (Python, SQLAlchemy, Marshmallow, PostgreSQL 18)

---

## AI Workflow Summary

See [`docs/ai-workflow-notes.md`](docs/ai-workflow-notes.md) for the full notes and running log.

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

Full report: [`docs/violation_report.md`](docs/violation_report.md)

---

## Backend setup

**Prerequisites:** Python 3.11+, PostgreSQL 18.

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env        # then fill in DATABASE_URL and JWT_SECRET_KEY
flask db upgrade
flask seed                  # optional: load demo data
flask run                   # starts on http://localhost:5000
```

**Environment variables** (see `backend/.env.example` for all keys):

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Long random value used to sign JWTs |
| `CORS_ORIGINS` | Comma-separated allowed origins (default `http://localhost:3000`) |
| `SWAGGER_ENABLED` | `true` or `false`. Defaults to `true` in non-production, `false` in production |
| `FLASK_ENV` | Set to `production` on Railway/Render; affects Swagger default |

**Run tests:**
```bash
python -m pytest tests/api tests/database -q -p no:randomly
```

**API docs** (when `SWAGGER_ENABLED=true`): `http://localhost:5000/api/docs`

---

## Frontend setup

**Prerequisites:** Node.js 20.9+, npm 12+.

```bash
cd frontend
npm install     # .npmrc sets allow-remote=all — required for Tailwind's optional WASM
                # package on npm 12, which otherwise fails with EALLOWREMOTE
cp .env.example .env.local   # then fill in the two API base URL variables
```

**Environment variables** (see `frontend/.env.example`):

| Variable | Where used | Value |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Browser (compiled in) | API origin, e.g. `http://localhost:5000` — no trailing slash, no `/api` |
| `API_BASE_URL` | Server Components | Same as above. Falls back to `NEXT_PUBLIC_API_BASE_URL` when unset |
| `PLAYWRIGHT_BASE_URL` | E2E tests only | Frontend origin, e.g. `http://localhost:3000`. Not needed on Vercel |

**Commands:**

| Command | Description |
|---|---|
| `npm run dev` | Start the development server on `http://localhost:3000` |
| `npm run build` | Run ESLint then build for production |
| `npm test` | Run all Vitest unit tests |
| `npm run typecheck` | TypeScript type check without emitting files |
| `npm run test:e2e` | Run Playwright end-to-end tests (needs `PLAYWRIGHT_BASE_URL`) |

---

## Deploying to Vercel

1. Import the repository. Set **Root Directory** to `frontend`.
2. Set these environment variables in the Vercel project settings:
   - `NEXT_PUBLIC_API_BASE_URL` — the Railway/Render API URL, e.g. `https://my-api.railway.app` (no trailing slash, no `/api`)
   - `API_BASE_URL` — the same value (Server Components use this; `NEXT_PUBLIC_*` variables are only available in browser code)
3. `PLAYWRIGHT_BASE_URL` is not needed in Vercel. It is only used by the local E2E test runner.
4. `NEXT_PUBLIC_*` values are compiled into the browser bundle at build time. A change requires a redeploy.
5. After the first deployment, check the Vercel build log → install step:
   - Confirm that `.npmrc` was read and `allow-remote=all` is active.
   - If Vercel uses an npm version older than 12 it may warn about the unknown key; the install still succeeds.

**CORS:** the backend `CORS_ORIGINS` must list the exact Vercel origin as `https://<host>` with no trailing slash and no path. Add `http://localhost:3000` for local development. Server Component requests are server-to-server and do not require a CORS entry. Each Vercel preview deployment has its own origin and needs its own entry.

---

## Repository layout

```
.kiro/
  specs/        database/, backend/, frontend/ specs with requirements, design, tasks, CHANGELOG
  steering/     database.md, backend.md, frontend.md (rule files), plus tool-usage, change-management, database-testing
  design-visual/ design.html (visual reference for the frontend)
backend/
  app/          Flask application (blueprints, models, migrations, config)
  tests/        API and database tests (pytest, PostgreSQL 18)
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
```
