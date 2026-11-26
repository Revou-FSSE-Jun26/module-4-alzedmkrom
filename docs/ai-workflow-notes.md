# AI Workflow Summary (draft template)

Fill this in as you work. Replace every `TODO` and every italic hint. When finished, copy the result into the "AI Workflow Summary" section of `README.md` and delete the hints. Only write what you actually did.

---

## AI Workflow Summary

### 1. Project brief

*Where does the brief live (README or /specs)? What did you write yourself versus take from the course brief?*

- Location: TODO
- Overview, user roles (board member, board administrator), core features, tech stack: TODO
- Non-functional requirements included (at least 2): TODO
- What I changed or added to the course brief: TODO

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
  - After: V2 has the register page call login with the same credentials and go to `/`. If that login fails, the page shows "Account created. Please log in." and redirects to `/login`. Recorded as V2 in `.kiro/specs/frontend/CHANGELOG.md`.
- Where the full history is recorded: `CHANGELOG.md` in each spec folder (V1, V2, ...).
- Backend spec path: requirements (23 requirements, then each one went through automatic detailing), then the Swagger revision (V2), then design, then tasks. The detailing step added decisions I did not give (an empty `PATCH /api/cards/<id>` returns 400, ties in `order` go after the sibling, reorder and move responses carry `rebalanced`). I reviewed them and kept them. TODO: say if you changed any.
- Other iteration, all recorded in `.kiro/specs/database/CHANGELOG.md`: V3 switched the test database from PostgreSQL 16 to the PostgreSQL 18 already installed locally, so no extra server is installed. The design also contains decisions to review: users who authored content cannot be hard-deleted (`RESTRICT`), and queries hide cards under soft-deleted columns. TODO: say whether you accepted or changed these.

### 3. Steering guidelines

*Say which files exist, when you wrote them, and how they are applied.*

- Workspace steering files in `.kiro/steering/`: `tool-usage.md` (use `rtk` commands for compact output), `change-management.md` (version every spec change in `CHANGELOG.md`), `database-testing.md` (run database tests on a throwaway PostgreSQL 18 cluster, never SQLite).
- Project guidelines in `/guidelines`: `frontend.md`, `backend.md`, `database.md`. Each rule has a Rule, a Rationale and a RevoTask Example.
- Written before code generation: partly. `tool-usage.md` came before the specs. `change-management.md` came after the database specs, so `CHANGELOG.md` was added afterwards (commit `a5e5fbe`). `database-testing.md` was added during task 6 (commit `c736368`). The `/guidelines` folder (`frontend.md`, `backend.md`, `database.md`) does not exist yet. TODO: write it before the backend and frontend code.
- How I checked the three files do not overlap or contradict each other: TODO
- Before and after comparison of AI output with and without the guidelines: TODO (link)

### 4. Code generation and review

*Explain how generated code was checked against the guidelines before commit.*

- Backend: required tasks 1 to 16 are done and committed (commits `c25ba64` to `7100d5b`, 2026-11-16 to 2026-11-17), one commit per blueprint or task (auth, users, boards, columns, cards, comments, notifications, analytics, health, OpenAPI and Swagger, Railway config). All 9 blueprint folders exist. The optional test tasks are not done, so tasks 17 and 18 are still open. Only a fixture smoke test (`backend/tests/api/test_fixtures_smoke.py`) exists, so the comment tests (201, 400, 401, 403), the 401 test per route and the 80% coverage gate from Requirement 23 are not met yet. TODO: write them or record why not.
- Frontend: one top-level task at a time, with one commit per task (`feat(frontend): ... (task N)`, commits `5dd5a59` to `e3fbedd`, 2026-11-20 to 2026-11-21). Tasks 1 to 15 are checked as done. Tasks 16 to 22 and sub-tasks 24.2 to 24.4 are optional test tasks that are not written, so the Vitest suites and the three Playwright specs do not exist yet. Task 24 is checked as done even though only its helper (24.1) exists. Still required: README (25.1), `vercel.json` (26.1) and the final checkpoint (27). TODO: decide whether to write the optional tests, and record the Vitest, `npm run lint`, `npm run build` and Playwright results.
- Frontend problem found and fixed: task 7.1 was started, but its file was never written and its status stayed `[~]`, so task 7.2 could not run. A review of the wave graph also found task 7.7 in the same wave as its dependency 7.6. I had Kiro reset 7.1 and task 7 to not started, moved 7.7 to a later wave, and removed the stale 7.1 run record from `tasks.meta.json`. This was a spec and tooling error, not a guideline violation. Evidence: `.kiro/specs/frontend/CHANGELOG.md`, `.kiro/specs/frontend/tasks.meta.json`.
- Database: how I ran tasks: one top-level task at a time, with one commit per task (`feat(database): ... (task N)`, commits `9b9c3c9` to `c02bc25`). Required tasks 1 to 9 are done and committed. The optional test tasks (2.2 to 2.5, 3.3, 7.2 to 7.7, 8.2, 8.3, 10, 11) are not done, so tasks 10 to 12 are still open in `tasks.md`. TODO: decide whether to run them.
- My review checklist (guideline by guideline): TODO
- Example of code I changed after review: TODO (file, what was wrong, what I changed)
- Backend tests I ran: TODO (record the last `python -m pytest` result and the coverage figure; I did not run it when writing this note).
- Tests I ran after each database task: task 6 added the shared test setup (`backend/tests/database/conftest.py`). Task 7 added `test_queries_smoke.py`. No property tests exist yet. TODO: record the last `python -m pytest tests/database` result.

### 5. Violations found and resolved

*At least 3 violations are required. Keep the full list in the violation report and link it here.*

| # | Generated code (file) | Guideline broken | Fix applied |
|---|-----------------------|------------------|-------------|
| 1 | TODO | TODO | TODO |
| 2 | TODO | TODO | TODO |
| 3 | TODO | TODO | TODO |

Full report: TODO (link)

### 6. Kiro CLI for tests and documentation

*Say what the CLI produced and what you refined by hand or by re-prompting.*

- Tests generated with the CLI (pytest, React Testing Library, Playwright): TODO
- Documentation generated with the CLI: TODO
- A prompt I had to refine, and why: TODO
- Things I fixed manually: TODO

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
| 2026-11-17 | Code | Backend optional tests not written. Tasks 17 and 18 open, only a fixture smoke test exists. | `.kiro/specs/backend/tasks.md` |
| 2026-11-14 | Specs | Frontend requirements (27) generated and detailed, V1 changelog added. | `.kiro/specs/frontend/CHANGELOG.md` |
| 2026-11-14 | Specs | Frontend V2: registration now signs in automatically (V1 Decision 5 reversed). | `.kiro/specs/frontend/CHANGELOG.md` |
| 2026-11-20 | Specs | Frontend design (V2) and tasks generated. Tasks graph has 130 sub-tasks in 13 waves. | `.kiro/specs/frontend/design.md`, `tasks.md` |
| 2026-11-20 | Setup | npm 12 blocked the Tailwind WASM tarball (`EALLOWREMOTE`). Fixed with `frontend/.npmrc` setting `allow-remote=all`. | `frontend/.npmrc` |
| 2026-11-20 to 2026-11-21 | Code | Frontend tasks 1 to 15 implemented, one commit per task. Task 24.1 (Playwright auth helper) committed. | commits `5dd5a59` to `e3fbedd` |
| 2026-11-21 | Review | Task 7.1 stuck and a same-wave dependency error for 7.7 found. Fixed in `tasks.md`, and the 7.1 run record removed from `tasks.meta.json`. | `.kiro/specs/frontend/CHANGELOG.md`, `tasks.meta.json` |
| 2026-11-21 | Code | Frontend still open: README (25.1), `vercel.json` (26.1), final checkpoint (27). Optional tests not written. | `.kiro/specs/frontend/tasks.md` |
| | | | |