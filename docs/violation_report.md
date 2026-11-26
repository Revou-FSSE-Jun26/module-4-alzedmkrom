# RevoTask Violation Report

Scope of this revision: the database steering (`database.md`). Backend and frontend checks are listed but not scored yet. They will be scored when `backend.md` and `frontend.md` are loaded.

## 0. Overview

| Item | Value |
|---|---|
| Author | AlzedMk2 (local Windows user; name to confirm) |
| Date of review | 2026-11-21 |
| Kiro version / model used | Kiro IDE session. The model is not recorded in the repo. |
| Steering files reviewed against | `database.md` (repo file, changelog v3). `backend.md` v7 and `frontend.md` v9 are not yet in `.kiro/steering/`. |
| Steering location in repo | `.kiro/steering/` |
| Baseline code (generated without steering) | Tag `baseline-no-steering` = commit `e3fbedd` (on `origin/main`), the last commit before any steering file was added. Database checks 14 to 19 were scored on this code. |
| Code after steering + refinement | `main`, commits `e1abc90` to `86143d1` (database layer, V4). Spec revision `fe1457c`. |
| Number of violations reported | 3 (all database, DB-CAS-01, DB-IDX-01, DB-ORD-01) |

**Original generation prompt(s):**

```text
Baseline (V3): Kiro executed .kiro/specs/database/tasks.md task by task, with no steering file loaded.
Example, task 4.1: "Implement User in app/models/user.py. Columns name, email, password_hash; checks name_length (1 to 255) and email_length (3 to 254); unique functional index uq_users_email_lower on lower(email); no plaintext password column. Requirements 1.1, 1.2, 1.3, 1.4, 1.7."
Example, task 4.3: "Implement BoardColumn in app/models/column.py ... order = db.Column(db.Float, nullable=False) with check order_positive ..."
```

**Refinement prompt for the "after" run (V4):**

```text
Regenerate the database layer on main from the database V4 spec and .kiro/steering/database.md. The steering is the source of truth for schema. Write only backend/app/models, backend/app/seed.py, backend/migrations/versions/0002_v4_schema.py and backend/tests/database. Keep migration 0001 untouched. Apply the resolved open decisions in CHANGELOG V4. Rewrite the delete rules to DB-CAS-01 exactly (owner references SET NULL, notifications.board_id has no foreign key). Map the order attribute to the position column (DB-ORD-01). Create every DB-IDX-01 index. Cover DB-TST-01 with PostgreSQL tests.
```

---

## 1. Summary of violations

| ID | Area | Guideline broken | Severity | Fix status | Fix commit |
|---|---|---|---|---|---|
| V-01 | Database | DB-CAS-01 (also DB-OWN-01, DB-NTF-01) | Medium | Fixed | `e1abc90` (models), `c18264f` (migration `0002_v4_schema`) |
| V-02 | Database | DB-IDX-01 (also DB-SOFT-02, DB-DON-01, DB-DON-02, DB-NTF-02) | Medium | Fixed | `e1abc90`, `c18264f` |
| V-03 | Database | DB-ORD-01 (also DB-CNV-02) | Low | Fixed | `e1abc90`, `c18264f` |

Severity guide: High = security hole, data loss, or wrong permissions. Medium = wrong behavior or broken contract. Low = maintainability, naming, or structure.

---

## 2. Violation details

### V-01: Owner references use RESTRICT, and notifications have a foreign key to boards

| Field | Details |
|---|---|
| Guideline broken | DB-CAS-01 in `database.md` |
| Rule (short, in my words) | Owner and author references (`created_by`, `added_by`, `assignee_id`) must be `ON DELETE SET NULL`. `notifications.board_id` must have no foreign key. |
| Location in generated code (baseline `e3fbedd`) | `backend/app/models/board.py:17` (`owner_id`, RESTRICT); `backend/app/models/card.py:22` (`created_by`, RESTRICT); `backend/app/models/comment.py:17` (`user_id`, RESTRICT); `backend/app/models/notification.py:17` (`board_id`, FK CASCADE) |
| Also affects | DB-OWN-01 (owner columns), DB-NTF-01 (notification independence) |
| Severity | Medium. Deleting a user who owns a board, created a card or wrote a comment fails with a foreign key error. Deleting a board removes notifications that should survive. |
| How I found it | Manual review of the baseline models, plus `grep -rn "ForeignKey" backend/app/models/`. |

**What Kiro generated (baseline):**

```text
# backend/app/models/card.py
created_by = db.Column(
    UUID(as_uuid=True),
    db.ForeignKey("users.id", ondelete="RESTRICT"),
    ...
)
# backend/app/models/notification.py
board_id = db.Column(
    UUID(as_uuid=True),
    db.ForeignKey("boards.id", ondelete="CASCADE"),
    ...
)
```

**Why this violates the guideline:** DB-OWN-01 says deleting a user must not delete or block on the work they created, and a NULL `created_by` means "no owner". RESTRICT blocks the user delete. The board-level FK on notifications makes the notification disappear with its board, which DB-NTF-01 forbids.

**Refinement prompt I wrote:** see the refinement prompt in section 0. Its rule for DB-CAS-01 names this case.

**Fix applied (V4 model excerpt, `e1abc90`):**

```text
# backend/app/models/card.py
created_by = db.Column(
    UUID(as_uuid=True),
    db.ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
)
# backend/app/models/notification.py: no ForeignKey on board_id
board_id = db.Column(UUID(as_uuid=True), nullable=True)
```

| Field | Details |
|---|---|
| Fix commit | `e1abc90` (models) and `c18264f` (migration `0002_v4_schema`, which converts the existing constraints) |
| Fixed by | Regeneration from the V4 spec and steering, run as a sub-agent. Not a manual edit. |
| How I verified the fix | `pg_constraint` on `revotask_db` shows `fk_cards_created_by_users ... ON DELETE SET NULL` and `fk_cards_assignee_id_users ... ON DELETE SET NULL`, and the composite `(column_id, board_id)` FK with `ON DELETE CASCADE`. The cascade tests in `backend/tests/database/test_cascades.py` pass (55 passed). |

---

### V-02: Database indexes are missing, not partial, or the wrong shape

| Field | Details |
|---|---|
| Guideline broken | DB-IDX-01 in `database.md` (the 12-row index table) |
| Rule (short, in my words) | Create exactly the listed indexes, partial where the steering says so (for example `WHERE deleted_at IS NULL` on cards). |
| Location in generated code (baseline) | `backend/app/models/card.py` (`ix_cards_column_id_order`, `ix_cards_assignee_id`, `ix_cards_completed_at`, not partial); `backend/app/models/comment.py` (`ix_comments_card_id` only); `backend/app/models/board.py` and `column.py` (no public or done index) |
| Also affects | DB-SOFT-02 (partial indexes on cards), DB-DON-01 (done index), DB-DON-02 (completed index), DB-NTF-02 (unread index) |
| Severity | Medium. Queries such as `GET /api/cards?assignee=me` and the comments list lose their intended index support. Soft-deleted rows also bloat the index. |
| How I found it | Scored check 19 on the baseline: `grep -rn "db.Index" backend/app/models/`. Only 3 of the 12 rows were present. |

**What Kiro generated (baseline):**

```text
db.Index("ix_cards_column_id_order", "column_id", "order"),
db.Index("ix_cards_assignee_id", "assignee_id"),
db.Index("ix_cards_completed_at", "completed_at"),
db.Index("ix_comments_card_id", "card_id"),
```

**Why this violates the guideline:** the baseline has no partial indexes, no `(board_id, completed_at)` index, no `(board_id, created_by)` index, no unread notification index, no public board index and no single-done-column index. Two of the baseline indexes cover the wrong columns for the endpoints they serve.

**Refinement prompt I wrote:** see the refinement prompt in section 0 (rule: "Create every DB-IDX-01 index").

**Fix applied (excerpt of V4 model, `e1abc90`):**

```text
# backend/app/models/card.py
db.Index("ix_cards_column_id_position", "column_id", "position",
         postgresql_where=db.text("deleted_at IS NULL")),
db.Index("ix_cards_assignee_id", "assignee_id",
         postgresql_where=db.text("assignee_id IS NOT NULL AND deleted_at IS NULL")),
db.Index("ix_cards_board_id_completed_at", "board_id", "completed_at",
         postgresql_where=db.text("completed_at IS NOT NULL AND deleted_at IS NULL")),
db.Index("ix_cards_board_id_created_by", "board_id", "created_by",
         postgresql_where=db.text("deleted_at IS NULL")),
```

| Field | Details |
|---|---|
| Fix commit | `e1abc90` and `c18264f` |
| Fixed by | Regeneration (sub-agent), not a manual edit |
| How I verified the fix | A `pg_indexes` query on `revotask_db` lists 13 index objects: the 12 DB-IDX-01 rows (the notifications row has two indexes) plus `uq_users_email_lower`. The index names match the spec. I did not re-check each partial predicate by hand. |

---

### V-03: The order column is named `order`, not `position`

| Field | Details |
|---|---|
| Guideline broken | DB-ORD-01 in `database.md` |
| Rule (short, in my words) | The database column is `position`. The model attribute and API field are `order`. `order` is a reserved SQL word. |
| Location in generated code (baseline) | `backend/app/models/card.py:27`, `backend/app/models/column.py:16` |
| Also affects | DB-CNV-02 (naming) |
| Severity | Low. The behavior works, but the name breaks the steering's naming rule and the reserved-word reason. |
| How I found it | Scored check 17 on the baseline. The column name in `db.Column(db.Float, ...)` has no explicit name, so it is `order`. |

**What Kiro generated (baseline):**

```text
order = db.Column(db.Float, nullable=False)
```

**Why this violates the guideline:** without an explicit name, the SQL column is `order`. Every raw SQL reference then needs quoting, and the steering's DB-ORD-01 example (`ck_cards_position`) cannot match.

**Refinement prompt I wrote:** see the refinement prompt in section 0.

**Fix applied (`e1abc90`):**

```text
order = db.Column("position", db.Float(53), nullable=False)
```

| Field | Details |
|---|---|
| Fix commit | `e1abc90` |
| Fixed by | Regeneration (sub-agent) |
| How I verified the fix | The `pg_constraint` and `pg_indexes` output shows `position` and `ix_cards_column_id_position`. The position constraint test in `backend/tests/database/test_constraints.py` passes. |

---

## 3. Before/after comparison

### 3.1 Setup

| Item | Before (no steering) | After (with steering) |
|---|---|---|
| Branch / commit | Tag `baseline-no-steering` = `e3fbedd` | `main` at `86143d1` (database commits `e1abc90` to `86143d1`) |
| Steering files loaded | None (`database.md` did not exist yet) | `database.md` (V4 steering) |
| Prompt used | `.kiro/specs/database/tasks.md` V3, task by task | `.kiro/specs/database/tasks.md` V4 section and the refinement prompt in section 0 |
| Kiro version / model | Kiro IDE session, model not recorded | Sub-agent (`general-task-execution`), model not recorded |
| Date run | 2026-11-14 | 2026-11-21 |

**Limits of this setup:** the "after" run was executed by a sub-agent with the V4 spec and steering loaded, not by a fresh Kiro session with only the steering file. The prompts are not identical, because V4 changed the spec. The comparison measures the database layer only.

### 3.2 Scoring checklist

Database checks (scored):

| # | Guideline | Check | Before | After | Evidence |
|---|---|---|---|---|---|
| 14 | DB-CNV-03 | Every primary key is a UUID | Pass | Pass | Before: `backend/app/models/mixins.py:13-18`. After: `backend/app/models/mixins.py:15-20` (`UUIDPrimaryKeyMixin` with `gen_random_uuid()`). `board_members` uses the composite PK, which the rule allows. |
| 15 | DB-SCH-01 | The `Card` model has `created_at`, `updated_at`, and `deleted_at` | Pass | Pass | Before: `card.py:7` (`UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin`). After: `backend/app/models/card.py:7`, same bases. |
| 16 | DB-MEM-01 | Roles are stored per board (`board_members.role`), and `users` has no role column | Pass | Pass | After: `backend/app/models/board_member.py:37` `CHECK role IN ('member', 'admin')`; `user.py` has no role column. |
| 17 | DB-ORD-01 | Card and column ordering uses `db.Float` with a positive-value CHECK | Pass (name wrong) | Pass | Before: column named `order`, so V-03. After: `card.py:23` and `column.py:19` `db.Column("position", db.Float(53), nullable=False)`. The CHECK also rejects NaN and Infinity (OD-4, deviation recorded in section 4). |
| 18 | DB-CAS-01 | Foreign keys declare the `ON DELETE` behavior from the cascade table | Fail | Pass | Before: V-01. After: `pg_constraint` on `revotask_db` shows `cards.(column_id, board_id)` CASCADE, `cards.assignee_id` SET NULL, `cards.created_by` SET NULL. Board, column, membership, comment and notification rules match the table in `database.md`. |
| 19 | DB-IDX-01 | The listed indexes exist (record how many of the 12 rows are present) | Fail (3 of 12) | Pass (12 of 12 rows) | Before: 3 of 12 present, 1 partial, 8 missing (V-02). After: `pg_indexes` on `revotask_db` lists the 12 rows, with notifications as two indexes (13 objects including `uq_users_email_lower`). Partial predicates were not re-checked by hand. |

Backend checks (not scored yet, backend steering not loaded):

| # | Guideline | Check | Before | After | Evidence |
|---|---|---|---|---|---|
| 1 | BE-STR-01 | The 8 blueprints each have `routes.py`, `service.py`, and `schema.py` | Not scored yet | Not scored yet | Backend steering pending |
| 2 | BE-STR-02 | No `db.session` or query code in any `routes.py` | Not scored yet | Not scored yet | Backend steering pending |
| 3 | BE-VAL-02 | Every input schema rejects unknown fields | Not scored yet | Not scored yet | Backend steering pending |
| 4 | BE-VAL-03 | `CardPositionSchema` requires a UUID `column_id` and `order` greater than 0 | Not scored yet | Not scored yet | Backend steering pending |
| 5 | BE-ERR-01 | All errors use the single `{"error": {"code", "message", "details"}}` shape | Not scored yet | Not scored yet | Backend steering pending |
| 6 | BE-ERR-03 | `GET /api/notifications` is paginated with `page` and `per_page`, with a maximum `per_page` | Not scored yet | Not scored yet | Backend steering pending |
| 7 | BE-AUTH-01 | Passwords are hashed, and no response includes `password_hash` | Not scored yet | Not scored yet | Backend steering pending |
| 8 | BE-AUTH-02 | The JWT has an expiry (`exp`) taken from configuration | Not scored yet | Not scored yet | Backend steering pending |
| 9 | BE-AZ-04 | A Member can delete only their own card or column, a column holding another member's card returns 409, and an Admin can delete any | Not scored yet | Not scored yet | Backend steering pending |
| 10 | BE-AZ-04 | Comment edit and delete are owner-only, even for an Admin | Not scored yet | Not scored yet | Backend steering pending |
| 11 | BE-SVC-01 | Services commit once and roll back on error, and routes never commit | Not scored yet | Not scored yet | Backend steering pending |
| 12 | BE-SVC-02 | `GET /api/boards/<id>` loads columns and cards with eager loading (no per-column or per-card queries) | Not scored yet | Not scored yet | Backend steering pending |
| 13 | BE-SEC-01 | No hard-coded secrets, values come from the environment, and `.env.example` exists | Not scored yet | Not scored yet | Backend steering pending |

Frontend checks (not scored yet, frontend steering not loaded):

| # | Guideline | Check | Before | After | Evidence |
|---|---|---|---|---|---|
| 20 | FE-STR-03 | Dashboard and Board Detail are Server Components | Not scored yet | Not scored yet | Frontend steering pending |
| 21 | FE-API-01, FE-API-03 | One `apiClient` makes all backend calls and throws an `ApiError` with `statusCode` and `message` | Not scored yet | Not scored yet | Frontend steering pending |
| 22 | FE-DND-03 | Drag-and-drop uses native events, updates optimistically, and restores the exact original position on error | Not scored yet | Not scored yet | Frontend steering pending |
| 23 | FE-NTF-01 | Notifications poll every 30 seconds and clear the interval on unmount | Not scored yet | Not scored yet | Frontend steering pending |
| 24 | FE-UI-01 | My Tasks and Profile use `BaseButton`, with no raw `<button>` elsewhere | Not scored yet | Not scored yet | Frontend steering pending |
| 25 | FE-AUTH-01 | The token is not stored in `localStorage` or `sessionStorage` | Not scored yet | Not scored yet | Frontend steering pending |
| 26 | FE-SEC-01 | No `dangerouslySetInnerHTML` anywhere | Not scored yet | Not scored yet | Frontend steering pending |
| 27 | FE-UX-03 | No text below 14px (except avatar initials and the notification count), body text and helper messages at 16px, and `BaseBadge` (medium weight) at 14px | Not scored yet | Not scored yet | Frontend steering pending |

### 3.3 Results

Only the six database checks are scored so far.

| Measure | Before (no steering) | After (with steering) | Change |
|---|---|---|---|
| Checks passed (of 27) | 4 of 6 scored (database only) | 6 of 6 scored (database only) | +2 |
| Pass rate | 67% of scored | 100% of scored | +33 points |
| Backend checks passed (of 13) | Not scored | Not scored | n/a |
| Database checks passed (of 6) | 4 | 6 | +2 |
| Frontend checks passed (of 8) | Not scored | Not scored | n/a |
| Guideline violations found in review | 3 (V-01 to V-03) | 0 open in database | -3 |
| Tests generated / tests passing (optional) | 1 smoke test file | 55 database tests passing (PostgreSQL 18) | n/a (not a like-for-like count) |

**What improved most, and why:** DB-CAS-01 and DB-IDX-01 went from fail to pass. Both are rules the steering lists as explicit tables, so the regenerated code could match them line by line (owner references SET NULL, the 12 index rows). DB-ORD-01 kept its pass, but the column name changed to `position`, which the steering asks for.

**What did not improve, or got worse:** Nothing in the database set got worse. The regeneration deleted the 17 local `activity_logs` rows when `0002` ran (the table was removed by the steering), and the downgrade cannot restore them. Migration `0002` also mixes schema and data changes in one revision, which DB-MIG-03 forbids. I did that because the filename was requested. See section 4.

**Limits of this comparison:** single run per condition. The "after" code was produced by a sub-agent with the V4 spec, so the two runs did not use identical prompts. The database checks depend on what the spec asks for, so a baseline spec that was not steering-aware would score differently. The backend and frontend checks are not scored, so this table does not show the full steering effect.

---

## 4. Guideline feedback

Changes below are proposed only. I have not edited `database.md`, because the steering file is yours to change. Each proposal would go into `docs/database-changelog.md` when you approve it.

| Guideline ID | Problem found | Change made | Changelog entry |
|---|---|---|---|
| DB-ORD-01 | The rule says `CHECK (position > 0)`, but PostgreSQL accepts `NaN` (it sorts above every number). The baseline code and the backend both needed `position < 'Infinity'`. | Proposed: change the CHECK to `position > 0 AND position < 'Infinity'`. Applied in the code (OD-4). | Proposed, not yet written |
| DB-SCH-01 | The table gives maximum lengths only. An empty `name` or `title` is accepted, which the baseline code rejected. | Proposed: add a minimum (for example `>= 1`) to each text column in the table. Applied in the code (OD-3). | Proposed, not yet written |
| DB-MIG-03 | Migration `0002` mixes schema and data changes in one revision, because the filename was requested. The rule forbids this. | Proposed: allow one revision when a conversion needs both, or write the data steps as a separate revision. | Proposed, not yet written |
| DB-OWN-02 | The steering says `created_by` is never updated, but names no enforcement point. The V4 spec relies on the backend. | Proposed: name the enforcement point (backend service or a trigger). No trigger was added (OD-9). | Proposed, not yet written |

---

## 5. Submission checklist

- [x] At least 3 violations are listed in section 2, from real Kiro output (the baseline `e3fbedd`).
- [x] Every violation names the guideline it breaks (ID and file).
- [x] Every violation records the fix applied, with a commit link and how it was verified.
- [x] Every violation includes the refinement prompt that was used.
- [x] The database part of the before/after comparison in section 3 is complete, with evidence for each check.
- [ ] Backend and frontend checks in section 3 are scored (pending `backend.md` and `frontend.md`).
- [ ] `frontend.md`, `backend.md`, and `database.md` are committed in `.kiro/steering/` (`backend.md` and `frontend.md` are pending).
- [x] Every database guideline has a Rule, a Rationale, and a concrete RevoTask example (`database.md`, DB-CNV-01 to DB-TST-01).
- [x] Contradictions between the database steering and the spec, and the database steering itself, are recorded in section 4.
- [ ] Section 0 author name to confirm, and the Kiro model to confirm.

---

## Appendix: Where to look first

| Guideline | Command or check |
|---|---|
| DB-CNV-03 | `grep -rn "primary_key\|gen_random_uuid" backend/app/models/` |
| DB-ORD-01 | `grep -rn "db.Float\|position" backend/app/models/` |
| DB-CAS-01 | `grep -rn "ForeignKey\|ForeignKeyConstraint" backend/app/models/` and check each `ondelete` |
| DB-IDX-01 | `grep -rn "db.Index" backend/app/models/` and `select indexname from pg_indexes` on `revotask_db` |
| BE-STR-01 | `ls backend/app/blueprints/*/` (pending backend steering) |
| FE-API-01 | `grep -rn "fetch(" frontend/app frontend/components frontend/hooks frontend/lib` (pending frontend steering) |
| FE-AUTH-01 | `grep -rn "localStorage\|sessionStorage" frontend` (exclude `node_modules`) |
| FE-UI-01 | `grep -rn "<button" frontend/app frontend/components --include=*.tsx` (anything outside `BaseButton.tsx`) |
| FE-SEC-01 | `grep -rn "dangerouslySetInnerHTML" frontend/app frontend/components` |
| FE-UX-03 | `grep -rn "text-xs\|text-\[" frontend/app frontend/components --include=*.tsx` |
