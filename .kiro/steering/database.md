---
inclusion: always
---

# RevoTask Database Guidelines

Stack: PostgreSQL + Flask-SQLAlchemy (SQLAlchemy 2.x) + Flask-Migrate (Alembic).
Every guideline has an ID, a **Rule**, a **Rationale**, and a **RevoTask example**. Cite the ID when reporting a violation (e.g. "violates DB-CAS-01").

## Scope and boundaries

This file owns: tables and columns, types, constraints, indexes, foreign keys and cascade behavior, migrations, and seed data.

This file does NOT own, and must not restate:
- Request validation, permissions, the error contract, query logic, transactions, and notification triggers: see `backend.md`.
- Anything about the UI: see `frontend.md`.

The section headings below named **Board membership**, **Board visibility**, **Ownership columns**, **Cascade rules**, **Ordering columns**, **Done columns**, **Soft delete**, and **Notification retention** are referenced by name from `backend.md`. Do not rename them.

---

## 1. Conventions

### DB-CNV-01 One database, one tool chain
- **Rule:** Use PostgreSQL for development, tests, and production. Models live in `app/models/<entity>.py`, one model per file, exported from `app/models/__init__.py`. Models subclass `db.Model` (Flask-SQLAlchemy) and declare columns with `db.Column` and `db` types such as `db.Float`, `db.Boolean`, and `db.DateTime(timezone=True)`. Schema changes are made only through Flask-Migrate migrations. `db.create_all()` is never called outside a throwaway test setup.
- **Rationale:** Partial indexes, CHECK constraints, and UUID types behave differently on SQLite, so tests on another engine give false confidence.
- **RevoTask example:** adding `cards.due_date` is a new migration file, not an edit to a table created earlier.

### DB-CNV-02 Naming
- **Rule:** Tables are plural snake_case (`board_members`). Columns are snake_case. Primary key is `id`. Foreign keys are `<entity>_id`. Configure `MetaData(naming_convention=...)` so every index, unique, check, foreign key, and primary key constraint gets a deterministic name (`ix_`, `uq_`, `ck_`, `fk_`, `pk_` prefixes).
- **Rationale:** Unnamed constraints get random names, which makes migrations non-reproducible and downgrades fail.
- **RevoTask example:** the one-done-column index is named `uq_columns_board_id_done`, not an auto-generated name.

### DB-CNV-03 UUID primary keys
- **Rule:** Every table except `board_members` has `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`, mapped as `UUID(as_uuid=True)`. No integer or sequential IDs.
- **Rationale:** The API addresses resources by UUID (`column_id` in `CardPositionSchema`, `<uuid:...>` path converters), and UUIDs cannot be enumerated.
- **RevoTask example:** `GET /api/cards/<uuid>` never exposes how many cards exist.

### DB-CNV-04 Timestamps
- **Rule:** Mutable tables have `created_at` and `updated_at` as `TIMESTAMPTZ NOT NULL DEFAULT now()`, with `updated_at` refreshed on update. Store UTC only. Append-only tables (`board_members`, `notifications`) have `created_at` only.
- **Rationale:** Timezone-aware UTC avoids ambiguity, and the "this week" analytics window is defined in UTC.
- **RevoTask example:** `cards.completed_at` is `TIMESTAMPTZ`, so "Monday 00:00 UTC" comparisons are exact.

### DB-CNV-05 Explicit nullability and hard deletes
- **Rule:** Every column declares `nullable` explicitly, and NOT NULL is the default choice. Rows are hard-deleted, with one exception: cards are soft-deleted through `cards.deleted_at` (see Soft delete). No `deleted_at`, `is_deleted`, or archive columns exist on any other table.
- **Rationale:** Implicit nullability hides bugs, and limiting soft delete to cards keeps the cascade behavior of every other table simple.
- **RevoTask example:** deleting a comment removes the row; there is no "deleted comment" state.

---

## 2. Tables

### DB-SCH-01 Tables and columns (single source of truth)
- **Rule:** The schema is exactly the following. Do not add tables or columns without updating this section first. The `position` columns are exposed in the models and the API as `order` (see DB-ORD-01). `created_at` / `updated_at` follow DB-CNV-04 where listed.

**users**

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `name` | VARCHAR(100) | NOT NULL |
| `email` | VARCHAR(255) | NOT NULL; unique on `lower(email)` |
| `password_hash` | VARCHAR(255) | NOT NULL |
| `created_at`, `updated_at` | TIMESTAMPTZ | NOT NULL |

There is no `role` column. Roles exist only on `board_members`.

**boards**

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `name` | VARCHAR(100) | NOT NULL |
| `is_public` | BOOLEAN | NOT NULL, default `true` |
| `created_by` | UUID | NULL, FK `users`, ON DELETE SET NULL |
| `created_at`, `updated_at` | TIMESTAMPTZ | NOT NULL |

**board_members**

| Column | Type | Constraints |
|---|---|---|
| `board_id` | UUID | NOT NULL, FK `boards`, ON DELETE CASCADE |
| `user_id` | UUID | NOT NULL, FK `users`, ON DELETE CASCADE |
| `role` | VARCHAR(10) | NOT NULL, CHECK in (`member`, `admin`) |
| `added_by` | UUID | NULL, FK `users`, ON DELETE SET NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL |

Primary key is `(board_id, user_id)`.

**columns**

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `board_id` | UUID | NOT NULL, FK `boards`, ON DELETE CASCADE |
| `name` | VARCHAR(100) | NOT NULL |
| `position` | DOUBLE PRECISION | NOT NULL, CHECK `position > 0` |
| `is_done` | BOOLEAN | NOT NULL, default `false` |
| `created_by` | UUID | NULL, FK `users`, ON DELETE SET NULL |
| `created_at`, `updated_at` | TIMESTAMPTZ | NOT NULL |

Also `UNIQUE (id, board_id)`, needed by the `cards` composite foreign key.

**cards**

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `board_id` | UUID | NOT NULL |
| `column_id` | UUID | NOT NULL |
| `title` | VARCHAR(200) | NOT NULL |
| `description` | TEXT | NULL, CHECK `char_length(description) <= 5000` |
| `assignee_id` | UUID | NULL, FK `users`, ON DELETE SET NULL |
| `due_date` | DATE | NULL |
| `position` | DOUBLE PRECISION | NOT NULL, CHECK `position > 0` |
| `completed_at` | TIMESTAMPTZ | NULL |
| `deleted_at` | TIMESTAMPTZ | NULL (set when the card is soft-deleted) |
| `created_by` | UUID | NULL, FK `users`, ON DELETE SET NULL |
| `created_at`, `updated_at` | TIMESTAMPTZ | NOT NULL |

Composite FK `(column_id, board_id)` references `columns (id, board_id)`, ON DELETE CASCADE.

**comments**

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `card_id` | UUID | NOT NULL, FK `cards`, ON DELETE CASCADE |
| `content` | TEXT | NOT NULL, CHECK `char_length(content) BETWEEN 1 AND 2000` |
| `created_by` | UUID | NULL, FK `users`, ON DELETE SET NULL |
| `created_at`, `updated_at` | TIMESTAMPTZ | NOT NULL |

**notifications**

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | NOT NULL, FK `users`, ON DELETE CASCADE (the recipient) |
| `type` | VARCHAR(30) | NOT NULL, CHECK in the `type` values defined in `backend.md` BE-NTF-03 |
| `message` | VARCHAR(500) | NOT NULL |
| `board_id` | UUID | NULL, **no foreign key** (see Notification retention) |
| `is_read` | BOOLEAN | NOT NULL, default `false` |
| `created_at` | TIMESTAMPTZ | NOT NULL |

- **Rationale:** One authoritative schema prevents generated migrations and models from drifting apart.
- **RevoTask example:** a request to "add a `priority` field to cards" starts with a row added to the `cards` table above, then a migration, then the model.

### DB-SCH-02 Text limits are the storage ceiling
- **Rule:** The lengths above are the single definition of maximum text length. Schemas in `backend.md` and validation in `frontend.md` take their limits from these tables and never define larger or separate ones. Text columns that have a limit but no VARCHAR length (`description`, `content`) carry a CHECK constraint as a backstop.
- **Rationale:** A schema limit that is looser than the database limit turns a 422 into a 500.
- **RevoTask example:** a 6,000-character `description` is rejected by the schema with 422, and would also be rejected by `ck_cards_description_length` if the schema were bypassed.

### DB-SCH-03 Cards cannot point at another board's column
- **Rule:** `cards.board_id` must always match the board of its column. This is enforced by the composite foreign key `(column_id, board_id)` → `columns (id, board_id)`, not by application code alone. `board_id` on a card is set from its column when the card is created and never changed independently.
- **Rationale:** The API rejects cross-board moves with 422, and the database makes that guarantee hold even if a bug skips the check.
- **RevoTask example:** an `UPDATE cards SET column_id = <column on board B>` for a card on board A fails with a foreign key violation.

---

## 3. Board membership

### DB-MEM-01 Membership is the only place roles live
- **Rule:** A user's role on a board is the `role` of their `board_members` row, constrained to `member` or `admin` by a CHECK. A user without a row has no role (the API treats them as a Guest). The table's primary key is `(board_id, user_id)`, so a user can have at most one row per board. No `guest` value is ever stored.
- **Rationale:** Per-board roles with a composite key make "two roles on one board" impossible.
- **RevoTask example:** inserting a second row for the same user on the same board fails on `pk_board_members`.

### DB-MEM-02 Last-admin safety needs a lock
- **Rule:** "A board always has at least one Admin" cannot be expressed as a CHECK. The service that demotes or removes an Admin must lock the board's admin rows (`SELECT ... FOR UPDATE` on `board_members` where `board_id = :id AND role = 'admin'`) before counting them, in the same transaction as the change.
- **Rationale:** Without the lock, two Admins demoting each other at the same moment can both pass the count check and leave the board with no Admin.
- **RevoTask example:** two simultaneous `PATCH /api/boards/<id>/members/<user_id>` demotions on a two-Admin board result in exactly one 200 and one 409 `LAST_ADMIN`.

---

## 4. Board visibility

### DB-VIS-01 Visibility is one boolean, default public
- **Rule:** `boards.is_public` is `BOOLEAN NOT NULL DEFAULT true`, with the default set at the database level (`server_default`) as well as in the model. Public listing is supported by a partial index on `boards (created_at DESC) WHERE is_public`.
- **Rationale:** Boards are public by default, and the default must hold even for rows inserted outside the ORM, such as seed scripts.
- **RevoTask example:** `INSERT INTO boards (id, name) VALUES (...)` produces a public board.

---

## 5. Ownership columns

### DB-OWN-01 `created_by` is nullable and uses SET NULL
- **Rule:** `boards`, `columns`, `cards`, and `comments` each have `created_by UUID NULL REFERENCES users ON DELETE SET NULL`. `board_members.added_by` and `cards.assignee_id` follow the same pattern. These columns are never NOT NULL, and never use CASCADE.
- **Rationale:** Deleting a user must not delete the work they created. A NULL `created_by` means "no owner", which the backend treats as foreign work that only Admins can delete.
- **RevoTask example:** if a user account is removed, their cards stay on the board with `created_by = NULL`, and their assigned cards become unassigned.

### DB-OWN-02 Ownership is set once
- **Rule:** `created_by` is set at insert time from the authenticated user and is never updated afterwards. There is no API field that writes it.
- **Rationale:** If ownership could change, the "delete only your own work" rule could be bypassed.
- **RevoTask example:** `PATCH /api/cards/<id>` cannot change who created the card.

---

## 6. Cascade rules

### DB-CAS-01 Foreign key behavior table
- **Rule:** Foreign keys use exactly these `ON DELETE` behaviors:

| Foreign key | On delete |
|---|---|
| `board_members.board_id` → `boards` | CASCADE |
| `board_members.user_id` → `users` | CASCADE |
| `columns.board_id` → `boards` | CASCADE |
| `cards (column_id, board_id)` → `columns (id, board_id)` | CASCADE |
| `comments.card_id` → `cards` | CASCADE |
| `notifications.user_id` → `users` | CASCADE |
| `created_by`, `added_by`, `assignee_id` → `users` | SET NULL |
| `notifications.board_id` | no foreign key |

Deleting a board therefore removes its memberships, columns, cards, and comments. Deleting a column removes its cards and their comments. A direct card delete is not a cascade: it sets `deleted_at` (DB-SOFT-01).
- **Rationale:** Children of a board have no meaning without it, while references to users must not destroy shared work.
- **RevoTask example:** an Admin deleting a board leaves no orphan cards or comments, and the Admin's `DELETE` needs no manual cleanup code.

### DB-CAS-02 The database cascade is a safety net, not a permission
- **Rule:** The cascades above are mechanical. They do not decide who may delete. A Member's delete is checked in the service first (`backend.md` BE-AZ-04); the cascade only runs after that check passes or for an Admin.
- **Rationale:** If the service skipped its check, the cascade would silently destroy other members' cards.
- **RevoTask example:** a Member deleting their own column that contains another member's card gets 409 from the service before the cascade could run.

### DB-CAS-03 ORM relationships defer to the database
- **Rule:** Parent relationships that have a database cascade declare `passive_deletes=True` and `cascade="all, delete-orphan"`. Every foreign key declares `ondelete` explicitly in the model, so migrations create the same behavior as the table above.
- **Rationale:** ORM-only cascades load every child row before deleting it, which is slow and misses rows added by other sessions.
- **RevoTask example:** `Board.columns = relationship(..., cascade="all, delete-orphan", passive_deletes=True)`.

---

## 7. Ordering columns

### DB-ORD-01 Float position columns
- **Rule:** `columns.position` and `cards.position` are `DOUBLE PRECISION NOT NULL` with `CHECK (position > 0)`. In the models, declare them as `order = db.Column("position", db.Float(53), nullable=False)`: the Python attribute and the API field are `order`, while the database column is named `position` because `order` is a reserved SQL word. A precision of 53 bits is stored as double precision. Never use `db.Integer`, `db.Numeric`, or a single-precision type. Ordering constants and formulas live in `backend.md` BE-ORD-01, not here.
- **Rationale:** Double precision gives enough room for midpoint insertion, and the CHECK matches the positive-float validation on `CardPositionSchema`.
- **RevoTask example:** an `INSERT` with `position = 0` fails on `ck_cards_position`.

### DB-ORD-02 Position is not unique
- **Rule:** There is no UNIQUE constraint on `position`, within a column or across a board. Position lookups are supported by non-unique indexes on `columns (board_id, position)` and `cards (column_id, position)` (partial on `deleted_at IS NULL` for cards).
- **Rationale:** The float strategy tolerates temporary ties and resolves them with a rebalance, while a UNIQUE constraint would turn a tie into a 500.
- **RevoTask example:** two cards briefly sharing `position = 1536.0` is valid until the rebalance in `backend.md` BE-ORD-02 renumbers the column.

---

## 8. Done columns

### DB-DON-01 One done column per board
- **Rule:** `columns.is_done` is `BOOLEAN NOT NULL DEFAULT false`. A partial unique index `uq_columns_board_id_done` on `columns (board_id) WHERE is_done` allows at most one done column per board. `cards.completed_at` is `TIMESTAMPTZ NULL` and is NULL for every card not currently in a done column.
- **Rationale:** "Completed this week" analytics rely on one unambiguous definition of done.
- **RevoTask example:** setting `is_done = true` on a second column of the same board fails on `uq_columns_board_id_done`, and the API returns 409.

### DB-DON-02 `completed_at` has a supporting index
- **Rule:** Create a partial index on `cards (board_id, completed_at) WHERE completed_at IS NOT NULL AND deleted_at IS NULL`.
- **Rationale:** The weekly analytics query filters on completed cards only, and most cards are not completed.
- **RevoTask example:** `completed_this_week` in `GET /api/boards/<id>/analytics` uses this index.

---

## 9. Soft delete

### DB-SOFT-01 Cards are soft-deleted
- **Rule:** `cards.deleted_at` is `TIMESTAMPTZ NULL`; NULL means the card is active. It is the only soft-delete column in the schema. A direct card delete sets it to the current UTC time (behavior in `backend.md` BE-SVC-06). Deleting a column or board still removes its cards from the table through the cascade, including soft-deleted ones. A soft-deleted card keeps its `column_id`, `board_id`, and `position`, and its comments stay in the table. Nothing restores a soft-deleted card through the application.
- **Rationale:** Deleted cards remain recoverable by an operator, while every other delete stays a plain, simple cascade.
- **RevoTask example:** after `DELETE /api/cards/<id>`, `SELECT * FROM cards WHERE id = :id` still returns the row with `deleted_at` set, but the board payload no longer includes it.

### DB-SOFT-02 One filter helper and partial indexes
- **Rule:** The `Card` model defines one class-level query helper, `Card.active()`, that applies `deleted_at IS NULL`, and services use it for every card query (BE-SVC-06). Card indexes used by board, move, task, and analytics queries are partial on `deleted_at IS NULL` (see DB-IDX-01).
- **Rationale:** A filter repeated by hand gets forgotten in one query, and soft-deleted rows would otherwise bloat the indexes.
- **RevoTask example:** `Card.active().filter_by(column_id=column.id)` backs the board view and uses the partial index on `(column_id, position)`.

---

## 10. Notification retention

### DB-NTF-01 Notifications are independent of what they describe
- **Rule:** A notification stores its own `message` text and an optional plain `board_id`. It has no foreign key to boards, columns, cards, or comments. Its only relationship is to the recipient (`user_id`). The text is written when the notification is created and never rebuilt from the original item.
- **Rationale:** A notification such as "Your card was deleted by an administrator" must outlive the card, column, or board it describes.
- **RevoTask example:** after a board is deleted with `CASCADE`, every `notifications` row about it is still there, with `board_id` pointing at a board that no longer exists.

### DB-NTF-02 Notification indexes
- **Rule:** Create an index on `notifications (user_id, created_at DESC)` for the paginated list, and a partial index on `notifications (user_id) WHERE NOT is_read` for unread lookups and for the `unread_count` returned by `GET /api/notifications`.
- **Rationale:** `GET /api/notifications` always filters by user and orders newest first.
- **RevoTask example:** page 2 of `GET /api/notifications?page=2&per_page=10` is served by the first index without a sort step.

---

## 11. Indexes

### DB-IDX-01 Every index is justified by an endpoint
- **Rule:** Create these indexes, and no others without an endpoint that needs them. Primary keys and unique constraints already create their own indexes.

| Table | Index | Serves |
|---|---|---|
| `users` | unique on `lower(email)` (`uq_users_email_lower`) | register, login, add member by email |
| `board_members` | `(user_id)` | `GET /api/boards?scope=mine`, `GET /api/cards?assignee=me` |
| `boards` | partial `(created_at DESC) WHERE is_public` | `GET /api/boards?scope=public` |
| `columns` | `(board_id, position)` | `GET /api/boards/<id>` |
| `columns` | unique `(board_id) WHERE is_done` | DB-DON-01 |
| `cards` | `(column_id, position) WHERE deleted_at IS NULL` | board view, position moves |
| `cards` | `(assignee_id) WHERE assignee_id IS NOT NULL AND deleted_at IS NULL` | `GET /api/cards?assignee=me` |
| `cards` | `(board_id, created_by) WHERE deleted_at IS NULL` | `cards_created` in analytics |
| `cards` | partial `(board_id, completed_at) WHERE completed_at IS NOT NULL AND deleted_at IS NULL` | DB-DON-02 |
| `comments` | `(card_id, created_at)` | `GET /api/cards/<id>/comments` |
| `comments` | `(created_by)` | `comments_added` in analytics |
| `notifications` | `(user_id, created_at DESC)`, partial `(user_id) WHERE NOT is_read` | DB-NTF-02 |

- **Rationale:** Indexes cost writes and storage, so each one needs a reason, and every join or filter in `backend.md` should be covered.
- **RevoTask example:** `GET /api/cards?assignee=me` filters on `assignee_id` and joins `board_members` on `user_id`, so both are indexed.

---

## 12. Migrations

### DB-MIG-01 One change per migration, reviewed
- **Rule:** Each schema change is one migration with a descriptive message (`add_cards_due_date`). Autogenerated migrations are always reviewed and edited before commit, because Alembic does not reliably detect partial indexes, CHECK constraints, or server defaults. Applied migrations are never edited; fix problems with a new migration.
- **Rationale:** Reviewed, immutable history keeps every environment reproducible.
- **RevoTask example:** the autogenerated migration for `uq_columns_board_id_done` is edited to include `postgresql_where=sa.text("is_done")`.

### DB-MIG-02 Every migration has a working downgrade
- **Rule:** Every migration implements `downgrade()`. CI runs `flask db upgrade` on an empty database, then `flask db downgrade base`, then `flask db upgrade` again.
- **Rationale:** A broken downgrade is discovered during an incident, which is the wrong time.
- **RevoTask example:** downgrading the `notifications` migration drops its two indexes before dropping the table.

### DB-MIG-03 Data migrations are separate
- **Rule:** Schema changes and data changes are in separate migrations. A migration that changes data must be safe to run on a table with existing rows (add nullable column, backfill, then add NOT NULL).
- **Rationale:** Mixing them makes failures hard to roll back.
- **RevoTask example:** adding a NOT NULL column to `cards` is three steps: add as nullable, backfill, set NOT NULL.

---

## 13. Seed and test data

### DB-SEED-01 Idempotent demo seed
- **Rule:** A `flask seed` command creates demo data: at least one Admin, one Member, and one Guest-only user (no membership), one public board with columns (including one done column), cards, and comments, plus one private board. It is idempotent (running it twice does not duplicate rows) and refuses to run when `FLASK_ENV=production` unless forced. Seed passwords are documented demo values, never real credentials.
- **Rationale:** Evaluators and the frontend need realistic data for every role, and per-board roles mean there is no global "seed admin".
- **RevoTask example:** after `flask seed`, logging in as the demo Member and calling `GET /api/boards` returns the demo boards they belong to.

### DB-TST-01 Constraints are tested against PostgreSQL
- **Rule:** Include tests that assert the database itself rejects or handles: a duplicate email differing only by case; a second done column on one board; `position <= 0`; an invalid membership `role`; a card moved to a column on a different board; a second membership row for the same user and board. Also assert cascade behavior: deleting a board removes its memberships, columns, cards (including soft-deleted ones), and comments; deleting a user sets `created_by` and `assignee_id` to NULL and keeps the rows; deleting a board leaves its notifications in place. Also assert that deleting a card keeps its row with `deleted_at` set, and that `Card.active()` excludes it.
- **Rationale:** Constraints are only guarantees if they are exercised without the application's own checks.
- **RevoTask example:** `test_second_done_column_rejected` inserts directly through SQLAlchemy and expects an `IntegrityError` naming `uq_columns_board_id_done`.
