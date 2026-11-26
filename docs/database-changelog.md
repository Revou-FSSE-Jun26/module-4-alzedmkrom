# database.md Changelog

Newest first. The current file is v4 (v4 produced on 2026-11-21; v1 to v3 on 2026-11-14). Each change is logged as it is made, so entries are accurate summaries, though earlier file versions are not kept for download.

Keep this file outside `.kiro/steering/` (for example `docs/`) so Kiro does not load it as context.

---

## v4 (current): Feedback from the database and backend scoring

Applied after the violation report (`docs/violation_report.md` section 4). Each change is listed with its reason.

**Changed**
- **DB-ORD-01 and DB-SCH-01 (position CHECK):** the position CHECK now has an upper bound, `position > 0 AND position < 'Infinity'`. Reason: PostgreSQL accepts `NaN` as a number above all others, so `position > 0` alone lets `NaN` through. The code already enforced this.
- **DB-SCH-01 (empty strings):** every text column in the tables also has `CHECK (char_length(<column>) >= 1)`. Reason: a maximum length alone accepts empty strings. The code already enforced this.
- **DB-SCH-01 (`notifications.type`):** the CHECK refers to the ten `type` values listed in `backend.md` BE-NTF-03. Reason: the two steering files disagreed. The database CHECK in the code still has only four values, so six notification types cannot be stored. That is a code gap, not a steering gap, and it is still open.
- **DB-OWN-02 (`created_by`):** names the enforcement point (the backend service layer, `backend.md` BE-AZ-02 and BE-VAL-02). Reason: the rule named no enforcer. No trigger was added.

**Not changed (decided)**
- **DB-MIG-03 (no mixed schema and data migrations):** kept. Migration `0002_v4_schema` mixes both, because the filename was requested and the migration has already run locally. Recorded as a known exception in the violation report.

**Related changes in other files**
- `backend.md` v8: BE-STR-01 (named app-level routes), BE-VAL-01 (validation runs after BE-AZ-03 checks), BE-ERR-02 (405 and specific 409 codes).
- `docs/violation_report.md` section 4: the proposals listed there are now applied.

**Impact**
- Requirements: none (database requirements unchanged).
- Design components: none.
- Implementation: the position CHECK in the code already matches. The notification CHECK still needs a migration that adds the six missing types, and the code must emit them. Neither is done.

---

## v3: Rubric alignment and soft-deleted cards

**Added**
- `cards.deleted_at` (`TIMESTAMPTZ NULL`) in the cards table.
- New section 9, **Soft delete** (DB-SOFT-01, DB-SOFT-02): cards are soft-deleted; deleting a column or board still removes cards through the cascade, including soft-deleted ones; `Card.active()` is the single filter helper. Later sections are renumbered 10 to 13. The section name is now referenced from `backend.md`.

**Changed**
- **Stack and models (DB-CNV-01):** Flask-SQLAlchemy with `db.Model`, `db.Column`, and `db` types.
- **DB-CNV-05:** hard deletes everywhere except cards. This replaces the earlier "no soft delete anywhere" rule.
- **Order column (DB-ORD-01):** models declare `order = db.Column("position", db.Float(53), nullable=False)`. The attribute and API field are `order`, and the database column stays `position`. The schema-mapping wording is removed.
- **Indexes (DB-IDX-01, DB-ORD-02, DB-DON-02):** card indexes are partial on `deleted_at IS NULL`.
- **DB-SCH-02:** the table lengths are now the single definition of maximum text length. Backend and frontend take their limits from them.
- **DB-CAS-01:** notes that a direct card delete is not a cascade.
- **DB-TST-01:** tests added for soft delete and `Card.active()`.

**Related changes in other files**
- `backend.md` v7: BE-SVC-06, singular file names, eight blueprints, and field lengths moved here.
- `frontend.md` v2: validation limits sourced from `database.md`.

---

## v2: Frontend alignment

Reference updates only. No schema, constraint, or cascade changes.

**Changed**
- DB-IDX-01: the `board_members (user_id)` and `cards (assignee_id)` index rows, and the example, now cite `GET /api/cards?assignee=me` instead of `GET /api/users/me/cards`.
- DB-NTF-02: the unread partial index now also serves the `unread_count` returned by `GET /api/notifications`.

**Related change in another file**
- `backend.md` v6: assigned-tasks endpoint moved and `unread_count` added.

---

## v1: First full draft

**Stack assumed:** PostgreSQL, SQLAlchemy 2.x, Flask-Migrate (Alembic). Front matter is `inclusion: always`.

**Added**
- **Conventions (DB-CNV-01 to 05):** PostgreSQL for dev, tests, and production; migrations only; deterministic constraint names; UUID primary keys; UTC `TIMESTAMPTZ`; explicit nullability; hard deletes only.
- **Tables (DB-SCH-01 to 03):** schema for `users`, `boards`, `board_members`, `columns`, `cards`, `comments`, and `notifications`. There is no `users.role`. `board_members` uses the composite primary key `(board_id, user_id)`. Cards carry a composite foreign key `(column_id, board_id)` so a card cannot point at another board's column. Text limits are the storage ceiling for the limits in `backend.md`.
- **Board membership (DB-MEM-01, 02):** roles live only in `board_members`, constrained to `member` or `admin`. Demoting or removing an Admin must lock the board's admin rows first, so concurrent changes cannot leave a board with no Admin.
- **Board visibility (DB-VIS-01):** `boards.is_public` defaults to `true` at the database level, with a partial index for public listing.
- **Ownership columns (DB-OWN-01, 02):** `created_by`, `added_by`, and `assignee_id` are nullable with `ON DELETE SET NULL`, and `created_by` is set once.
- **Cascade rules (DB-CAS-01 to 03):** full `ON DELETE` table. The database cascade is a safety net, not a permission, since the service's 409 check runs first. ORM relationships use `passive_deletes=True`.
- **Ordering columns (DB-ORD-01, 02):** `position` is `DOUBLE PRECISION` with `CHECK (position > 0)` and is not unique. The API field `order` maps to the column `position`, because `order` is a reserved SQL word.
- **Done columns (DB-DON-01, 02):** `is_done` with a partial unique index (one done column per board), `completed_at` on cards, and a supporting partial index.
- **Notification retention (DB-NTF-01, 02):** notifications store their own `message` and a plain `board_id` with no foreign keys to boards, columns, cards, or comments, so they survive deletions. Indexes for the paginated list and unread lookups.
- **Indexes (DB-IDX-01):** every index tied to the endpoint that needs it.
- **Migrations (DB-MIG-01 to 03):** one reviewed change per migration, a working downgrade checked in CI, schema and data changes kept separate.
- **Seed and tests (DB-SEED-01, DB-TST-01):** idempotent `flask seed` with data for every role, and constraint and cascade tests run against PostgreSQL.

**Related change in another file**
- `backend.md` v5 was edited to match the `position` naming (BE-SVC-02 and the section 6 intro).
