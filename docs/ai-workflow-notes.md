# AI Workflow Summary

Fill this in as you work. Replace every `TODO` and every italic hint. When finished, copy the result into the "AI Workflow Summary" section of `README.md` and delete the hints. Only write what you actually did.

Status of this draft (2026-11-26): sections 3 to 6 and the running log are updated from the repo state and from this session. Items marked "Open for you" need your decision or your material, which I do not have.

---

## AI Workflow Summary

### 1. Project brief

*Where does the brief live (README or /specs)? What did you write yourself versus take from the course brief?*

- Location: Open for you. The course brief is not in the repo context I worked from.
- Overview, user roles (board member, board administrator), core features, tech stack: Open for you. The steering files state the roles and stack (`.kiro/steering/backend.md` "User types", `frontend.md` "User types"); copy from there if the README needs them.
- Non-functional requirements included (at least 2): Open for you. Examples present in the steering: secrets from the environment (BE-SEC-01), restricted CORS (BE-SEC-02), no SQL built from strings (BE-SEC-03), and bounded pagination (BE-ERR-03).
- What I changed or added to the course brief: Open for you.

### 2. Specification generation and iteration with Kiro

*Describe the path from idea to tasks, and how you improved each AI-generated document.*

- Specs are split by layer: `database` ([.kiro/specs/database](../.kiro/specs/database)), `backend` ([.kiro/specs/backend](../.kiro/specs/backend)) and `frontend` ([.kiro/specs/frontend](../.kiro/specs/frontend)). Each has requirements, design, tasks and a changelog.
- Workflow per spec: requirements, then design, then tasks. Requirements went through automatic detailing, then a requirements analysis pass.
- Example of a refinement round (real before and after):
  - Before: requirement 11.6 was one criterion. If the connection was not established within 10 seconds, the app raised an error and did not start.
  - Prompt or answer I gave: I ran the requirements analysis. It asked whether startup should retry or fail on the first timeout. I answered "retry one or more times, each bounded by the timeout". Kiro picked 3 attempts because I gave no number.
  - After: criterion 6 retries each 10-second attempt up to 3 times. New criterion 7 raises the "database unreachable" error, without the password, after all 3 fail. Recorded as V2 in the changelog.
- Second refinement round (backend, real before and after):
  - Before: backend `requirements.md` V1 had 23 requirements and no API documentation.
  - Prompt I gave: "add requirements to make Swagger UI for the app for each blueprint". Kiro read this as one Swagger UI page for the whole app, with one tag per blueprint, and I accepted that reading.
  - After: V2 adds Requirement 24 (`GET /api/docs`, `GET /api/openapi.json`, schemas generated from each blueprint Marshmallow schemas, Bearer JWT scheme, `SWAGGER_ENABLED` switch, tests). It also edits Requirements 17, 18, 20 and 23. Recorded as V2 in `.kiro/specs/backend/CHANGELOG.md`.
- Frontend refinement round (real before and after):
  - Before: frontend requirements V1, Decision 5, said registration does not sign in, so a successful registration redirected to `/login`. Kiro wrote that decision without asking me.
  - Answer I gave: I questioned the decision and chose "switch to auto-login".
  - After: V2 has the register page call login with the same credentials and go to `/`. If that login fails, the page shows "Account created. Please log in." and redirects to `/login`. Recorded as V2 in `.kiro/specs/frontend/CHANGELOG.md`. The steering file followed in `frontend.md` v10 (see section 3).
- Where the full history is recorded: `CHANGELOG.md` in each spec folder (V1, V2, ...).
- Backend spec path: requirements (23 requirements, then each one went through automatic detailing), then the Swagger revision (V2), then design, then tasks. The detailing step added decisions I did not give (an empty `PATCH /api/cards/<id>` returns 400, ties in `order` go after the sibling, reorder and move responses carry `rebalanced`). Open for you: say whether you kept or changed each of them.
- Other iteration, all recorded in `.kiro/specs/database/CHANGELOG.md`: V3 switched the test database from PostgreSQL 16 to the PostgreSQL 18 already installed locally, so no extra server is installed. The design also contains decisions to review: users who authored content cannot be hard-deleted (`RESTRICT`), and queries hide cards under soft-deleted columns. Open for you: say whether you accepted or changed these.

### 3. Steering guidelines

*Say which files exist, when you wrote them, and how they are applied.*

- Workspace steering files in `.kiro/steering/` (six files): `tool-usage.md` (use `rtk` commands for compact output), `change-management.md` (version every spec change in `CHANGELOG.md`), `database-testing.md` (run database tests on a throwaway PostgreSQL 18 cluster, never SQLite), and the three RevoTask guideline files `database.md`, `backend.md`, `frontend.md`. Each rule in the three guideline files has an ID, a Rule, a Rationale and a RevoTask Example.
- The three guideline files live in `.kiro/steering/`, not in a `/guidelines` folder. That folder does not exist, and the earlier draft that said otherwise was wrong.
- Written before code generation: partly.
  - `tool-usage.md` came before the specs.
  - `change-management.md` came after the database specs, so `CHANGELOG.md` was added afterwards (commit `a5e5fbe`).
  - `database-testing.md` was added during database task 6 (commit `c736368`).
  - `database.md` and `backend.md` were applied in steering commit `27d81a0` after the first code existed. The baseline comparison used code generated without them (tag `baseline-no-steering`, commit `e3fbedd`), and the regenerated code followed them.
  - `frontend.md` was committed in `6c7cbbb` after the first frontend code existed, for the same baseline comparison. Its current version is v11 (`docs/frontend-changelog.md`).
- How I checked the three files do not overlap or contradict each other: I did not run a systematic cross-check of every rule. I found and resolved these contradictions while applying them, and recorded each one in `docs/violation_report.md` section 4 and in `docs/database-changelog.md` and `docs/backend-changelog.md`:
  - DB-ORD-01 needed `position < 'Infinity'` so the CHECK rejects NaN.
  - DB-SCH-01 gave maximum lengths only, so an empty name was accepted.
  - DB-MIG-03 forbids mixing schema and data in one migration. Migration `0002` does this (a known exception, see section 4).
  - BE-STR-01 said "exactly eight domains", which conflicted with the required `GET /api/health`.
  - BE-AZ-03 puts authorization before validation, while BE-VAL-01 says every input is validated first.
  - BE-NTF-03 lists ten notification types, but the database CHECK listed four.
  - FE-PAGE-01 said registration redirects to `/login`, which I changed to auto-login (`frontend.md` v10).
- Before and after comparison of AI output with and without the guidelines: `docs/violation_report.md`, section 3.2 (27 checks) and section 3.3. The frontend "after" scores rest on `git grep`, unit tests, lint and build. I ran browser checks only for the routes I changed (see section 4).

### 4. Code generation and review

*Explain how generated code was checked against the guidelines before commit.*

- Backend: required tasks 1 to 16 were committed (commits `c25ba64` to `7100d5b`, 2026-11-16 to 2026-11-17), one commit per blueprint or task. The OpenAPI and Swagger UI work (task 14, commit `1525acf`) is not in the current code. Commit `fe27c75` removed `app/common/` during the steering regeneration, and nothing restored the OpenAPI module, the docs routes or `SWAGGER_ENABLED`. `tasks.md` still marks task 14 as done, which is wrong. The 8 blueprint folders (`analytics`, `auth`, `boards`, `cards`, `columns`, `comments`, `notifications`, `users`) exist, plus the health route in the app factory, as `BE-STR-01` requires after the steering change. The backend was then regenerated against `backend.md` v8 by a sub-agent (commits `260712f` to `1935b07`, with one manual fix in `1935b07`).
- Backend tests (updated 2026-11-26, this is the test status, not what the draft said earlier):
  - Test files exist beyond the fixture smoke test: `tests/api/` has `test_auth_users`, `test_boards`, `test_cards`, `test_columns`, `test_comments_notifications`, `test_members`, `test_flows` and `test_fixtures_smoke`. `tests/database/` has `test_cascades`, `test_constraints`, `test_migrations`, `test_queries_smoke`, `test_schema` and `test_seed`.
  - Last run: `python -m pytest tests/api tests/database -q -p no:randomly` gives 195 passed (140 API, 55 database) on PostgreSQL 18.
  - Coverage: `pytest --cov=app` gives 95.7% (1353 statements, 58 missed), above the 80% gate in Requirement 23.
  - Open for you: optional tasks 17 and 18 in `backend/tasks.md` were not re-checked in this pass. Confirm their checkbox state before you mark the backend done.
- Frontend: one top-level task at a time, with one commit per task (`feat(frontend): ... (task N)`, commits `5dd5a59` to `e3fbedd`, 2026-11-20 to 2026-11-21). `e3fbedd` is also the baseline for the steering comparison. Tasks 1 to 15 are checked as done. The baseline frontend was then scored against `frontend.md` (commit `6c7cbbb`), regenerated by a sub-agent in eight commits (`68a4358` to `95fd7f7`), and scored again (`00bb4ed`).
  - Unit tests: 17 Vitest files, 99 tests, all passing. These were written in the steering pass, not from the task definitions for tasks 16 to 22, so do not count them against those tasks without checking.
  - Playwright: two spec files exist. `e2e/route-states.spec.ts` (3 tests) and `e2e/register-auto-login.spec.ts` (1 test) pass against the local backend and frontend. The existing helper `e2e/helpers/auth.ts` was checked against the auto-login flow and passes.
  - Checks: `npm run typecheck`, `npm run lint`, `npm test` and `npm run build` all pass on the current `main`.
  - Still open: README (25.1), `vercel.json` (26.1) and the final checkpoint (27). Sub-tasks 24.2 to 24.4 were not checked against the spec in this pass.
- Frontend problem found and fixed: task 7.1 was started, but its file was never written and its status stayed `[~]`, so task 7.2 could not run. A review of the wave graph also found task 7.7 in the same wave as its dependency 7.6. I had Kiro reset 7.1 and task 7 to not started, moved 7.7 to a later wave, and removed the stale 7.1 run record from `tasks.meta.json`. This was a spec and tooling error, not a guideline violation. Evidence: `.kiro/specs/frontend/CHANGELOG.md`, `.kiro/specs/frontend/tasks.meta.json`.
- Database: how I ran tasks: one top-level task at a time, with one commit per task (`feat(database): ... (task N)`, commits `9b9c3c9` to `c02bc25`). Required tasks 1 to 9 are done and committed. The optional test tasks (2.2 to 2.5, 3.3, 7.2 to 7.7, 8.2, 8.3, 10, 11) are not done, so tasks 10 to 12 are still open in `tasks.md`. Open for you: decide whether to run them. The database tests that do exist are listed in the backend tests bullet above.
- Review checklist, guideline by guideline: for the frontend, I scored the 27 checks in `docs/violation_report.md` section 3.2 (8 frontend, 19 database and backend). The sub-agent's regeneration report marked more rules PASS by code reading. I did not verify each of those, so the frontend checklist is 8 of 8 scored rules, not every rule in `frontend.md`. Known gaps are listed in `docs/violation_report.md` section 3.3: the design reference is only partly applied (inputs, panels, dark mode and the font are not), and FE-UX-04 is partial.
- Example of code I changed after review: `frontend/components/layout/Header.tsx`. The header rendered "Log out" and "My tasks" without checking for a user, so an anonymous visitor saw signed-in links and no "Log in". FE-AUTH-03 requires "Log in" after logout. I changed the header to show "Log in" when there is no user and the signed-in links only for a user, and added a test for the signed-out state (commit `f247df9`). Unit tests had not caught it, because every existing header test supplied a user.
- Backend tests I ran: `python -m pytest tests/api tests/database` (195 passed) and `pytest --cov=app` (95.7%), both on 2026-11-26. I did not run them when writing the first draft of this note.
- Tests I ran after each database task: task 6 added the shared test setup (`backend/tests/database/conftest.py`). Task 7 added `test_queries_smoke.py`. Property tests do not exist. The last database run is included in the 195 backend tests above.

### 5. Violations found and resolved

*At least 3 violations are required. Keep the full list in the violation report and link it here.*

| # | Generated code (file) | Guideline broken | Fix applied |
|---|-----------------------|------------------|-------------|
| 1 | `frontend/components/layout/Header.tsx`: "Log out" and "My tasks" shown to anonymous visitors, no "Log in" link | FE-AUTH-03, FE-ROLE-02 | Header shows "Log in" without a user and the signed-in links only with one (`f247df9`). Test added. |
| 2 | `frontend/lib/session.ts`: the session cookie was written from the browser with `document.cookie`, so it was not httpOnly | FE-AUTH-01 (V-09) | Login is a Server Action that sets an httpOnly cookie (`043caf1`). |
| 3 | `frontend/lib/errors.ts`: `ApiError` had only `statusCode` and `message`, so components could not read `code` or `details` | FE-API-03 (V-08) | `ApiError` has `statusCode`, `message`, `code` and `details`, filled from the BE-ERR-01 body (`68a4358`). |
| 4 | `frontend/app/error.tsx`: read a `retry` prop, but Next.js passes `reset`, so "Try again" did nothing | FE-UX-01 | Shared `RouteError` uses `reset` (`e4c62f9`). |
| 5 | `frontend/app/my-tasks/page.tsx`, `app/page.tsx` and `components/shared/FormField.tsx`: helper text at 14px, not the required 16px. `BaseBadge.tsx` and the notification timestamp at 12px, below the 14px minimum | FE-UX-03 (V-10) | Helper text at `text-base`, badges and timestamps at `text-sm`, `text-xs` only for the notification count (`341b4af`). |

Full report: `docs/violation_report.md`, sections 1 and 2 (V-01 to V-11), with the scoring in section 3.2. Violations V-01 to V-07 are database and backend. V-08 to V-11 are frontend.

### 6. Kiro CLI for tests and documentation

*Say what the CLI produced and what you refined by hand or by re-prompting.*

- Tests generated with the CLI (pytest, React Testing Library, Playwright): the backend and database tests came from the backend sub-agent and the spec tasks. The frontend unit tests and the two Playwright specs were written in the Kiro IDE session in this pass, and I ran them. The e2e run needs the backend seeded (`flask seed`) and both dev servers running.
- Documentation generated with the CLI: the spec documents, changelogs and `docs/violation_report.md` were drafted by the agent and reviewed by me. The report's frontend section was first wrong about where the steering version lives (it said `frontend.md` had no version, but `docs/frontend-changelog.md` records v9, then v10 and v11). I corrected it in `b124327`.
- A prompt I had to refine, and why: the frontend regeneration prompt listed nine priority groups, but it left out FE-UX-01 (loading, error and not-found states), FE-ROLE-03 (refresh after 403 or 404) and FE-UI-03 (no dialog close while a submit is pending). The design reference was in the context section but not in a priority group, so the sub-agent did not apply it. The sub-agent's report also marked some rules as passing from code reading alone. I accepted that report too early, and only later added the missing groups in the Kiro session.
- Things I fixed manually:
  - Tailwind v4 cannot `@apply` a custom component class (`btn`), so the design classes apply `.btn` and the variant together in markup.
  - `RegisterForm.test.tsx` expected a lowercased email, but the form sends the email trimmed and not lowercased. The API lowercases it, so I corrected the test, not the form.
  - `KanbanColumn` put the title and the action buttons on one flex row, so the title wrapped mid-word. I moved the actions to their own row (`22b2297`).
  - The expired-session wording (FE-AUTH-04) was too broad. Client-side 401s do delete the cookie, and only Server Component 401s leave it in place. Corrected in `frontend.md` v11.

---

## Running notes (working log, not part of the README summary)

Add one line per event so you do not rely on memory later. Do not copy this table into the README.

| Date | Phase | What happened | Evidence (file or commit) |
|------|-------|---------------|---------------------------|
| 2026-11-14 | Specs | Database requirements, design and tasks generated. Analysis changed 11.6 into 11.6 and 11.7. | `.kiro/specs/database/CHANGELOG.md` |
| 2026-11-14 | Steering | Added `change-management.md` after the specs existed, then created `CHANGELOG.md`. | `.kiro/steering/change-management.md` |
| 2026-11-14 | Specs | Added CHANGELOG.md V1 and V2 for the database spec. | `.kiro/specs/database/CHANGELOG.md` |
| 2026-11-14 | Specs | V3: test database moved from PostgreSQL 16 to the local PostgreSQL 18. Added steering `database-testing.md`. | commit `c736368` |
| 2026-11-14 | Code | Database tasks 1 to 9 implemented, one commit per task. | `git log`, commits `9b9c3c9` to `c02bc25` |
| 2026-11-14 | Code | Optional property and example tests not written. Tasks 10, 11 and 12 still open in `tasks.md`. | `.kiro/specs/database/tasks.md` |
| 2026-11-14 | Specs | Backend requirements (23) generated and detailed, V1 changelog added. | `.kiro/specs/backend/CHANGELOG.md` |
| 2026-11-14 | Specs | Backend V2: added Requirement 24 (Swagger UI) and edited 17, 18, 20, 23. | `.kiro/specs/backend/CHANGELOG.md` |
| 2026-11-14 | Review | A PowerShell escape corrupted the word "rebalanced" in the backend assumptions and changelog. Found by a control-character scan and repaired. Example of an AI-introduced error caught in review (candidate for the violation report). | `.kiro/specs/backend/requirements.md`, `CHANGELOG.md` |
| 2026-11-14 | Specs | Backend design and tasks generated. Design notes Railway `railway.json` is deprecated (cutoff 2026-12-01) and `marshmallow` is pinned below 4. | `.kiro/specs/backend/design.md`, `tasks.md` |
| 2026-11-16 to 2026-11-17 | Code | Backend tasks 1 to 16 implemented, one commit per blueprint or task. | `git log`, commits `c25ba64` to `7100d5b` |
| 2026-11-17 | Code | Backend optional tests not written. Tasks 17 and 18 open, only a fixture smoke test exists. Superseded on 2026-11-26: API and database test files exist (see the backend tests bullet in section 4). Task checkboxes still to confirm. | `backend/tests/`, `.kiro/specs/backend/tasks.md` |
| 2026-11-14 | Specs | Frontend requirements (27) generated and detailed, V1 changelog added. | `.kiro/specs/frontend/CHANGELOG.md` |
| 2026-11-14 | Specs | Frontend V2: registration now signs in automatically (V1 Decision 5 reversed). | `.kiro/specs/frontend/CHANGELOG.md` |
| 2026-11-20 | Specs | Frontend design (V2) and tasks generated. Tasks graph has 130 sub-tasks in 13 waves. | `.kiro/specs/frontend/design.md`, `tasks.md` |
| 2026-11-20 | Setup | npm 12 blocked the Tailwind WASM tarball (`EALLOWREMOTE`). Fixed with `frontend/.npmrc` setting `allow-remote=all`. | `frontend/.npmrc` |
| 2026-11-20 to 2026-11-21 | Code | Frontend tasks 1 to 15 implemented, one commit per task. Task 24.1 (Playwright auth helper) committed. | commits `5dd5a59` to `e3fbedd` |
| 2026-11-21 | Review | Task 7.1 stuck and a same-wave dependency error for 7.7 found. Fixed in `tasks.md`, and the 7.1 run record removed from `tasks.meta.json`. | `.kiro/specs/frontend/CHANGELOG.md`, `tasks.meta.json` |
| 2026-11-21 | Code | Frontend still open: README (25.1), `vercel.json` (26.1), final checkpoint (27). | `.kiro/specs/frontend/tasks.md` |
| 2026-11-26 | Steering | Frontend baseline (`e3fbedd`) scored against `frontend.md`: 5 of 8 scored checks pass. Report section 3.2 filled. `frontend.md` committed. | commits `6c7cbbb`, `00bb4ed` |
| 2026-11-26 | Code | Frontend regenerated by a sub-agent in eight commits, one per steering group. After scoring: 8 of 8 scored checks pass. Four frontend violations (V-08 to V-11) recorded. | commits `68a4358` to `95fd7f7`, `docs/violation_report.md` |
| 2026-11-26 | Review | Report said `frontend.md` had no version. Wrong: `docs/frontend-changelog.md` records the version. Corrected. | commit `b124327` |
| 2026-11-26 | Code | Route loading and error states, board not-found page, refresh after 403 and 404, dialog close guard while a submit is pending, form and grouping tests. Also fixed the root `error.tsx`, which used `retry` instead of `reset`. | commit `e4c62f9` |
| 2026-11-26 | Code | Design tokens, prism background, header, buttons, badges and cards applied. Inputs, panels, dark mode and font not applied, so FE-UX-04 is partial. | commit `a630fcd` |
| 2026-11-26 | Steering | Registration signs the user in automatically (product decision changed by the user). `frontend.md` v10, changelog v10, `RegisterForm` calls the login action. | commit `6643584`, `docs/frontend-changelog.md` |
| 2026-11-26 | Steering | FE-AUTH-04 wording changed (option A, the user chose it). Client 401 deletes the cookie, Server Component 401 keeps it. `frontend.md` v11. Column header wrap fixed. | commit `22b2297` |
| 2026-11-26 | Review | Anonymous visitors saw "Log out" and signed-in links in the header. Fixed to show "Log in". Found in a browser check, not by unit tests. | commit `f247df9` |
| 2026-11-26 | Review | Swagger and OpenAPI (task 14, `1525acf`) are missing from the current backend. `fe27c75` deleted `app/common/`, and `tasks.md` still marks task 14 done. Found while checking the production Swagger default. Not restored yet. | `git show fe27c75`, `backend/app/`, `.kiro/specs/backend/tasks.md` |
| 2026-11-26 | Verification | Backend: `pytest tests/api tests/database` 195 passed, `pytest --cov=app` 95.7%. Frontend: lint passes, 99 unit tests pass, `npm run build` compiles. Playwright: 4 tests pass on localhost (3 route-state, 1 registration). | `backend/`, `frontend/` run output, 2026-11-26 |
| | | | |
